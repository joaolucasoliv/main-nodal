"""
Find peer organisations for a given entry.

Scoring favours *actionable* matches: strong topic overlap, geographic
proximity, and cross-class complementarity (a founder benefits from meeting
institutions and politicians, not only other founders).
"""
import pandas as pd


def peers_of(df: pd.DataFrame, name: str, top_n: int = 6) -> pd.DataFrame:
    """Rank peers for `name` by focus overlap, geography and class complementarity.

    Returns a DataFrame with extra columns:
      - score:   numeric ranking score
      - why:     list of short reason strings for the match
      - shared:  list of overlapping focus areas (may be empty)
    """
    if name not in set(df["name"]):
        return df.iloc[0:0]

    row = df[df["name"] == name].iloc[0]
    target_focus = set(row["focus_areas"] or [])
    target_country = row["country"]
    target_city = row["city"]
    target_type = row["type"]
    target_class = row.get("actor_class", "institution")

    others = df[df["name"] != name].copy()

    def score_row(r):
        shared = sorted(set(r["focus_areas"] or []) & target_focus)
        reasons: list[str] = []
        s = 0.0

        if shared:
            s += len(shared) * 2.0
            reasons.append("focus:" + " · ".join(shared[:3]))

        if r["city"] == target_city:
            s += 2.0
            reasons.append(f"city:{r['city']}")
        elif r["country"] == target_country:
            s += 1.0
            reasons.append(f"country:{r['country']}")

        # Cross-class complementarity: leaders grow through diverse connections.
        r_class = r.get("actor_class", "institution")
        if r_class != target_class:
            s += 0.8
            reasons.append(f"class:{r_class}")
        else:
            s -= 0.2

        if r["type"] == target_type:
            s += 0.25

        return pd.Series({"score": s, "why": reasons, "shared": shared})

    scored = others.apply(score_row, axis=1)
    out = pd.concat([others.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)
    return out.sort_values("score", ascending=False).head(top_n)


def same_city(df: pd.DataFrame, city: str, exclude: str = "") -> pd.DataFrame:
    return df[(df["city"] == city) & (df["name"] != exclude)]


def same_focus(df: pd.DataFrame, focus: str, exclude: str = "") -> pd.DataFrame:
    return df[
        df["focus_areas"].apply(lambda lst: focus in (lst or []))
        & (df["name"] != exclude)
    ]
