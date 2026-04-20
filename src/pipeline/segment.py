"""
Segment the changemaker dataset into meaningful cohorts.
"""
import pandas as pd


def by_type(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("type").size().reset_index(name="count").sort_values("count", ascending=False)


def by_country(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["country", "region"]).size().reset_index(name="count").sort_values("count", ascending=False)


def by_city(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["city", "country"]).size().reset_index(name="count").sort_values("count", ascending=False)


def by_focus(df: pd.DataFrame) -> pd.Series:
    return df["focus_areas"].explode().value_counts().rename("count")


def by_generation(df: pd.DataFrame) -> pd.Series:
    return df["generation"].value_counts().rename("count")


def cross_type_focus(df: pd.DataFrame) -> pd.DataFrame:
    exploded = df[["type", "focus_areas"]].explode("focus_areas")
    return (
        exploded.groupby(["type", "focus_areas"])
        .size()
        .reset_index(name="count")
        .pivot(index="type", columns="focus_areas", values="count")
        .fillna(0)
    )


def cross_country_focus(df: pd.DataFrame) -> pd.DataFrame:
    exploded = df[["country", "focus_areas"]].explode("focus_areas")
    return (
        exploded.groupby(["country", "focus_areas"])
        .size()
        .reset_index(name="count")
        .pivot(index="country", columns="focus_areas", values="count")
        .fillna(0)
    )
