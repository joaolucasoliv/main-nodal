"""
Find peer organisations for a given entry, based on shared focus areas,
region, and generation — the scaffolding that makes Nodal a matchmaking tool.
"""
import pandas as pd


def peers_of(df: pd.DataFrame, name: str, top_n: int = 6) -> pd.DataFrame:
    """Return orgs most similar to `name` by shared focus areas, then same country, then same type."""
    if name not in set(df["name"]):
        return df.iloc[0:0]

    row = df[df["name"] == name].iloc[0]
    target_focus = set(row["focus_areas"] or [])
    target_country = row["country"]
    target_city = row["city"]
    target_type = row["type"]

    others = df[df["name"] != name].copy()

    def score(r) -> float:
        focus_overlap = len(set(r["focus_areas"] or []) & target_focus)
        same_city = 2 if r["city"] == target_city else 0
        same_country = 1 if r["country"] == target_country else 0
        same_type = 0.5 if r["type"] == target_type else 0
        return focus_overlap * 2 + same_city + same_country + same_type

    others["score"] = others.apply(score, axis=1)
    return others.sort_values("score", ascending=False).head(top_n)


def same_city(df: pd.DataFrame, city: str, exclude: str = "") -> pd.DataFrame:
    return df[(df["city"] == city) & (df["name"] != exclude)]


def same_focus(df: pd.DataFrame, focus: str, exclude: str = "") -> pd.DataFrame:
    return df[
        df["focus_areas"].apply(lambda lst: focus in (lst or []))
        & (df["name"] != exclude)
    ]
