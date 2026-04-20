"""
Generate plain-language insights for Nodal product recommendations (i18n-aware).
"""
import pandas as pd
from src.pipeline import segment as seg
from src.dashboard.i18n import t


def generate(df: pd.DataFrame, lang: str = "es") -> list[dict]:
    insights = []

    types = seg.by_type(df)
    top_type = types.iloc[0]["type"]
    top_type_count = int(types.iloc[0]["count"])
    insights.append({
        "category": t("ins_comp", lang),
        "finding":  t("ins_comp_f", lang, type=top_type, n=top_type_count),
        "implication": t("ins_comp_a", lang, type=top_type),
    })

    countries = seg.by_country(df)
    top3 = countries.head(3)["country"].tolist()
    insights.append({
        "category": t("ins_geo", lang),
        "finding":  t("ins_geo_f", lang, list=", ".join(top3), n=df["country"].nunique()),
        "implication": t("ins_geo_a", lang),
    })

    focus = seg.by_focus(df)
    top3_focus = focus.head(3).index.tolist()
    insights.append({
        "category": t("ins_theme", lang),
        "finding":  t("ins_theme_f", lang, list=", ".join(top3_focus)),
        "implication": t("ins_theme_a", lang),
    })

    if "generation" in df.columns:
        gens = seg.by_generation(df)
        new_gen = int(gens.get("2020s (new generation)", 0))
        insights.append({
            "category": t("ins_gen", lang),
            "finding":  t("ins_gen_f", lang, n=new_gen),
            "implication": t("ins_gen_a", lang),
        })

    cities = seg.by_city(df)
    top_city = cities.iloc[0]["city"]
    insights.append({
        "category": t("ins_foot", lang),
        "finding":  t("ins_foot_f", lang, n=df["city"].nunique(), city=top_city),
        "implication": t("ins_foot_a", lang),
    })

    return insights
