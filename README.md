# trading_pattern_recognition

Scripts for collecting chart pattern images into `data/raw/<pattern_name>`.

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\scraper\download_patterns.py --per-pattern 10
```

Clean the raw dataset into `data/processed/clean` and quarantine suspicious files:

```powershell
.\.venv\Scripts\python.exe .\scripts\dataset\clean_dataset.py --reset-output
```

Popular pattern folders are created under `data/raw`, for example:

- `data/raw/head_and_shoulders`
- `data/raw/bullish_triange`
- `data/raw/bearish_triangle`
- `data/raw/double_top`
- `data/raw/cup_and_handle`
