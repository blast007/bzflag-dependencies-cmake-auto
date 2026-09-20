#!/usr/bin/env python3
import hashlib
import json
import os
import re
import uuid
import sys
import urllib.request
import urllib.error
from pathlib import Path
import subprocess
from dataclasses import dataclass, asdict, is_dataclass
from packaging import version
import argparse

http_timeout = 30

@dataclass
class AssetInfo:
    url: str
    github_repo: str
    version: version.Version
    sha256_hash: str

@dataclass
class UpdateInfo(AssetInfo):
    new_version: version.Version

# Variable to track a list of errors
errors: list[str] = []

class UpdateInfoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        elif isinstance(o, version.Version):
            return str(o)
        return super().default(o)


def s_if_not_one_len(data) -> str:
    return f"{'s' if len(data) != 1 else ''}"


def get_absolute_path(relative_path: str) -> Path | None:
    """Get an absolute path using a path relative to the root of the git repository."""
    if not hasattr(get_absolute_path, "base_path"):
        try:
            # Run the git command to get the top-level directory
            root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
            get_absolute_path.base_path = Path(root.strip())
        except subprocess.CalledProcessError:
            # Not a git repository or git is not installed
            errors.append("Failed to find the git root")
            return None
    return get_absolute_path.base_path / relative_path


def parse_sources_cmake(sources_path: Path) -> dict[str, AssetInfo] | None:
    """Parse the contents of sources.cmake, returning any GitHub information."""
    # Verify that the file exists
    if not sources_path.exists():
        errors.append("Error finding sources.cmake")
        return None

    # Build a regex to extract the parts of the GitHub URL and to extract the SHA256
    source_re = re.compile(r'set\((\w+)_URL\s+\"(https://github.com/([^/]+/[^/]+)/.*/.*?(\d+(?:[._]\d+)+)[^\"]+)\"\)\nset\((\w+)_HASH\s+\"SHA256=([0-9a-fA-F]+)\"\)')

    # Read the contents of the sources file
    text = sources_path.read_text()

    # Build up a list of dependencies and their URLs
    sources: dict[str, AssetInfo] = {}
    for match in source_re.finditer(text):
        # Check that group 1 and group 4 match, which should both be the variable prefix (such as SDL)
        if match.group(1) != match.group(5):
            errors.append(f"Error parsing sources.cmake. Mismatched variable prefix ({match.group(1)} vs {match.group(5)})")
            # Don't bother parsing any further
            return None
        sources[match.group(1)] = AssetInfo(
            match.group(2), # URL
            match.group(3), # org/repo
            version.Version(match.group(4)), # version
            match.group(6), # SHA256
        )

    if not sources:
        errors.append("No sources found in sources.cmake")
        return None

    return sources


def github_request(url: str) -> urllib.request.Request :
    """Convenient wrapper to create an urllib Request and add the GitHub token, if available."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "bzflag-dependency-update-bot")

    # Use GITHUB_TOKEN if available for higher rate limits
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token is not None and github_token != "":
        req.add_header("Authorization", f"token {github_token}")

    return req


def get_github_latest_release(repo: str) -> dict | None:
    """Fetch the latest release information for a GitHub repository."""
    try:
        # The check_updates() call will suffix :2 onto the organization if the sources are still using SDL2. Because the
        # latest version is SDL3 now, we have to grab the list of releases and search for a SDL2 release. We currently
        # only check the latest 50 releases, so this could eventually fail.
        if repo == "libsdl-org/SDL:2":
            req = github_request(f"https://api.github.com/repos/libsdl-org/SDL/releases?per_page=50")
            with urllib.request.urlopen(req, timeout=http_timeout) as response:
                data = json.loads(response.read())
                # Find the first (newest) SDL2 release
                for release in data:
                    if release["tag_name"].startswith("release-2."):
                        return release

            # Couldn't find an SDL2 release
            return None
        else:
            req = github_request(f"https://api.github.com/repos/{repo}/releases/latest")
            with urllib.request.urlopen(req, timeout=http_timeout) as response:
                return json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError) as _:
        return None


def calculate_suffix_rank(name, suffix_ranks) -> int:
    for rank, suffixes in enumerate(suffix_ranks):
        if any(name.endswith(s) for s in suffixes):
            return rank
    return len(suffix_ranks)


def find_best_asset(assets):
    asset_re = re.compile(r'.*?(\d+(?:[._]\d+)+)\.(?:tar\.gz|tgz|tar\.bz2|zip)$')
    suffix_rank = (
        ('.tar.gz', '.tgz'),  # first choice
        ('.tar.bz2',),  # second choice
        ('.zip',),  # third choice
    )

    matches = []  # (rank, name, asset, version)
    for asset in assets:
        name = asset.get('name', '')
        m = asset_re.search(name)
        if m:
            matches.append((calculate_suffix_rank(name, suffix_rank), name, asset, version.Version(m.group(1))))

    # Go through the asset matches, in order of rank, to find the best asset
    for rank in range(len(suffix_rank)):
        matches_at_rank = [a for a in matches if a[0] == rank]

        # If we have one match, then this is the best one to use
        if len(matches_at_rank) == 1:
            # Return the asset and the version
            return matches_at_rank[0][2], matches_at_rank[0][3]
        # If we found more than one at the same rank, we cannot determine which is the best
        elif len(matches_at_rank) > 1:
            raise Exception("Multiple matching assets found, so it is not possible to determine the correct asset")

    # We didn't find any matches
    return None, None


def download_sha256(url: str) -> str | None:
    """Download a file from a URL and return its SHA-256 hex digest."""
    try:
        with urllib.request.urlopen(url, timeout=http_timeout) as response:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: response.read(65536), b""):
                hasher.update(chunk)
            return hasher.hexdigest()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def check_updates() -> dict[str, UpdateInfo] | None:
    """Checks for any dependency updates, and returns a list of any that were found."""
    sources_path = get_absolute_path("sources.cmake")
    if sources_path is None:
        return None

    sources = parse_sources_cmake(sources_path)
    if sources is None:
        return None

    updates: dict[str, UpdateInfo] = {}

    # Loop through all the dependencies and check if we're on the latest version for each
    for dep_name, source in sources.items():
        # Get info about the latest release, with a special case for SDL2 so that we check for the latest SDL2 release
        if source.github_repo == 'libsdl-org/SDL' and source.version < version.Version("3.0.0"):
            latest_release = get_github_latest_release(source.github_repo + ":2")
        else:
            latest_release = get_github_latest_release(source.github_repo)

        if latest_release is None:
            errors.append(f"{source.github_repo}: Failed to fetch release information")
            continue

        latest_asset: UpdateInfo | None = None

        # If there are assets, check those for a .tar.gz or .tgz file
        assets = latest_release.get("assets", [])
        if assets:
            try:
                # Try to find the best asset
                best_asset, beset_asset_version = find_best_asset(assets)
                if best_asset is not None:
                    # Ensure the digest is sha256
                    digest = best_asset.get("digest") or ""
                    if not digest.startswith("sha256:"):
                        errors.append(f"{source.github_repo}: Asset does not have a sha256 hash")
                        continue

                    # Store a reference this as the latest asset
                    latest_asset = UpdateInfo(
                        best_asset["browser_download_url"],
                        source.github_repo,
                        source.version,
                        digest[len("sha256:"):],
                        beset_asset_version
                    )
            except Exception as e:
                errors.append(f"{source.github_repo}: {e}")
                continue

            # If we went through all the assets and found one that is valid, check if it's newer
            if latest_asset is None:
                errors.append(f"{source.github_repo}: Failed to determine latest asset")
                continue
            else:
                if latest_asset.new_version > source.version:
                    updates[dep_name] = latest_asset

        # Otherwise, we'll use the GitHub generated source archives (currently only for PDCurses)
        else:
            # Extract the version number from the tag
            tag_ver_re = re.compile(r'(\d+(?:[._]\d+)+)')
            match = re.match(tag_ver_re, latest_release["tag_name"])
            if match:
                new_version = version.Version(match.group(1).replace("_", "."))

                # Check if it's newer
                if new_version > source.version:

                    # Build the download URL
                    download_url = f"https://github.com/{source.github_repo}/archive/refs/tags/{latest_release["tag_name"]}.tar.gz"
                    download_hash = download_sha256(download_url)

                    if download_hash is None:
                        errors.append(f"{source.github_repo}: Failed to download {download_url} for hashing")
                        continue

                    updates[dep_name] = UpdateInfo(
                        download_url,
                        source.github_repo,
                        source.version,
                        download_hash,
                        new_version,
                    )

    return updates


def update_sources_cmake(updates: dict[str, UpdateInfo]):
    """Writes out an updated sources.cmake with the latest updates."""
    sources_path = get_absolute_path("sources.cmake")
    if sources_path is None or not sources_path.exists():
        errors.append(f"{sources_path}: Failed to find sources.cmake file")
        return

    # Read the contents of the sources file
    contents = sources_path.read_text()

    # Apply each update
    for lib_name, update in updates.items():
        # Update URL
        contents = re.sub(
            rf'set\({lib_name}_URL\s+"[^"]*"\)',
            f'set({lib_name}_URL "{update.url}")',
            contents
        )

        # Update hash
        hash_value = f"SHA256={update.sha256_hash}"
        contents = re.sub(
            rf'set\({lib_name}_HASH\s+"[^"]*"\)',
            f'set({lib_name}_HASH "{hash_value}")',
            contents
        )

    # Write out the updated file
    sources_path.write_text(contents)


def write_github_output(updates: dict[str, UpdateInfo]) -> None:
    """Writes output variables for later GitHub Actions steps."""

    # Create a list of update information strings used for the commit and PR body
    updates: list[str] = [f"{u.github_repo}: {u.version} → {u.new_version}" for u in updates.values()]

    # Create a delimiter for multi-line values should be unique.
    delimiter = f"EOF_{uuid.uuid4().hex}"

    # Build the title and the body
    title = f'Automatic update for {len(updates)} update{s_if_not_one_len(updates)}'
    body = f'{"\n".join(updates)}'

    # Write the output, falling back to stdout when not in a GitHub environment (for debugging)
    if "GITHUB_OUTPUT" in os.environ:
        fh = open(os.environ["GITHUB_OUTPUT"], "a")
    else:
        fh = sys.stdout

    print(f'commit-message<<{delimiter}\n{title}\n{body}\n{delimiter}', file=fh)
    print(f'pr-title={title}', file=fh)
    print(f'pr-body<<{delimiter}\n{body}\n{delimiter}', file=fh)


def main() -> int:
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report updates without writing files")
    args = parser.parse_args()

    # Check for updates
    updates = check_updates()

    # We do not want to update the files if any errors were encountered.
    if errors:
        for e in errors:
            print(f"::error::{e}")
        return 1

    # Update the files if we found any updates
    if updates:
        print(f"::notice::Found {len(updates)} update{s_if_not_one_len(updates)}!")
        for _, update in updates.items():
            print(f"::notice::{update.github_repo}: {update.version} → {update.new_version}")
        if not args.dry_run:
            update_sources_cmake(updates)
            write_github_output(updates)
        else:
            print(f"::warning::Updates were found, but files were not updated in dry-run mode.")
    else:
        print(f"::notice::All dependencies are up-to-date!")

    return 0

if __name__ == "__main__":
    exit(main())
