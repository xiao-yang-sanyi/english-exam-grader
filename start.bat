@echo off
chcp 65001 >nul
rem 高中英语试卷批改网 - 一键启动并自动打开浏览器
cd /d "%~dp0"

set "PORT=5000"
if not "%~1"=="" set "PORT=%~1"

set "PY="
if exist "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
  set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
) else (
  where python >nul 2>nul && set "PY=python"
)

if "%PY%"=="" (
  echo [错误] 未找到 Python，请安装 Python 3.9+ 后重试。
  pause
  exit /b 1
)

rem 若网站已在运行（端口被占用），直接打开浏览器即可
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo 网站已在运行中，正在打开浏览器...
  start "" "http://127.0.0.1:%PORT%"
  timeout /t 8 /nobreak >nul
  exit /b 0
)

echo 正在启动 高中英语试卷批改网 ...
echo 浏览器将自动打开： http://127.0.0.1:%PORT%
start "" "http://127.0.0.1:%PORT%"
"%PY%" app.py %PORT%
pause
