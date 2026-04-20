"""
Generate plain-language insights for Nodal product recommendations.
"""
import pandas as pd
from src.pipeline import segment as seg


def generate(df: pd.DataFrame) -> list[dict]:
    insights = []

    types = seg.by_type(df)
    top_type = types.iloc[0]["type"]
    top_type_count = int(types.iloc[0]["count"])
    insights.append({
        "category": "Ecosystem Composition",
        "finding": f"{top_type}s are the most common actor type ({top_type_count} entries).",
        "implication": f"Design Nodal's onboarding to speak fluently to {top_type}s first — "
                       "they are the densest, most-mobilised node in the ecosystem.",
    })

    countries = seg.by_country(df)
    top3_countries = countries.head(3)["country"].tolist()
    insights.append({
        "category": "Geographic Density",
        "finding": f"Top three countries: {', '.join(top3_countries)}. "
                   f"{df['country'].nunique()} countries represented.",
        "implication": "Pilot the first platform features where ecosystem density is highest, "
                       "then replicate outward. Avoid diluting effort across all countries early.",
    })

    focus = seg.by_focus(df)
    top3_focus = focus.head(3).index.tolist()
    insights.append({
        "category": "Thematic Landscape",
        "finding": f"Most-addressed focus areas: {', '.join(top3_focus)}.",
        "implication": "These are where peer-learning demand is highest. "
                       "Seed the first working groups and content library around these themes.",
    })

    if "generation" in df.columns:
        gens = seg.by_generation(df)
        new_gen = int(gens.get("2020s (new generation)", 0))
        insights.append({
            "category": "Generational Mix",
            "finding": f"{new_gen} organisations were founded in the 2020s, "
                       f"alongside long-standing institutional actors.",
            "implication": "Nodal sits between two generations — young initiatives need visibility and "
                           "mentorship; legacy institutions need fresh talent and energy. "
                           "Design exchanges that trade these assets.",
        })

    cities = seg.by_city(df)
    city_count = df["city"].nunique()
    top_city = cities.iloc[0]["city"]
    insights.append({
        "category": "Urban Footprint",
        "finding": f"Presence in {city_count} cities. {top_city} is the single densest node.",
        "implication": "Host the founding convening in the densest node and stream it regionally — "
                       "this concentrates energy without excluding distributed members.",
    })

    return insights


def top_cities_per_type(df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    return (
        df.groupby(["type", "city"])
        .size()
        .reset_index(name="count")
        .sort_values(["type", "count"], ascending=[True, False])
        .groupby("type")
        .head(top_n)
        .reset_index(drop=True)
    )
