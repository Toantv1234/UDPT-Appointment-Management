@echo off
setlocal enabledelayedexpansion

call :echoStep "Stopping and removing containers..."
docker-compose down

call :echoStep "Clean up data from containers..."
IF EXIST "resources\logs" (
    for /d %%D in ("resources\logs\*") do rd /s /q "%%D"
    del /q "resources\logs\*"
)

call :echoSuccess "Successfully removed containers and data."


:echoSuccess
REM Print [SUCCESS] in green, rest normal
echo|set /p="[32mSUCCESS[0m: "
echo %~1
goto :eof

:echoStep
REM Print [STEP] in yellow, rest normal
echo|set /p="[33mSTEP[0m: "
echo %~1
goto :eof
