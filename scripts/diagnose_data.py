"""Diagnostic script to analyze data file format issues.

Run this script to understand what values are in your Excel file.
"""

import pandas as pd
import sys

# File path and sheet name
FILE_PATH = r"c:\Users\Gerry Chan\OneDrive\Documents\Para40Min15Prev40.xlsx"
SHEET_NAME = "1st_Trigger"


def main():
    print(f"Loading: {FILE_PATH}")
    print(f"Sheet: {SHEET_NAME}")
    print("=" * 60)

    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)

    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")

    # Check for gain_pct and similar columns
    gain_cols = [col for col in df.columns if "gain" in col.lower()]
    mae_cols = [col for col in df.columns if "mae" in col.lower()]

    print(f"\nGain-related columns: {gain_cols}")
    print(f"MAE-related columns: {mae_cols}")

    print("\n" + "=" * 60)
    print("ANALYSIS OF GAIN COLUMNS")
    print("=" * 60)

    for col in gain_cols:
        print(f"\n--- {col} ---")
        values = df[col].astype(float)
        print(f"  Count: {len(values)}")
        print(f"  Min: {values.min():.6f}")
        print(f"  Max: {values.max():.6f}")
        print(f"  Mean: {values.mean():.6f}")
        print(f"  Median: {values.median():.6f}")
        print(f"  Std: {values.std():.6f}")

        # Sample values
        print(f"  First 10 values: {values.head(10).tolist()}")

        # Check format
        abs_mean = abs(values.mean())
        if abs_mean < 0.01:
            print(f"  FORMAT HINT: Very small values - might be 100x smaller than expected")
        elif 0.01 <= abs_mean < 1:
            print(f"  FORMAT HINT: Looks like decimal format (0.10 = 10%)")
        elif 1 <= abs_mean < 100:
            print(f"  FORMAT HINT: Looks like percentage format (10 = 10%)")
        else:
            print(f"  FORMAT HINT: Very large values - unusual format")

    print("\n" + "=" * 60)
    print("ANALYSIS OF MAE COLUMNS")
    print("=" * 60)

    for col in mae_cols:
        print(f"\n--- {col} ---")
        values = df[col].astype(float)
        print(f"  Count: {len(values)}")
        print(f"  Min: {values.min():.6f}")
        print(f"  Max: {values.max():.6f}")
        print(f"  Mean: {values.mean():.6f}")
        print(f"  Median: {values.median():.6f}")
        print(f"  First 10 values: {values.head(10).tolist()}")

        # Check format
        abs_mean = abs(values.mean())
        if abs_mean < 0.01:
            print(f"  FORMAT HINT: Very small values - might be 100x smaller than expected")
        elif 0.01 <= abs_mean < 1:
            print(f"  FORMAT HINT: Looks like decimal format (0.10 = 10%)")
        elif 1 <= abs_mean < 100:
            print(f"  FORMAT HINT: Looks like percentage format (10 = 10%)")
        else:
            print(f"  FORMAT HINT: Very large values - unusual format")

    # Win/Loss analysis
    print("\n" + "=" * 60)
    print("WIN/LOSS ANALYSIS (using 'gain_pct' if exists)")
    print("=" * 60)

    if "gain_pct" in df.columns:
        gains = df["gain_pct"].astype(float)
        winners = gains[gains > 0]
        losers = gains[gains < 0]

        print(f"\nTotal trades: {len(gains)}")
        print(f"Winners: {len(winners)} ({100*len(winners)/len(gains):.1f}%)")
        print(f"Losers: {len(losers)} ({100*len(losers)/len(gains):.1f}%)")

        if len(winners) > 0:
            print(f"\nWinners - mean: {winners.mean():.6f}, min: {winners.min():.6f}, max: {winners.max():.6f}")
        if len(losers) > 0:
            print(f"Losers - mean: {losers.mean():.6f}, min: {losers.min():.6f}, max: {losers.max():.6f}")

        # Expected display values
        print("\n" + "=" * 60)
        print("EXPECTED DISPLAY VALUES")
        print("=" * 60)
        print(f"\nIf data is in DECIMAL format (0.20 = 20%):")
        print(f"  Avg Winner (displayed): {winners.mean() * 100:.2f}%")
        print(f"  Avg Loser (displayed): {losers.mean() * 100:.2f}%")

        print(f"\nIf data is ALREADY in PERCENTAGE format (20 = 20%):")
        print(f"  Avg Winner (displayed): {winners.mean():.2f}%")
        print(f"  Avg Loser (displayed): {losers.mean():.2f}%")


if __name__ == "__main__":
    main()
