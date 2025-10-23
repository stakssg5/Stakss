# Forensic Search Desktop App

A simple desktop application that:
- Shows a login screen (credentials in `config.json`)
- Lets you search a local SQLite database of random people
- Automatically plays a forensic demo video whenever a search occurs

## Run (Linux/Mac)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Run (Windows)
```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build Windows EXE
```bat
build_windows.bat
```

Place a demo video at `resources/forensic.mp4` (or change the path in `config.json`).
