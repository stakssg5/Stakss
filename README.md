## Safe demo: colorful Python CLI extractor

This repository includes a safe Python script that mimics the look-and-feel of the screenshot you shared (colored `[TAGS]`, sequential logs), but performs a legitimate task locally:

- Initializes a small SQLite database with fake sample users
- Reads a specified number of rows using parameterized (safe) queries
- Writes results to a CSV file

### Files
- `safe_sqlite_extractor.py`: the CLI tool
- `demo_users.db`: generated SQLite database (created on first run or with `--init-db`)
- `extracted_users.csv`: output CSV

### Prerequisites
- Python 3.8+

### Usage

Initialize the demo database and extract 5 rows:

```bash
python3 safe_sqlite_extractor.py --init-db --count 5
```

Extract 10 rows, waiting 3.5s between each, writing to a custom CSV:

```bash
python3 safe_sqlite_extractor.py -n 10 -w 3.5 -o my_users.csv
```

Use a custom database path:

```bash
python3 safe_sqlite_extractor.py -d data/demo.db -n 3
```

### Notes
- The data is randomly generated and not real.
- Queries are parameterized to demonstrate safe database access.
- This is for educational purposes only.
