@echo off
setlocal enabledelayedexpansion

REM Define the Git for Windows download URL
set GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.1/Git-2.42.0-64-bit.exe

REM Download the Git installer
echo Downloading Git for Windows installer...
curl -L -o git_installer.exe %GIT_URL%

REM Run the installer in silent mode
echo Running the Git installer...
start /wait git_installer.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES

REM Clean up the installer file
echo Cleaning up the installer...
del git_installer.exe

REM Check and display the installed Git version
echo Git installation completed. Installed Git version:
git --version

pause
