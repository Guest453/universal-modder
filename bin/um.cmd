@echo off
rem um.cmd - windows launcher for the universal-modder CLI (no bash needed).
rem usage: um.cmd scan --list | um.cmd fal sprite "..." | um.cmd kb search "terraria"
setlocal
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
python -m um %*
