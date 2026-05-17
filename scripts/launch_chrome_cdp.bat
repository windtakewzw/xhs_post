@echo off
REM Launch Chrome with CDP port for Patchright anti-detection
REM Chrome 136+ requires non-default user-data-dir for remote debugging

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo [ERROR] Chrome not found. Please install Google Chrome.
    exit /b 1
)

set "CDP_PORT=9222"
set "PROFILE=%~dp0..\accounts\chrome-cdp-profile"

echo [CDP] Stopping existing Chrome...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 3 /nobreak >nul

if not exist "%PROFILE%" mkdir "%PROFILE%"

echo [CDP] Starting Chrome on port %CDP_PORT%...
echo [CDP] Profile: %PROFILE%
start "" "%CHROME%" ^
  --remote-debugging-port=%CDP_PORT% ^
  --user-data-dir="%PROFILE%" ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-features=TranslateUI ^
  --disable-background-networking ^
  --disable-sync

REM Wait for CDP port to come up
echo [CDP] Waiting for port %CDP_PORT%...
for /l %%i in (1,1,30) do (
    curl -s http://127.0.0.1:%CDP_PORT%/json/version >nul 2>&1
    if not errorlevel 1 (
        echo [CDP] Chrome ready on port %CDP_PORT%
        exit /b 0
    )
    timeout /t 1 /nobreak >nul
)
echo [WARN] Chrome started but port %CDP_PORT% not responding after 30s
exit /b 0
