"""
Standardise and enrich raw Latin American urban changemaker data.
"""
import pandas as pd

COUNTRY_REGIONS = {
    "Peru": "Andean",
    "Bolivia": "Andean",
    "Ecuador": "Andean",
    "Colombia": "Andean",
    "Venezuela": "Andean",
    "Brazil": "Brazil",
    "Argentina": "Southern Cone",
    "Chile": "Southern Cone",
    "Uruguay": "Southern Cone",
    "Paraguay": "Southern Cone",
    "Mexico": "Mexico & Central America",
    "Guatemala": "Mexico & Central America",
    "Honduras": "Mexico & Central America",
    "Costa Rica": "Mexico & Central America",
    "Panama": "Mexico & Central America",
    "United States": "North America (partner)",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["country"] = df["country"].str.strip()
    df["city"] = df["city"].str.strip().str.title()
    df["region"] = df["country"].map(COUNTRY_REGIONS).fillna("Other")

    df["type"] = df["type"].fillna("Organization").str.strip().str.title()

    df["founded_year"] = pd.to_numeric(df.get("founded_year"), errors="coerce")
    current_year = 2026
    df["age_years"] = (current_year - df["founded_year"]).fillna(0).astype(int)
    df["generation"] = pd.cut(
        df["founded_year"].fillna(current_year),
        bins=[0, 1999, 2009, 2019, 2100],
        labels=["Pre-2000 (foundational)", "2000s (institutional)",
                "2010s (civic tech wave)", "2020s (new generation)"],
    )

    return df.reset_index(drop=True)
