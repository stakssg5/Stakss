@echo off
setlocal

REM Build Windows executable using PyInstaller
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Include multimedia plugins by collecting PySide6 data
REM To make config writable/sharable, you may prefer one-folder (remove --onefile)
pyinstaller --noconfirm ^
  --name ForensicSearch ^
  --onefile ^
  --add-data "config.json;." ^
  --add-data "resources\\forensic.mp4;resources" ^
  --add-data "resources\\*.png;resources" ^
  --add-data "resources\\*.jpg;resources" ^
  --add-data "resources\\*.jpeg;resources" ^
  --collect-all PySide6 ^
  main.py

echo Build complete. Dist located at %CD%\dist
endlocal
