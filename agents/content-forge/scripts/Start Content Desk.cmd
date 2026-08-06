@echo off
title Matrixly Content Desk
cd /d "%~dp0\.."
echo.
echo  Matrixly Content Desk — one-click setup
echo  You will only be asked for business details and optional keys.
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo  Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
  echo  Check "Add python.exe to PATH" during install, then run this again.
  echo.
  pause
  exit /b 1
)
python scripts\bootstrap.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo  Setup finished with an error. You can retry or contact support.
  pause
)
exit /b %EXITCODE%
