@echo off
REM Copyright 2025 Google LLC
REM
REM Licensed under the Apache License, Version 2.0 (the "License");
REM you may not use this file except in compliance with the License.
REM You may obtain a copy of the License at
REM
REM     http://www.apache.org/licenses/LICENSE-2.0
REM
REM Unless required by applicable law or agreed to in writing, software
REM distributed under the License is distributed on an "AS IS" BASIS,
REM WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
REM See the License for the specific language governing permissions and
REM limitations under the License.
REM
REM SPDX-License-Identifier: Apache-2.0

REM Genkit Chat - Windows Run Script
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"

REM Parse command
set "CMD=%~1"
if "%CMD%"=="" set "CMD=help"

goto :%CMD% 2>nul || goto :unknown

:help
echo.
echo Genkit Chat - Multi-model AI Chat Application (Windows)
echo.
echo Usage: genkit-chat.bat [command] [options]
echo.
echo Commands:
echo     start       Run backend (DevUI) and frontend concurrently
echo     dev         Run backend with Genkit DevUI
echo     backend     Run backend only
echo     frontend    Run frontend development server
echo     build       Build frontend for production
echo     lint        Run lint and type checks on backend code
echo     test        Run backend integration tests
echo     stop        Stop all running services
echo     help        Show this help message
echo.
echo Backend Options:
echo     --framework robyn^|fastapi   Web framework to use (default: robyn)
echo     --port PORT                 Server port (default: 8080)
echo.
echo Environment Variables:
echo     GEMINI_API_KEY          Gemini API key (recommended for Google AI)
echo     ANTHROPIC_API_KEY       Anthropic API key (optional)
echo     OPENAI_API_KEY          OpenAI API key (optional)
echo     OLLAMA_HOST             Ollama server URL (default: http://localhost:11434)
echo.
echo Examples:
echo     genkit-chat.bat start
echo     genkit-chat.bat dev --framework fastapi
echo     genkit-chat.bat backend --framework robyn
echo     genkit-chat.bat lint
echo     genkit-chat.bat test
echo.
goto :eof

:check_python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 is required but not installed.
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do echo [OK] Python found: %%a
goto :eof

:check_uv
where uv >nul 2>&1
if errorlevel 1 (
    echo [WARN] uv not found. Installing...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
for /f "tokens=*" %%a in ('uv --version 2^>^&1') do echo [OK] uv found: %%a
goto :eof

:check_node
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 24+ is required for frontend.
    echo Install from: https://nodejs.org
    exit /b 1
)
for /f "tokens=*" %%a in ('node --version 2^>^&1') do echo [OK] Node.js found: %%a
goto :eof

:check_genkit_cli
where genkit >nul 2>&1
if errorlevel 1 (
    echo [WARN] Genkit CLI not found. Installing...
    pnpm add -g genkit
)
echo [OK] Genkit CLI found
goto :eof

:setup_backend
echo [INFO] Setting up backend...
cd /d "%BACKEND_DIR%"

if not exist ".venv" (
    uv venv
    echo [OK] Created virtual environment
)

uv sync --group test
echo [OK] Backend dependencies installed
goto :eof

:dev
set "FRAMEWORK=robyn"
:parse_dev_args
if "%~2"=="" goto :run_dev
REM Handle --framework=VALUE format
set "ARG=%~2"
if "%ARG:~0,12%"=="--framework=" (
    set "FRAMEWORK=%ARG:~12%"
    shift
    goto :parse_dev_args
)
REM Handle --framework VALUE format
if "%~2"=="--framework" (
    set "FRAMEWORK=%~3"
    shift
    shift
    goto :parse_dev_args
)
shift
goto :parse_dev_args

:run_dev
echo [INFO] Starting Genkit Chat with DevUI (%FRAMEWORK%)...
call :check_python
if errorlevel 1 exit /b 1
call :check_uv
call :check_genkit_cli
call :setup_backend

echo [INFO] DevUI will be available at http://localhost:4000
echo [INFO] API will be available at http://localhost:8080

cd /d "%BACKEND_DIR%"
call .venv\Scripts\activate.bat
genkit start -- python src/main.py --framework %FRAMEWORK%
goto :eof

:backend
set "FRAMEWORK=robyn"
set "PORT=8080"
:parse_backend_args
if "%~2"=="" goto :run_backend
REM Handle --framework=VALUE format
set "ARG=%~2"
if "%ARG:~0,12%"=="--framework=" (
    set "FRAMEWORK=%ARG:~12%"
    shift
    goto :parse_backend_args
)
REM Handle --framework VALUE format
if "%~2"=="--framework" (
    set "FRAMEWORK=%~3"
    shift
    shift
    goto :parse_backend_args
)
REM Handle --port=VALUE format
if "%ARG:~0,7%"=="--port=" (
    set "PORT=%ARG:~7%"
    shift
    goto :parse_backend_args
)
REM Handle --port VALUE format
if "%~2"=="--port" (
    set "PORT=%~3"
    shift
    shift
    goto :parse_backend_args
)
shift
goto :parse_backend_args

:run_backend
echo [INFO] Starting backend with %FRAMEWORK% on port %PORT%...
call :check_python
if errorlevel 1 exit /b 1
call :check_uv
call :setup_backend

cd /d "%BACKEND_DIR%"
call .venv\Scripts\activate.bat
python src/main.py --framework %FRAMEWORK% --port %PORT%
goto :eof

:frontend
echo [INFO] Starting frontend development server...
call :check_node
if errorlevel 1 exit /b 1

cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    pnpm install
)
pnpm start
goto :eof

:build
echo [INFO] Building frontend for production...
call :check_node
if errorlevel 1 exit /b 1

cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    pnpm install
)
pnpm run build
echo [OK] Frontend built to frontend/dist/
goto :eof

:lint
echo [INFO] Running lint checks...
call :check_python
if errorlevel 1 exit /b 1
call :check_uv
call :setup_backend

cd /d "%BACKEND_DIR%"

echo [INFO] Running ruff check...
uv run --with ruff ruff check src/ tests/
if errorlevel 1 (
    echo [ERROR] Ruff lint check failed!
    echo Run: cd backend ^&^& uv run --with ruff ruff check --fix src/ tests/
    exit /b 1
)
echo [OK] Ruff lint check passed

echo [INFO] Running ruff format check...
uv run --with ruff ruff format --check src/ tests/
if errorlevel 1 (
    echo [ERROR] Ruff format check failed!
    echo Run: cd backend ^&^& uv run --with ruff ruff format src/ tests/
    exit /b 1
)
echo [OK] Ruff format check passed

echo [INFO] Running pyright type check...
uv run --with pyright pyright src/ tests/
if errorlevel 1 (
    echo [ERROR] Pyright type check failed!
    exit /b 1
)
echo [OK] Pyright type check passed

echo [OK] All lint checks passed!
goto :eof

:test
echo [INFO] Running backend integration tests...
call :check_python
if errorlevel 1 exit /b 1
call :check_uv
call :setup_backend

cd /d "%BACKEND_DIR%"
uv run --group test pytest tests/ -v
goto :eof

:start
set "FRAMEWORK=robyn"
:parse_start_args
if "%~2"=="" goto :run_start
REM Handle --framework=VALUE format
set "ARG=%~2"
if "%ARG:~0,12%"=="--framework=" (
    set "FRAMEWORK=%ARG:~12%"
    shift
    goto :parse_start_args
)
REM Handle --framework VALUE format
if "%~2"=="--framework" (
    set "FRAMEWORK=%~3"
    shift
    shift
    goto :parse_start_args
)
shift
goto :parse_start_args

:run_start
echo [INFO] Starting Genkit Chat (Backend + Frontend) with %FRAMEWORK%...
call :check_python
if errorlevel 1 exit /b 1
call :check_uv
call :check_node
if errorlevel 1 exit /b 1
call :check_genkit_cli
call :setup_backend

REM Setup frontend
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    pnpm install
)

echo [INFO] Starting services...
echo [INFO] DevUI: http://localhost:4000
echo [INFO] Backend API: http://localhost:8080
echo [INFO] Frontend: http://localhost:4200

REM Start backend in background
start "Genkit Backend" cmd /c "cd /d %BACKEND_DIR% && .venv\Scripts\activate.bat && genkit start -- python src/main.py --framework %FRAMEWORK%"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in foreground
cd /d "%FRONTEND_DIR%"
pnpm start
goto :eof

:stop
echo [INFO] Stopping all Genkit Chat services...
REM Kill processes on common ports
for %%p in (8080 4000 4001 4034 4200) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%p ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
        if not errorlevel 1 echo [OK] Killed process on port %%p
    )
)
echo [OK] Services stopped
goto :eof

:unknown
echo [ERROR] Unknown command: %CMD%
call :help
exit /b 1
