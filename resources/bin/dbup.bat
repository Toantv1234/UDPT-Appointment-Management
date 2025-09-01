@echo off

setlocal enabledelayedexpansion

cd .

call :echoStep "Starting Docker containers..."
docker-compose up -d
if !errorlevel! neq 0 (
    call :echoErr "Error starting Docker containers. Exiting script."
    exit /b !errorlevel!
)

call :echoStep "Restarting FastAPI container..."
docker-compose restart fastapi
if !errorlevel! neq 0 (
    call :echoErr "Error restarting FastAPI container. Exiting script."
    exit /b !errorlevel!
)

call :echoSuccess "All services have been initialized successfully!"

REM --- Color echo functions ---
:echoStatus
REM Print [STATUS] in cyan, rest normal
echo|set /p="[36mINFO[0m: "
echo %~1
goto :eof

:echoSuccess
REM Print [SUCCESS] in green, rest normal
echo|set /p="[32mSUCCESS[0m: "
echo %~1
goto :eof

:echoErr
REM Print [ERR] in red,1 rest normal
echo|set /p="[31mERR[0m: "
echo %~1
goto :eof

:echoStep
REM Print [STEP] in yellow, rest normal
echo|set /p="[33mSTEP[0m: "
echo %~1
goto :eof
