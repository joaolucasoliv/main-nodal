"""
Load changemaker data from local CSV or a Google Sheets export URL.
"""
import pandas as pd
from pathlib import Path


MULTI_VALUE_COLS = ["focus_areas"]


def load_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_google_sheet(sheet_id: str, gid: str = "0") -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)


def explode_multivalued(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in MULTI_VALUE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("").str.split(";").apply(
                lambda items: [x.strip() for x in items if x.strip()]
            )
    return df
