"""
Combine all per-annotation CSVs into one big CSV.
Usage:
  python src/combine_csv.py --csv-dir csv_exports --out-file final_annotations/combined_annotations.csv
"""

import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True, help="Folder containing per-annotation CSVs")
    parser.add_argument("--out-file", required=True, help="Path of the combined CSV file to write")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir).expanduser().resolve()
    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No CSV files found in {csv_dir}")

    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"[WARN] Skipping {f.name}: {e}")

    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv(args.out_file, index=False, encoding="utf-8")
    print(f"[OK] Combined {len(dfs)} files → {args.out_file}")

if __name__ == "__main__":
    main()