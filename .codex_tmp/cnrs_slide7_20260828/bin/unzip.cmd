@echo off
if "%~1"=="-Z1" (
  tar -tf "%~2"
  exit /b %ERRORLEVEL%
)
if "%~1"=="-p" (
  tar -xOf "%~2" "%~3"
  exit /b %ERRORLEVEL%
)
exit /b 2
