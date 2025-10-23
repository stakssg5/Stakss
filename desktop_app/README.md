# Forensic Search Desktop App

A simple desktop application that:
- Shows a login screen (credentials in `config.json`)
- Lets you search a local SQLite database of random people
- Automatically plays a forensic demo video whenever a search occurs
 - Includes a Geo tab to browse/search landmarks, government roles, and locals by country
 - Includes a Cameras tab to catalog/search lawful public or user-provided streams and play them
 - People can be linked with specific cameras (authorized/private) for quick access (no unauthorized access)

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

## Geo features
- Countries, landmarks, and sample government roles are seeded on first run.
- Use the Geo tab:
  - Select a country or keep "All countries".
  - Type to search landmarks (left), government officials (middle), and locals (right).
  - The video auto-plays with each search.

## Deleting records
- People tab: select one or more rows and click "Delete selected".
- Geo tab:
  - Landmarks list: select and click "Delete landmarks".
  - Government list: select and click "Delete government".
  - Locals list: select and click "Delete locals".

## Cameras (lawful catalog)
- Catalog public or permissioned camera streams; no scanning/hacking.
- Cameras tab:
  - Filter by country, public-only, fixed-only.
  - Search by name/location; select to play.
  - Add camera: provide name, location (optional), country, and URL/file path.
  - Delete selected cameras.
  - Sample demo entries use the local `resources/forensic.mp4` to illustrate playback.

## Linking private/authorized cameras
- Link cameras to a person record for quick access:
  - In People tab: select a person.
  - In Cameras tab: select a camera.
  - Back in People tab: click "Link selected camera from Cameras tab" to associate it.
  - Select linked entries and click "Unlink selected" to remove association.
- Important: Only add and link cameras you own or are authorized to access. This app does not scan or bypass protections.
