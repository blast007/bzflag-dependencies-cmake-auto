@echo off

if not "%DevEnvDir%" == "" (
	echo.
	echo Error: Do not run from an existing Visual Studio command prompt or with a prompt from a previous run.
	exit /b 1
)

set "INPUT_ARCH=%~1"
:: If no architecture is specified, just build the default architectures.
if not defined INPUT_ARCH (
	cmd.exe /C %~0 x86
	if errorlevel 1 exit /b 1
	cmd.exe /C %~0 x64
	if errorlevel 1 exit /b 1
	exit /b 0
)

if "%INPUT_ARCH%" == "x86" goto x86
if "%INPUT_ARCH%" == "x64" goto x64
if "%INPUT_ARCH%" == "arm64" goto arm64
goto invalidarch

:x86
set VCVAR_ARCH=x86
set CMAKE_ARCH=Win32
goto run

:x64
set VCVAR_ARCH=x64
set CMAKE_ARCH=x64
goto run

:arm64
set VCVAR_ARCH=x64_arm64
set CMAKE_ARCH=arm64
goto run

:invalidarch
echo Error: Invalid architecture specified. Use one of x86, x64, or arm64
exit /b 1

:no_vs
echo Error: no Visual Studio installation with the C++ toolset was found
exit /b 1

:no_vcvars
echo Error: unable to locate vcvarsall.bat under %INSTALL_DIR%
exit /b 1

:vcvars_failed
echo Error: vcvarsall.bat failed
exit /b 1

:run
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "INSTALL_DIR="
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -products * -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "INSTALL_DIR=%%i"
if not defined INSTALL_DIR goto no_vs

set "VCVARSALL=%INSTALL_DIR%\VC\Auxiliary\Build\vcvarsall.bat"
if not exist "%VCVARSALL%" goto no_vcvars

call "%VCVARSALL%" %VCVAR_ARCH%
if errorlevel 1 goto vcvars_failed


cmake -S . -B build/%INPUT_ARCH% -A %CMAKE_ARCH%
if errorlevel 1 (
	echo Error: CMake configure failed for %INPUT_ARCH%
	exit /b 1
)
cmake --build build/%INPUT_ARCH% --parallel --config Debug
if errorlevel 1 (
	echo Error: CMake Debug build failed for %INPUT_ARCH%
	exit /b 1
)
cmake --build build/%INPUT_ARCH% --parallel --config Release
if errorlevel 1 (
	echo Error: CMake Release build failed for %INPUT_ARCH%
	exit /b 1
)
exit /b 0
