# Forensic Search Desktop App

A simple desktop application that:
- Shows a login screen (credentials stored in user config)
- Lets you search a local SQLite database of random people
- Automatically plays a forensic demo video whenever a search occurs
 - Includes a Geo tab to browse/search landmarks, government roles, and locals by country
 - Includes a Cameras tab to catalog/search lawful public or user-provided streams and play them
 - People can be linked with specific cameras (authorized/private) for quick access (no unauthorized access)
 - Geolocate tab: approximate IP/domain geolocation lookup via a public provider

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

### Settings persistence (even one-file EXE)
- Settings are stored per user in the OS config directory:
  - Windows: `%APPDATA%/ForensicSearch/config.json`
  - macOS: `~/Library/Application Support/ForensicSearch/config.json`
  - Linux: `~/.config/ForensicSearch/config.json`
- On first run, the app seeds from the bundled `config.json`.
- Use Settings → Credentials… to change username/password; changes persist.

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

## Geolocation (approximate)
- Purpose: given an IP or domain, fetch approximate location data (city/region/country, lat/lon when available) from a public geolocation API.
- Configure provider in `config.json` under `geolocation` (default: `ipapi.co`).
- Open the Geolocate tab, enter IP/domain, and click Lookup.
- Notes:
  - Accuracy varies; results can be approximate or stale.
  - Respect privacy and applicable laws; do not misuse location data.

## Linking private/authorized cameras
- Link cameras to a person record for quick access:
  - In People tab: select a person.
  - In Cameras tab: select a camera.
  - Back in People tab: click "Link selected camera from Cameras tab" to associate it.
  - Select linked entries and click "Unlink selected" to remove association.
- Important: Only add and link cameras you own or are authorized to access. This app does not scan or bypass protections.
