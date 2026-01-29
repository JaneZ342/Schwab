# Contributing to Schwab Contact Matching

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Schwab.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt`

## Development Setup

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies including optional ones
pip install -r requirements.txt
pip install rapidfuzz  # For speed
pip install pytest     # For testing (if adding tests)
```

## Configuration for Local Development

Create a `.env` file in the repository root:

```bash
cp .env.example .env
# Edit .env with your local file paths
```

## Making Changes

1. **Follow the existing code style**:
   - Use clear variable names
   - Add docstrings to functions
   - Keep functions focused and small
   - Add comments for complex logic

2. **Test your changes**:
   - Run with sample data
   - Check both sheets in output
   - Verify match scores make sense
   - Test with different thresholds

3. **Update documentation**:
   - If adding features, update README.md
   - Add inline code comments
   - Update this file if process changes

## Submitting Changes

1. Commit with clear messages:
   ```bash
   git add .
   git commit -m "Add feature: descriptive message"
   ```

2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Create a Pull Request with:
   - Clear description of changes
   - Why the change is needed
   - Any new dependencies added
   - Testing performed

## Reporting Issues

When reporting bugs, please include:
- Python version
- Pandas version
- Sample data structure (without sensitive info)
- Error message and traceback
- Steps to reproduce

## Code Guidelines

### Imports
```python
import pandas as pd
import os
from pathlib import Path
try:
    from rapidfuzz import fuzz, process
except ImportError:
    from fuzzywuzzy import fuzz, process
```

### Function Documentation
```python
def match_by_name_and_company(Schwab_df, contacts_df, threshold: int = 90, verbose: bool = True):
    """Fuzzy match Schwab rows to contacts by First + Last + cleaned company.
    
    Args:
        Schwab_df (pd.DataFrame): Schwab contact records
        contacts_df (pd.DataFrame): Advyzon contact records
        threshold (int): Minimum match score (0-100). Default 90.
        verbose (bool): Print progress updates. Default True.
        
    Returns:
        pd.DataFrame: Combined data with match results and scoring
        
    Raises:
        ValueError: If required columns not found
    """
```

### Error Handling
```python
try:
    df = pd.read_excel(file_path)
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    raise
except Exception as e:
    logger.error(f"Error reading file: {e}")
    raise
```

## Performance Optimization

When optimizing:
1. Profile before and after with sample data
2. Document what you changed and why
3. Ensure results are still correct
4. Update README if performance characteristics change

## Adding Dependencies

Before adding new dependencies:
1. Check if pandas/fuzzywuzzy already provide the functionality
2. Ensure it's actively maintained
3. Add to both `requirements.txt` and `README.md`
4. Document why it's needed

## Testing Checklist

Before submitting a PR:
- [ ] Matches produce reasonable scores
- [ ] Progress messages are clear
- [ ] Output Excel file is valid
- [ ] No new warnings on import
- [ ] Works with both RapidFuzz and fuzzywuzzy
- [ ] Handles missing columns gracefully
- [ ] Works on Windows (primary) and Unix paths

## Questions?

- Check existing issues and discussions
- Review the README for common questions
- Look at recent commits for patterns
- Ask in a new issue with [QUESTION] tag

Thank you for contributing!