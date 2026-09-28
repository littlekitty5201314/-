@echo off
REM Video Tracer Agent launcher (ASCII only to avoid codepage issues)
REM Usage: drag a video file onto this bat, or run: run.bat "C:\path\to\video.mp4"
REM Portable: paths are resolved relative to this script's folder (%~dp0).

setlocal

REM Python environment lives in .\venv next to this script.
set "PYTHON=%~dp0venv\Scripts\python.exe"
set "MAIN=%~dp0main.py"

if not exist "%PYTHON%" (
    echo.
    echo Python environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

if "%~1"=="" (
    echo No video file specified.
    echo Tip: drag a video file onto this run.bat icon to run it.
    echo Or run from terminal: run.bat "C:\path\to\video.mp4"
    set /p "VIDEO=Or type the full video path here and press Enter: "
) else (
    set "VIDEO=%~1"
)

if not defined VIDEO goto :end
if "%VIDEO%"=="" goto :end

if not exist "%VIDEO%" (
    echo.
    echo Video file not found: %VIDEO%
    goto :end
)

echo.
echo Running video source tracing...
echo Video: %VIDEO%
echo.

"%PYTHON%" "%MAIN%" "%VIDEO%"

:end
echo.
echo ===== Done. Report is saved in the output folder. =====
pause
endlocal
