@echo off

:: Adjust this if you have an edition other than Community
set VSEDITION=Community

if not "%DevEnvDir%" == "" (
	echo.
	echo Please do not run from an existing Visual Studio command prompt or with a prompt from a previous run.
	goto:eof
)

set INPUT_ARCH=%1
:: If no architecture is specified, just build the default architectures.
if "%INPUT_ARCH%" == "" (
	start /wait cmd.exe /C %~0 x86
	start /wait cmd.exe /C %~0 x64
	goto:eof
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
echo Invalid architecture specified. Use one of x86, x64, or arm64
pause
goto:eof

:run

if exist "%ProgramFiles%\Microsoft Visual Studio\2017\%VSEDITION%\VC\Auxiliary\Build\vcvarsall.bat" (
	call "%ProgramFiles%\Microsoft Visual Studio\2017\%VSEDITION%\VC\Auxiliary\Build\vcvarsall.bat" %VCVAR_ARCH%
) else if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2017\%VSEDITION%\VC\Auxiliary\Build\vcvarsall.bat" (
	call "%ProgramFiles(x86)%\Microsoft Visual Studio\2017\%VSEDITION%\VC\Auxiliary\Build\vcvarsall.bat" %VCVAR_ARCH%
) else (
	echo Unable to locate vcvarsall.bat, aborting
	pause
	goto:eof
)

cmake -S . -B build/%INPUT_ARCH% -A %CMAKE_ARCH%
set CONFIGURE_STATUS=%ERRORLEVEL%
if %CONFIGURE_STATUS% == 0 (
	cmake --build build/%INPUT_ARCH% --config Debug
	cmake --build build/%INPUT_ARCH% --config Release
)
