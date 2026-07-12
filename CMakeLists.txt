cmake_minimum_required(VERSION 4.0)
project(BZFlagDependencies)
include(ExternalProject)
include(sources.cmake)

# Windows
if(MSVC)
	# Change Win32 to x86 to match Visual C++
	if(CMAKE_VS_PLATFORM_NAME STREQUAL "Win32")
		set(DEP_ARCH "x86")
	else()
		set(DEP_ARCH "${CMAKE_VS_PLATFORM_NAME}")
	endif()
	set(OUTPUT_DIR windows-$<IF:$<CONFIG:Debug>,debug,release>-${DEP_ARCH})
	set(OUTPUT_DIR_RELEASE windows-release-${DEP_ARCH})
	set(OUTPUT_DIR_DEBUG windows-debug-${DEP_ARCH})
	set(CURL_TLS "SCHANNEL")

# macOS
elseif(APPLE)
	set(OUTPUT_DIR macOS-$<IF:$<CONFIG:Debug>,debug,release>-arm64-x86_64)
	set(CURL_TLS "OPENSSL")

# Unsupported
else()
	message(FATAL_ERROR "Unsupported platform")
endif()

# Handle copying license files as needed
set(LICENSE_INSTALL_PATH "${CMAKE_SOURCE_DIR}/licenses")
file(MAKE_DIRECTORY "${LICENSE_INSTALL_PATH}")
function(copy_license PROJECT_NAME LICENSE_FILE)
	if(IS_ABSOLUTE "${LICENSE_FILE}")
		set(_source_file "${LICENSE_FILE}")
	else()
		set(_source_file "${CMAKE_BINARY_DIR}/${PROJECT_NAME}/SRC/${PROJECT_NAME}/${LICENSE_FILE}")
	endif()
	add_custom_command(
		TARGET ${PROJECT_NAME} POST_BUILD
		COMMAND ${CMAKE_COMMAND} -E copy_if_different
			"${_source_file}"
			"${LICENSE_INSTALL_PATH}/${PROJECT_NAME}.txt"
		COMMENT "Copying license file for ${PROJECT_NAME}"
		BYPRODUCTS "${LICENSE_INSTALL_PATH}/${PROJECT_NAME}.txt"
	)
endfunction()


##############################################################################
# SDL 2
##############################################################################
set(EP_SDL2 "sdl2")
ExternalProject_Add(${EP_SDL2}
	URL		${SDL_URL}
	URL_HASH	${SDL_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_SDL2}
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
			-DCMAKE_OSX_ARCHITECTURES:STRING=arm64$<SEMICOLON>x86_64
)
copy_license(${EP_SDL2} "LICENSE.txt")


##############################################################################
# GLEW
##############################################################################
set(EP_GLEW "glew")
ExternalProject_Add(${EP_GLEW}
	URL		${GLEW_URL}
	URL_HASH	${GLEW_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_GLEW}
	SOURCE_SUBDIR	build/cmake
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
			-DCMAKE_OSX_ARCHITECTURES:STRING=arm64$<SEMICOLON>x86_64

			-DCMAKE_POLICY_VERSION_MINIMUM=3.5
			-DBUILD_UTILS:BOOL=false
			-DBUILD_SHARED_LIBS:BOOL=false
	# TODO: REMOVE THIS BEFORE MERGING
	#BUILD_COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}/${EP_GLEW}/src/glew-build/ --target glew_s --config $<CONFIG>
)
copy_license(${EP_GLEW} "LICENSE.txt")


##############################################################################
# c-ares
##############################################################################
set(EP_CARES "c-ares")
ExternalProject_Add(${EP_CARES}
	URL		${CARES_URL}
	URL_HASH	${CARES_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_CARES}
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
			-DCMAKE_OSX_ARCHITECTURES:STRING=arm64$<SEMICOLON>x86_64

			-DCARES_BUILD_TOOLS:BOOL=false
)
copy_license(${EP_CARES} "LICENSE.md")


# PDCurses, zlib, curl, and regex are only need to be built for Windows
if(MSVC)

##############################################################################
# PDCurses
##############################################################################
find_program(MAKE_EXE gmake nmake make REQUIRED PATHS ENV PATH)
set(EP_PDCURSES "pdcurses")
ExternalProject_Add(${EP_PDCURSES}
	URL		${PDCURSES_URL}
	URL_HASH	${PDCURSES_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_PDCURSES}
	BUILD_IN_SOURCE	true
	SOURCE_SUBDIR	wincon
	CONFIGURE_COMMAND	""
	BUILD_COMMAND	${MAKE_EXE} -f Makefile.vc $<IF:$<CONFIG:Debug>,DEBUG=Y,> WIDE=Y UTF8=Y pdcurses.lib
	INSTALL_COMMAND	${CMAKE_COMMAND} -E copy "../curses.h" "${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}/include/curses.h"
	        COMMAND	${CMAKE_COMMAND} -E copy "pdcurses.lib" "${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}/lib/pdcurses.lib"
)
copy_license(${EP_PDCURSES} "README.md")


##############################################################################
# zlib
##############################################################################
set(EP_ZLIB "zlib")
ExternalProject_Add(${EP_ZLIB}
	URL		${ZLIB_URL}
	URL_HASH	${ZLIB_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_ZLIB}
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
			-DCMAKE_OSX_ARCHITECTURES:STRING=arm64$<SEMICOLON>x86_64

			# Because zlib's CMake project caches these, we have to unset them here to
			# prevent reusing the path from the config that was first built.
			-UINSTALL_BIN_DIR
			-UINSTALL_LIB_DIR
			-UINSTALL_INC_DIR
			-UINSTALL_MAN_DIR
)
copy_license(${EP_ZLIB} "README")


##############################################################################
# curl
##############################################################################
set(EP_CURL "curl")
ExternalProject_Add(${EP_CURL}
	DEPENDS		${EP_ZLIB} ${EP_CARES}
	URL		${CURL_URL}
	URL_HASH	${CURL_HASH}
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_CURL}
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
			-DCMAKE_OSX_ARCHITECTURES:STRING=arm64$<SEMICOLON>x86_64

			# Enable TLS support
			-DCURL_USE_${CURL_TLS}:BOOL=true

			# Build with zlib support
			-DCURL_ZLIB:BOOL=true
			-DZLIB_INCLUDE_DIR:STRING=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}/include
			-DZLIB_LIBRARY_DEBUG:STRING=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR_DEBUG}/lib/zd.lib
			-DZLIB_LIBRARY_RELEASE:STRING=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR_RELEASE}/lib/z.lib

			# Build with c-ares support
			-DENABLE_ARES:BOOL=true
			-DCARES_INCLUDE_DIR:STRING=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}/include
			-DCARES_LIBRARY:STRING=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}/lib/cares.lib

			# Control which type of library we build
			-DBUILD_SHARED_LIBS:BOOL=true
			-DBUILD_STATIC_CURL:BOOL=false
			-DBUILD_STATIC_LIBS:BOOL=false

			# Remove the default library suffix and switch to using _debug for debug builds
			-DIMPORT_LIB_SUFFIX:STRING=
			-DCMAKE_DEBUG_POSTFIX:STRING=_debug

			# Disable protocols that we don't need
			-DCURL_DISABLE_DICT:BOOL=true
			-DCURL_DISABLE_GOPHER:BOOL=true
			-DCURL_DISABLE_IMAP:BOOL=true
			-DCURL_DISABLE_IPFS:BOOL=true
			-DCURL_DISABLE_KERBEROS_AUTH:BOOL=true
			-DCURL_DISABLE_LDAP:BOOL=true
			-DCURL_DISABLE_LDAPS:BOOL=true
			-DCURL_DISABLE_MQTT:BOOL=true
			-DCURL_DISABLE_NTLM:BOOL=true
			-DCURL_DISABLE_POP3:BOOL=true
			-DCURL_DISABLE_RTSP:BOOL=true
			-DCURL_DISABLE_SMB:BOOL=true
			-DCURL_DISABLE_SMTP:BOOL=true
			-DCURL_DISABLE_TELNET:BOOL=true
			-DCURL_DISABLE_TFTP:BOOL=true

			# Disable some other stuff
			-DCURL_USE_LIBSSH:BOOL=false
			-DCURL_USE_LIBSSH2:BOOL=false
			-DCURL_BROTLI:STRING=OFF
			-DCURL_ZSTD:STRING=OFF
			-DUSE_LIBIDN2:BOOL=false
			-DUSE_NGHTTP2:BOOL=false
			-DCURL_DISABLE_COOKIES:BOOL=true
			-DCURL_USE_LIBPSL:BOOL=false

			# Disable some extra stuff
			-DBUILD_CURL_EXE:BOOL=false
			-DBUILD_LIBCURL_DOCS:BOOL=false
			-DBUILD_MISC_DOCS:BOOL=false
)
copy_license(${EP_CURL} "COPYING")


##############################################################################
# regex
##############################################################################
set(EP_REGEX "regex")
ExternalProject_Add(${EP_REGEX}
	SOURCE_DIR	${CMAKE_CURRENT_SOURCE_DIR}/src/regex/
	PREFIX		${CMAKE_CURRENT_BINARY_DIR}/${EP_REGEX}
	CMAKE_ARGS	-DCMAKE_INSTALL_PREFIX=${CMAKE_SOURCE_DIR}/${OUTPUT_DIR}
)
copy_license(${EP_REGEX} "${CMAKE_CURRENT_SOURCE_DIR}/src/regex/license.txt")

endif() # MSVC
