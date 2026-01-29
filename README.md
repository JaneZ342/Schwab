# Schwab Contact Matching

A Python-based contact matching system that uses fuzzy string matching to reconcile contact records between Schwab and Advyzon datasets. The tool intelligently matches records by name, company, and email with configurable similarity thresholds.

## Features

- **Fuzzy Matching**: Uses token_set_ratio for intelligent name and company matching (threshold: 90% by default)
- **Fast Processing**: Optimized with RapidFuzz (or falls back to fuzzywuzzy)
- **Progress Tracking**: Real-time progress updates during matching
- **Match Scoring**: Includes match confidence scores (0-100) for each record
- **Flexible Configuration**: Customizable similarity thresholds and file paths

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

For faster matching, optionally install RapidFuzz:

```bash
pip install rapidfuzz
```

### 2. Prepare Your Data

Place your Excel files in a known location and update the paths in `scripts/match_raw_data.py`:

```python
Schwab_discovery_path = Path("path/to/Schwab unmatched double check.xlsx")
all_contacts_path = Path("path/to/All Contact.xlsx")
output_path = Path("path/to/unmatched_match.xlsx")
```

Or use environment variables (see Configuration section below).

### 3. File Format Requirements

#### Schwab File
Required columns (flexible naming - system checks multiple variants):
- `First_Name_` or `First Name` or `First`
- `Last_Name_` or `Last Name` or `Last`
- `Business_Name` or `Business Name` or `Company`

#### Contacts File
Required columns (flexible naming - system checks multiple variants):
- `First Name` or `First_Name_` or `First`
- `Last Name` or `Last_Name_` or `Last`
- `Company Name` or `Company` or `Business_Name`

## Usage

### Basic Usage

```bash
python .\scripts\match_raw_data.py
```

This will:
1. Load Schwab and contacts data from configured paths
2. Clean and normalize company names (removes suffixes like Inc, LLC, Corp)
3. Build matching keys from first name + last name + company
4. Perform fuzzy matching (90% threshold by default)
5. Output results to `unmatched_match.xlsx` with two sheets:
   - `in discovery`: Records found in discovery
   - `not in discovery`: Records not found in discovery

### Output Format

Each output sheet contains:
- **Original Schwab columns**: All original data preserved
- **Matched**: Boolean (True/False)
- **Match_Score**: Similarity score (0-100)
- **Adv_* columns**: Matching contact record data (prefixed with `Adv_`)

Example:
```
First_Name_ | Last_Name_ | Business_Name | ... | Matched | Match_Score | Adv_Email | Adv_Phone | ...
Jane        | Doe       | Acme Corp     | ... | True    | 95          | jane@... | 555-...   | ...
John        | Smith     | Tech LLC      | ... | False   | 45          | NULL     | NULL      | ...
```

## Configuration

### File Paths

Edit the top of `scripts/match_raw_data.py` to set your file paths:

```python
# Update these paths to point to your data files
Schwab_file_path = Path(r"C:\Users\YourName\path\to\Schwab unmatched double check.xlsx")
contacts_file_path = Path(r"C:\Users\YourName\path\to\All Contact.xlsx")
output_file_path = Path(r"C:\Users\YourName\path\to\unmatched_match.xlsx")
```

Alternatively, use relative paths if you place files in the repository:

```python
Schwab_file_path = Path("data/Schwab unmatched double check.xlsx")
contacts_file_path = Path("data/All Contact.xlsx")
output_file_path = Path("data/unmatched_match.xlsx")
```

### Matching Threshold

Edit the `threshold` parameter in the function call (bottom of script):

```python
# Default: 90% similarity required to match
matched_in_discovery = match_by_name_and_company(Schwab_discovery, all_contacts, threshold=90)

# More permissive (more matches, some false positives)
matched_in_discovery = match_by_name_and_company(Schwab_discovery, all_contacts, threshold=80)

# Stricter (fewer matches, higher confidence)
matched_in_discovery = match_by_name_and_company(Schwab_discovery, all_contacts, threshold=95)
```

### Column Name Mappings

Customize in `match_by_name_and_company()` function:

```python
# Schwab column options
sw_first = pick_col(sw, ["First_Name_", "First Name", "First name", "First"])
sw_last = pick_col(sw, ["Last_Name_", "Last Name", "Last name", "Last"])
sw_company = pick_col(sw, ["Business_Name", "Business Name", "Company", "Company Name"])

# Contact column options
adv_first = pick_col(adv, ["First Name", "First name", "First", "First_Name_"])
adv_last = pick_col(adv, ["Last Name", "Last name", "Last", "Last_Name_", "Last Name "])
adv_company = pick_col(adv, ["Company Name", "Company", "Business_Name", "Business Name"])
```

### Company Suffix Pattern

Customize which company suffixes are removed:

```python
suffix_pattern = r"\b(inc|llc|ltd|co|corporation|corp|pllc|pc|gmbh|ag|bv|sa|sarl|sas|pte|pty|limited|investment|group)\b"
```

## Matching Algorithm

1. **Data Normalization**:
   - Company names: Remove common suffixes (Inc, LLC, Ltd, Corp, etc.)
   - All text: Lowercase, trim whitespace, remove extra spaces
   
2. **Key Construction**:
   - Format: `{first_name} {last_name} | {clean_company}` (lowercase)
   
3. **Matching Strategy**:
   - Uses `token_set_ratio` for fuzzy matching
   - Lightweight blocking by first letter and length (±30%) on large datasets
   - Default threshold: 90% similarity
   
4. **Candidate Filtering** (for performance):
   - If >500 candidates, filters to only those starting with same letter
   - Further filters by similar length (±30%)
   - Falls back to all candidates if filtering produces no results

## Performance

- **RapidFuzz**: ~3-10x faster than fuzzywuzzy
- **Blocking optimization**: Reduces candidates by 50-90% on large datasets
- Typical runtime: 
  - ~100 records: <1 second
  - ~1,000 records: 5-15 seconds
  - ~10,000 records: 1-5 minutes

## Files

- `scripts/match_raw_data.py`: Main fuzzy matching script (recommended)
- `scripts/match_discovery.py`: Alternative CRD-based matching pipeline (legacy)
- `requirements.txt`: Python dependencies
- `.gitignore`: Git ignore patterns
- `README.md`: This file

## Troubleshooting

### Slow Matching
- Install `rapidfuzz` for 3-10x speed improvement: `pip install rapidfuzz`
- Lower the candidate filter threshold by editing the blocking logic
- Split large datasets into chunks and run separately

### Poor Match Quality

**Too many false positives (high match rate but low confidence)**:
- Increase `threshold` from 90 to 95

**Too few matches (many unmatched records)**:
- Lower `threshold` from 90 to 80 or 85
- Review company name normalization - check if it's too aggressive

**Wrong columns being matched**:
- Verify column names match the expected formats
- Check the `pick_col()` function parameters
- Ensure data is clean (no leading/trailing spaces, consistent casing)

### File Not Found

```
FileNotFoundError: Excel file not found
```

- Verify file path is correct: `ls "C:\path\to\file.xlsx"`
- Use absolute paths or ensure relative paths are from script directory
- Check file isn't open in another program (Excel may lock it)

### Module Import Errors

```
ModuleNotFoundError: No module named 'pandas'
```

Run: `pip install -r requirements.txt`

### Slow SequenceMatcher Warning

```
UserWarning: Using slow pure-python SequenceMatcher. Install python-Levenshtein...
```

Run: `pip install python-Levenshtein`

Or better: `pip install rapidfuzz` (includes C++ optimizations)

## Development

### Adding Custom Matching Logic

Extend the `match_by_name_and_company()` function:

```python
def match_by_name_and_company(Schwab_df, contacts_df, threshold=90, verbose=True):
    # ... existing code ...
    
    # Add email matching before fuzzy matching:
    sw["Email"] = pick_col(sw, ["Email_Address", "Email"])
    adv["Email"] = pick_col(adv, ["Email_", "Email", "Email_Address"])
    
    # ... existing fuzzy logic ...
```

### Running on Large Datasets

For datasets >50,000 rows:

1. **Enable RapidFuzz**: `pip install rapidfuzz`
2. **Increase blocking threshold**: 
   ```python
   if len(candidates) > 500:  # Change to 1000 or more
   ```
3. **Consider parallel processing**: Split data and run multiple instances

## License

[Add your license here - MIT, Apache 2.0, etc.]

## Author

[Your name/email]

## Contributing

[Add contribution guidelines]