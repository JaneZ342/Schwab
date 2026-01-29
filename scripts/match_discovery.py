import pandas as pd
from pathlib import Path
import argparse
import json
import logging
import re
import os
from typing import Tuple, Optional

from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION: Update these paths or use environment variables
# ============================================================================
DEFAULT_EXCEL = Path(os.getenv(
    "ADVYZON_FILE",
    r"C:\Users\Jane\Desktop\Contact Data Checked by Discovery\Advyzon Contacts 10-24 (1).xlsx"
))
SCHWAB_EXCEL = Path(os.getenv(
    "SCHWAB_MATCHED_FILE",
    r"C:\Users\Jane\Desktop\Schwab\Schwab IMPACT 2025 Post Attendee matched and unmatched list.xlsx"
))
# ============================================================================

SCHWAB_MATCH_SHEET = "Contact in Discovery"
SCHWAB_UNMATCH_SHEET = "Contact not in discovery"
ADVY_MATCH_SHEET = "Revised dups in discovery"
ADVY_UNMATCH_SHEET = "Revised dups not in discovery"


def normalize_company_name(name: str) -> str:
    """Normalize company name: remove suffixes, lowercase, clean whitespace."""
    if not name:
        return ''
    s = str(name).strip().lower()
    s = re.sub(r"[^\w\s]", ' ', s)
    s = re.sub(r"\b(?:inc|llc|ltd|corp|co|group|pllc|pl|pc|pa|pcs|service|investment|management)\b\.?$", '', s).strip()
    s = re.sub(r"\s+", ' ', s).strip()
    return s


def load_excel_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    logger.info(f"Loaded {len(df)} rows from {sheet_name} in {file_path.name}")
    return df


def extract_sheet1_schema(excel_path: Path, out_dir: Path) -> None:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    try:
        df = pd.read_excel(excel_path, sheet_name='Sheet1', engine='openpyxl')
        sheet_name = 'Sheet1'
    except ValueError:
        df = pd.read_excel(excel_path, sheet_name=0, engine='openpyxl')
        sheet_name = df.columns.name or 'Sheet1'
    columns = list(df.columns.astype(str))
    dtypes = {str(col): str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    schema = {
        'source_file': str(excel_path),
        'sheet': sheet_name,
        'row_count': len(df),
        'column_count': len(columns),
        'columns': columns,
        'dtypes': dtypes,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    schema_path = out_dir / 'sheet1_schema.json'
    with schema_path.open('w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2)
    sample_path = out_dir / 'sheet1_sample.csv'
    df.head(100).to_csv(sample_path, index=False)
    logger.info(f"Wrote schema to: {schema_path} and sample to: {sample_path}")


def match_contacts_by_crd_and_email(all_contacts: pd.DataFrame, schwab_table: pd.DataFrame,
                                   crd_col: str = 'MatchedRepCRD',
                                   adv_email_col: str = 'Email_',
                                   adv_id_col_hint: str = 'Record_ID') -> pd.DataFrame:
    """
    CRD-based merge with duplicate handling:
    - One-to-one match: each Schwab row maps to at most one Advyzon row
    - For duplicate CRD matches (multiple Adv rows per CRD), pick best by email match, else random
    - Output: original Schwab rows + 4 match columns (Matched_or_not, Match_Score, adv_Email_, adv_Record_ID)
    """
    # Find best Advyzon row per CRD (if duplicates exist)
    adv = all_contacts.copy()
    sw = schwab_table.copy()
    
    # Determine actual ID column name in Advyzon
    adv_id_col = None
    for candidate in (adv_id_col_hint, 'Record_ID', 'RecordID', 'Record Id', 'ID'):
        if candidate in adv.columns:
            adv_id_col = candidate
            break
    # Determine CRD column name in Advyzon (check for common variants)
    adv_crd_col = None
    for candidate in ('CRD', 'Rep_CRD', 'RepCRD', 'MatchedRepCRD', 'Matched_CRD'):
        if candidate in adv.columns:
            adv_crd_col = candidate
            break

    # Determine actual Adv email column if default not present (check common variants)
    if adv_email_col not in adv.columns:
        for cand in ('Email_', 'Email', 'Email Address', 'Email_Address', 'EmailAddress'):
            if cand in adv.columns:
                adv_email_col = cand
                break
    
    # If no CRD column found in Advyzon, check Schwab for the column name to use
    if adv_crd_col is None:
        logger.warning(f"No CRD column found in Advyzon. Available columns: {list(adv.columns[:10])}")
        # Fallback: return Schwab with unmatched status
        result = sw.copy()
        result['Matched_or_not'] = 'unmatched'
        result['Match_Score'] = 0
        result['adv_Email_'] = None
        result['adv_Record_ID'] = None
        return result
    
    # Normalize emails for comparison
    if adv_email_col not in adv.columns:
        adv[adv_email_col] = ''
    adv['_email_norm'] = adv[adv_email_col].fillna('').astype(str).str.strip().str.lower()
    
    if 'Email_Address' not in sw.columns:
        sw['Email_Address'] = ''
    sw['_email_norm'] = sw['Email_Address'].fillna('').astype(str).str.strip().str.lower()
    
    # For each CRD, pick best Advyzon row
    # Group Advyzon by CRD, pick best within each group (email match first, then random)
    best_adv_per_crd = {}
    for crd, group in adv.groupby(adv_crd_col, dropna=False):
        if pd.isna(crd):
            continue
        # If multiple rows with same CRD, pick one with email if available, else first
        if len(group) > 1:
            with_email = group[group['_email_norm'] != '']
            if len(with_email) > 0:
                best_adv_per_crd[crd] = with_email.iloc[0]
            else:
                best_adv_per_crd[crd] = group.iloc[0]
        else:
            best_adv_per_crd[crd] = group.iloc[0]
    
    # Start with original Schwab table (preserves row count and order)
    result = sw[['Email_Address']].copy()  # Keep original Email_Address for reference
    result['Matched_or_not'] = 'unmatched'
    result['Match_Score'] = 0
    result['adv_Email_'] = None
    result['adv_Record_ID'] = None
    
    # Merge: for each Schwab row, look up matching Advyzon by CRD
    if 'Matched_CRD' in sw.columns:
        for idx, sw_row in sw.iterrows():
            crd = sw_row.get('Matched_CRD')
            if pd.notna(crd) and crd in best_adv_per_crd:
                adv_row = best_adv_per_crd[crd]
                result.at[idx, 'Matched_or_not'] = 'matched_crd'
                result.at[idx, 'Match_Score'] = 100
                result.at[idx, 'adv_Email_'] = adv_row.get(adv_email_col)
                if adv_id_col:
                    # store as string to avoid Excel scientific notation
                    rec_id = adv_row.get(adv_id_col)
                    if pd.notna(rec_id):
                        result.at[idx, 'adv_Record_ID'] = str(int(rec_id)) if isinstance(rec_id, (int, float)) and not isinstance(rec_id, bool) else str(rec_id)
    
    # Prepend original Schwab columns, then the 4 match columns
    result = pd.concat([sw.drop(columns=['_email_norm'], errors='ignore'),
                        result[['Matched_or_not', 'Match_Score', 'adv_Email_', 'adv_Record_ID']]], axis=1)
    # Ensure adv_Record_ID is string/object to prevent Excel scientific notation
    # Replace missing values with None without calling fillna(None)
    result['adv_Record_ID'] = result['adv_Record_ID'].astype('object')
    result['adv_Record_ID'] = result['adv_Record_ID'].where(result['adv_Record_ID'].notna(), None)
    
    logger.info(f"CRD matching completed: {(result['Matched_or_not'] == 'matched_crd').sum()} matched out of {len(result)}")
    return result


def match_unmatched_by_email_then_fuzzy(all_contacts: pd.DataFrame, schwab_table: pd.DataFrame,
                                       adv_email_col: str = 'Email_', schwab_email_col: str = 'Email_Address',
                                       schwab_email_domain_col: str = 'Email_Domain',
                                       adv_first_col: str = 'First_Name_', adv_last_col: str = 'Last_Name_', adv_company_col: str = 'Company_Name',
                                       schwab_first_col: str = 'First_Name_', schwab_last_col: str = 'Last_Name_', schwab_company_col: str = 'Business_Name',
                                       threshold: int = 80) -> pd.DataFrame:
    adv = all_contacts.copy()
    sw = schwab_table.copy()
    def _col_series(df: pd.DataFrame, col: str) -> pd.Series:
        return df[col] if col in df.columns else pd.Series([''] * len(df), index=df.index)
    adv['_email_norm'] = _col_series(adv, adv_email_col).fillna('').astype(str).str.strip().str.lower()
    adv['_used'] = False
    sw['_email_norm'] = _col_series(sw, schwab_email_col).fillna('').astype(str).str.strip().str.lower()
    final_rows = []
    for idx_s, sw_row in sw.iterrows():
        sw_idx = sw_row.name
        sw_email_norm = sw_row.get('_email_norm', '')
        adv_matches = adv[(adv['_email_norm'] == sw_email_norm) & (adv['_used'] == False)]
        if (sw_email_norm != '') and (len(adv_matches) > 0):
            adv_idx = adv_matches.index[0]
            adv_row = adv.loc[adv_idx]
            adv.at[adv_idx, '_used'] = True
            adv_data = {k: v for k, v in adv_row.to_dict().items() if not str(k).startswith('_')}
            rec = {f'adv_{k}': v for k, v in adv_data.items()}
            rec.update({f'schwab_{k}': v for k, v in sw_row.to_dict().items()})
            rec['schwab__index'] = sw_idx
            rec['Matched_or_not'] = 'email_matched'
            rec['Match_Score'] = 100
            final_rows.append(rec)
            continue
        sw_first = str(sw_row.get(schwab_first_col, '')).strip().lower()
        sw_last = str(sw_row.get(schwab_last_col, '')).strip().lower()
        sw_company = normalize_company_name(sw_row.get(schwab_company_col, ''))
        sw_key = f"{sw_first} {sw_last} {sw_company}".strip()
        sw_email_domain = str(sw_row.get(schwab_email_col, '')).split('@')[-1].lower() if '@' in str(sw_row.get(schwab_email_col, '')) else ''
        
        # Blocking: only compare against adv rows with matching email domain or name initials
        best_score = 0
        best_adv_idx: Optional[int] = None
        unused_adv = adv[adv['_used'] == False]
        
        # If Schwab has email domain, prioritize candidates with same domain
        candidates = unused_adv
        if sw_email_domain:
            adv_domains = unused_adv[adv_email_col].fillna('').astype(str).str.split('@').str[-1].str.lower()
            domain_match = unused_adv[adv_domains == sw_email_domain]
            if len(domain_match) > 0:
                candidates = domain_match
        
        # If still many candidates, filter by name initials (first letter of first+last name)
        if len(candidates) > 100 and sw_first and sw_last:
            sw_initials = (sw_first[0] + sw_last[0]).lower()
            adv_initials = (unused_adv[adv_first_col].fillna('').astype(str).str[0].str.lower() + 
                          unused_adv[adv_last_col].fillna('').astype(str).str[0].str.lower())
            candidates = unused_adv[adv_initials == sw_initials]
            if len(candidates) == 0:
                candidates = unused_adv  # fallback if no initials match
        
        for idx_a, adv_row in candidates.iterrows():
            adv_first = str(adv_row.get(adv_first_col, '')).strip().lower()
            adv_last = str(adv_row.get(adv_last_col, '')).strip().lower()
            adv_company = normalize_company_name(adv_row.get(adv_company_col, ''))
            adv_key = f"{adv_first} {adv_last} {adv_company}".strip()
            score = fuzz.token_set_ratio(sw_key, adv_key)
            if score > best_score:
                best_score = score
                best_adv_idx = idx_a
        if best_score >= threshold and best_adv_idx is not None:
            best_adv = adv.loc[best_adv_idx]
            adv.at[best_adv_idx, '_used'] = True
            adv_data = {k: v for k, v in best_adv.to_dict().items() if not str(k).startswith('_')}
            rec = {f'adv_{k}': v for k, v in adv_data.items()}
            rec.update({f'schwab_{k}': v for k, v in sw_row.to_dict().items()})
            rec['schwab__index'] = sw_idx
            rec['Matched_or_not'] = 'fuzzy_matched'
            rec['Match_Score'] = int(best_score)
            final_rows.append(rec)
        else:
            adv_cols = [c for c in adv.columns if not str(c).startswith('_')]
            rec = {f'adv_{k}': None for k in adv_cols}
            rec.update({f'schwab_{k}': v for k, v in sw_row.to_dict().items()})
            rec['schwab__index'] = sw_idx
            rec['Matched_or_not'] = 'unmatched'
            rec['Match_Score'] = 0
            final_rows.append(rec)
    result = pd.DataFrame(final_rows)
    if schwab_email_domain_col in sw.columns and f'schwab_{schwab_email_domain_col}' not in result.columns:
        result[f'schwab_{schwab_email_domain_col}'] = sw[schwab_email_domain_col].values
    logger.info(f"Email+fuzzy matching completed: {len(result)} schwab rows processed")
    return result


def load_default_tables() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    adv_matched = load_excel_sheet(DEFAULT_EXCEL, ADVY_MATCH_SHEET)
    adv_unmatched = load_excel_sheet(DEFAULT_EXCEL, ADVY_UNMATCH_SHEET)
    schwab_matched = load_excel_sheet(SCHWAB_EXCEL, SCHWAB_MATCH_SHEET)
    schwab_unmatched = load_excel_sheet(SCHWAB_EXCEL, SCHWAB_UNMATCH_SHEET)
    return adv_matched, adv_unmatched, schwab_matched, schwab_unmatched


def _safe_get_adv_record_id_column(df: pd.DataFrame) -> Optional[str]:
    for candidate in ('Record_ID', 'RecordID', 'Record Id', 'ID', 'id'):
        if candidate in df.columns:
            return candidate
    return None


def run(output_path: Path = Path('data') / 'schwab_matched.xlsx') -> None:
    adv_matched, adv_unmatched, schwab_matched, schwab_unmatched = load_default_tables()
    merged_crd = match_contacts_by_crd_and_email(adv_matched, schwab_matched)
    matched_unmatched = match_unmatched_by_email_then_fuzzy(adv_unmatched, schwab_unmatched)
    
    # Build final unmatched sheet preserving original Schwab row count and order
    final_unmatched = schwab_unmatched.copy()
    final_unmatched['Matched_or_not'] = 'unmatched'
    final_unmatched['Match_Score'] = 0
    final_unmatched['adv_Email_'] = None
    final_unmatched['adv_Record_ID'] = None
    
    # Re-attach match results by index
    if 'schwab__index' in matched_unmatched.columns:
        matched_unmatched_indexed = matched_unmatched.set_index('schwab__index')
        for idx in final_unmatched.index:
            if idx in matched_unmatched_indexed.index:
                match_row = matched_unmatched_indexed.loc[idx]
                final_unmatched.at[idx, 'Matched_or_not'] = match_row.get('Matched_or_not', 'unmatched')
                final_unmatched.at[idx, 'Match_Score'] = match_row.get('Match_Score', 0)
                final_unmatched.at[idx, 'adv_Email_'] = match_row.get('adv_Email_', None)
                # Get Record_ID (handle scientific notation by storing as string)
                adv_id_col = _safe_get_adv_record_id_column(adv_unmatched)
                if adv_id_col:
                    rec_id = match_row.get(f'adv_{adv_id_col}', None)
                    if pd.notna(rec_id):
                        final_unmatched.at[idx, 'adv_Record_ID'] = str(int(rec_id)) if isinstance(rec_id, (int, float)) else str(rec_id)
    
    # Ensure Email_Domain column exists and is populated from Schwab sheet
    if 'Email_Domain' not in final_unmatched.columns:
        final_unmatched['Email_Domain'] = schwab_unmatched.get('Email_Domain', None)
    else:
        # Fill missing Email_Domain values from original Schwab sheet
        final_unmatched['Email_Domain'] = final_unmatched['Email_Domain'].fillna(schwab_unmatched.get('Email_Domain', None))
    
    # Convert Record_ID to string to prevent Excel scientific notation
    final_unmatched['adv_Record_ID'] = final_unmatched['adv_Record_ID'].astype('object')
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        merged_crd.to_excel(writer, sheet_name='matched', index=False)
        final_unmatched.to_excel(writer, sheet_name='unmatched', index=False)
    
    logger.info(f"Matched sheet: {len(merged_crd)} rows")
    logger.info(f"Unmatched sheet: {len(final_unmatched)} rows (original Schwab unmatched: {len(schwab_unmatched)})")
    print(f'Wrote combined workbook to: {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Run matching pipeline and write combined Excel workbook')
    parser.add_argument('--out', '-o', help='Output workbook path', default=str(Path('data') / 'schwab_matched.xlsx'))
    parser.add_argument('--schema', action='store_true', help='Only extract Sheet1 schema from DEFAULT_EXCEL')
    args = parser.parse_args()
    if args.schema:
        extract_sheet1_schema(DEFAULT_EXCEL, Path('data'))
    else:
        run(Path(args.out))


if __name__ == '__main__':
    main()
