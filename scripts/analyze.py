#!/usr/bin/env python3
"""
Quick terminal report of Nodal member data.
Usage:
    python scripts/analyze.py                       # uses sample data
    python scripts/analyze.py data/my_export.csv    # your own CSV
"""
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.ingest import load_csv, explode_multivalued
from src.pipeline.clean import clean
from src.pipeline import segment as seg
from src.analysis.insights import generate


def bar(label: str, count: int, total: int, width: int = 30) -> str:
    filled = round(count / total * width)
    return f"  {label:<30} {'█' * filled:<{width}} {count:>3} ({count/total*100:.0f}%)"


def section(title: str) -> None:
    print(f"\n{'─' * 52}")
    print(f"  {title.upper()}")
    print(f"{'─' * 52}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_members.csv"
    df = load_csv(path)
    df = clean(df)
    df = explode_multivalued(df)
    total = len(df)

    print(f"\n{'═' * 52}")
    print(f"  NODAL · MEMBER INTELLIGENCE REPORT")
    print(f"  Source: {path}  |  {total} members")
    print(f"{'═' * 52}")

    section("Overview")
    print(f"  {'Countries':<20} {df['country'].nunique()}")
    print(f"  {'Cities':<20} {df['city'].nunique()}")
    print(f"  {'Avg experience':<20} {df['experience_years'].mean():.1f} yrs")

    section("Roles")
    for _, row in seg.by_role(df).iterrows():
        print(bar(row["role"], row["count"], total))

    section("Top Countries")
    for _, row in seg.by_country(df).head(8).iterrows():
        print(bar(f"{row['country']} ({row['region']})", row["count"], total))

    section("Top Interests")
    interests = seg.by_interest(df)
    for label, count in interests.items():
        print(bar(label, count, total))

    section("Urban Challenges Named")
    for label, count in seg.by_challenge(df).head(10).items():
        print(bar(label, count, total))

    section("Engagement Preferences")
    for label, count in seg.by_engagement(df).items():
        print(bar(label, count, total))

    section("Key Insights & Recommendations")
    for i, ins in enumerate(generate(df), 1):
        print(f"\n  {i}. [{ins['category']}]")
        print(f"     Finding:    {ins['finding']}")
        print(f"     Action:     {ins['implication']}")

    print(f"\n{'═' * 52}\n")


if __name__ == "__main__":
    main()
