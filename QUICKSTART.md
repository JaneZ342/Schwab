# Quick Start Guide

## For Windows Users (PowerShell)

### 1. Clone and Setup (First Time)
```powershell
git clone https://github.com/YOUR_USERNAME/Schwab.git
cd Schwab
pip install -r requirements.txt
pip install rapidfuzz  # Optional but recommended for speed
```

### 2. Configure Your File Paths

**Option A: Edit the script** (easiest for beginners)
```powershell
# Edit scripts/match_raw_data.py
# Lines 15-20: Update these paths to your files
$EDITOR scripts/match_raw_data.py
```

**Option B: Use environment variables** (cleaner)
```powershell
set SCHWAB_FILE=C:\path\to\Schwab unmatched double check.xlsx
set CONTACTS_FILE=C:\path\to\All Contact.xlsx
set OUTPUT_FILE=C:\path\to\output\unmatched_match.xlsx
```

**Option C: Copy .env template**
```powershell
copy .env.example .env
# Edit .env with your paths
```

### 3. Run the Matching
```powershell
python .\scripts\match_raw_data.py
```

You'll see progress updates:
```
[INFO] Loading Schwab data...
[INFO] Loaded 500 rows from 'in discovery'
[INFO] Starting fuzzy match with 500 Schwab rows vs 10000 contacts (threshold=90%)
[PROGRESS] Processed 50/500 rows (10%)
[PROGRESS] Processed 100/500 rows (20%)
...
[INFO] Fuzzy matching complete: 450/500 rows matched (~90%)
[INFO] Done! Output saved to: C:\path\to\output\unmatched_match.xlsx
```

### 4. Check Results

Open the generated Excel file with two sheets:
- **in discovery**: Records matched in the discovery set
- **not in discovery**: Records not in discovery set

Each row has:
- **Matched**: True/False
- **Match_Score**: 0-100 (higher = better match)
- **Adv_* columns**: Contact data for matched records

## For Linux/Mac Users

### 1. Clone and Setup
```bash
git clone https://github.com/YOUR_USERNAME/Schwab.git
cd Schwab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install rapidfuzz  # Optional
```

### 2. Configure Paths
```bash
export SCHWAB_FILE=/path/to/Schwab unmatched double check.xlsx
export CONTACTS_FILE=/path/to/All Contact.xlsx
export OUTPUT_FILE=/path/to/output/unmatched_match.xlsx
```

Or create `.env` file:
```bash
cp .env.example .env
nano .env  # Edit with your paths
```

### 3. Run
```bash
python scripts/match_raw_data.py
```

## Adjusting Match Sensitivity

### More Matches (Risk: Some False Positives)
Edit line in `scripts/match_raw_data.py`:
```python
threshold=80  # Down from 90
```

### Stricter Matches (Risk: Some Real Matches Missed)
```python
threshold=95  # Up from 90
```

## Troubleshooting

### "File not found" Error
```
[ERROR] Schwab file not found: C:\path\to\file.xlsx
```
**Solution**: Verify the path exists and file isn't open in Excel

### Slow Performance
**Solution**: Install RapidFuzz:
```powershell
pip install rapidfuzz
```

### Different Column Names
Edit the column mapping in `match_raw_data.py`:
```python
sw_first = pick_col(sw, ["First_Name_", "First Name", "First"])
# Add more column name variants if needed
```

## Next Steps

- Review the full [README.md](README.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) if you want to improve the tool
- See [GITHUB_READY_CHANGES.md](GITHUB_READY_CHANGES.md) for technical details

## Need Help?

1. Check [README.md - Troubleshooting](README.md#troubleshooting)
2. Review your file paths carefully
3. Ensure Excel files have the expected sheet names
4. Check column names match the expected formats
5. Try with a small sample first