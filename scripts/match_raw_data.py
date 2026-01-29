import pandas as pd
import os
from pathlib import Path
try:
    from rapidfuzz import fuzz, process
except ImportError:
    from fuzzywuzzy import fuzz, process

# ============================================================================
# CONFIGURATION: Update these paths to point to your data files
# ============================================================================
# You can either edit these paths directly, or use environment variables:
#   set SCHWAB_FILE=C:\path\to\file.xlsx
#   set CONTACTS_FILE=C:\path\to\file.xlsx
#   set OUTPUT_FILE=C:\path\to\output.xlsx

SCHWAB_FILE = os.getenv(
    "SCHWAB_FILE",
    r"C:\Users\Jane\Desktop\Schwab\Schwab unmatched double check.xlsx"
)
CONTACTS_FILE = os.getenv(
    "CONTACTS_FILE",
    r"C:\Users\Jane\Desktop\Schwab\All Contact.xlsx"
)
OUTPUT_FILE = os.getenv(
    "OUTPUT_FILE",
    r"C:\Users\Jane\Desktop\Schwab\unmatched_match.xlsx"
)
# ============================================================================

def pick_col(df, candidates, default_value=""):
    """
    Return the first existing column from `candidates` as a cleaned Series.
    If none exist, return a Series of default_value with same index.
    """
    for c in candidates:
        if c in df.columns:
            return df[c].fillna(default_value).astype(str).str.strip()
    # no candidate found -> return empty series aligned with df
    return pd.Series([default_value] * len(df), index=df.index, dtype="object")


def match_by_name_and_company(Schwab_df, contacts_df, threshold: int = 90, verbose: bool = True):
    """Fuzzy match Schwab rows to contacts by First + Last + cleaned company."""
    if verbose:
        print(f"\n[INFO] Starting fuzzy match with {len(Schwab_df)} Schwab rows vs {len(contacts_df)} contacts (threshold={threshold}%)")
    sw = Schwab_df.copy()
    adv = contacts_df.copy()

    suffix_pattern = r"\b(inc|llc|ltd|co|corporation|corp|pllc|pc|gmbh|ag|bv|sa|sarl|sas|pte|pty|limited|investment|group)\b"

    # --- Company cleaning ---
    sw_company = pick_col(sw, ["Business_Name", "Business Name", "Company", "Company Name"])
    adv_company = pick_col(adv, ["Company Name", "Company", "Business_Name", "Business Name"])

    sw["clean_company"] = (
        sw_company.str.replace(suffix_pattern, "", case=False, regex=True)
                  .str.replace(",", "", regex=False)
                  .str.strip()
                  .str.lower()
    )

    adv["clean_company"] = (
        adv_company.str.replace(suffix_pattern, "", case=False, regex=True)
                   .str.replace(",", "", regex=False)
                   .str.strip()
                   .str.lower()
    )

    # --- Name parts ---
    sw_first = pick_col(sw, ["First_Name_", "First Name", "First name", "First"])
    sw_last  = pick_col(sw, ["Last_Name_", "Last Name", "Last name", "Last"])

    adv_first = pick_col(adv, ["First Name", "First name", "First", "First_Name_"])
    adv_last  = pick_col(adv, ["Last Name", "Last name", "Last", "Last_Name_", "Last Name "])

    # --- Build keys ---
    sw["Key"] = (sw_first + " " + sw_last + " | " + sw["clean_company"]).str.strip().str.lower()
    adv["Key"] = (adv_first + " " + adv_last + " | " + adv["clean_company"]).str.strip().str.lower()

    adv_keys = adv["Key"].fillna("").astype(str).tolist()
    if verbose:
        print(f"[INFO] Built keys. Ready to match {len(sw)} Schwab rows against {len(adv_keys)} contact keys.")

    out_rows = []
    if verbose:
        print(f"[INFO] Starting fuzzy matching loop...")
    for i, (_, sw_row) in enumerate(sw.iterrows()):
        if verbose and (i + 1) % max(1, len(sw) // 10) == 0:
            print(f"[PROGRESS] Processed {i + 1}/{len(sw)} rows ({100 * (i + 1) // len(sw)}%)")
        sk = sw_row.get("Key", "")
        if not sk:
            rec = sw_row.to_dict()
            rec["Matched"] = False
            rec["Match_Score"] = 0
            out_rows.append(rec)
            continue

        # Lightweight blocking: filter by first letter and length to reduce candidates
        candidates = adv_keys
        if len(candidates) > 500:
            sk_first = sk[0] if sk else ""
            sk_len = len(sk)
            candidates = [k for k in candidates if k and k[0] == sk_first and abs(len(k) - sk_len) <= max(1, int(sk_len * 0.3))]
            if not candidates:
                candidates = adv_keys

        match = process.extractOne(sk, candidates, scorer=fuzz.token_set_ratio)

        if match is None:
            rec = sw_row.to_dict()
            rec["Matched"] = False
            rec["Match_Score"] = 0
            out_rows.append(rec)
            continue

        matched_key, score = match[0], match[1]

        if score >= threshold:
            adv_row = adv[adv["Key"] == matched_key].iloc[0]
            merged = sw_row.to_dict()
            for c, v in adv_row.to_dict().items():
                merged[f"Adv_{c}"] = v
            merged["Matched"] = True
            merged["Match_Score"] = int(score)
            out_rows.append(merged)
        else:
            rec = sw_row.to_dict()
            rec["Matched"] = False
            rec["Match_Score"] = int(score)
            out_rows.append(rec)

    result_df = pd.DataFrame(out_rows)
    if verbose:
        matched_count = (result_df["Matched"] == True).sum()
        print(f"[INFO] Fuzzy matching complete: {matched_count}/{len(result_df)} rows matched (~{100 * matched_count // len(result_df)}%)\n")
    return result_df

# Load Schwab data
print("[INFO] Loading Schwab data...")
print(f"[INFO] File path: {SCHWAB_FILE}")
try:
    Schwab_discovery = pd.read_excel(SCHWAB_FILE, sheet_name="in discovery")
    print(f"[INFO] Loaded {len(Schwab_discovery)} rows from 'in discovery'")
    Schwab_not_in_discovery = pd.read_excel(SCHWAB_FILE, sheet_name="not in discovery")
    print(f"[INFO] Loaded {len(Schwab_not_in_discovery)} rows from 'not in discovery'")
except FileNotFoundError:
    print(f"[ERROR] Schwab file not found: {SCHWAB_FILE}")
    print("[INFO] Please update SCHWAB_FILE path in the script or set the SCHWAB_FILE environment variable.")
    exit(1)

print("[INFO] Loading contacts data...")
print(f"[INFO] File path: {CONTACTS_FILE}")
try:
    all_contacts = pd.read_excel(CONTACTS_FILE)
    print(f"[INFO] Loaded {len(all_contacts)} contact rows")
except FileNotFoundError:
    print(f"[ERROR] Contacts file not found: {CONTACTS_FILE}")
    print("[INFO] Please update CONTACTS_FILE path in the script or set the CONTACTS_FILE environment variable.")
    exit(1)

print(f"\n[INFO] Output will be saved to: {OUTPUT_FILE}\n")

print("="*60)
matched_in_discovery = match_by_name_and_company(Schwab_discovery, all_contacts)
print("="*60)

print("="*60)
matched_not_in_discovery = match_by_name_and_company(Schwab_not_in_discovery, all_contacts)
print("="*60)

with pd.ExcelWriter(OUTPUT_FILE) as writer:
    print("[INFO] Writing results to Excel...")
    matched_in_discovery.to_excel(writer, sheet_name="in discovery", index=False)
    matched_not_in_discovery.to_excel(writer, sheet_name="not in discovery", index=False)
print(f"[INFO] Done! Output saved to: {OUTPUT_FILE}")

