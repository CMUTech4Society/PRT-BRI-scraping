#!/usr/bin/env python3
"""
Convert a folder of route JSON exports into a single CSV with
rows as routes and columns as months repeated per year.

Assumptions based on the provided sample file:
- Years are listed in dsr.DS[0].SH[0].DM1 -> items with key "G1", e.g. "2019", "2023", ...
- Months are listed in dsr.DS[0].PH[0].DM0, with G0 indices mapping to ValueDicts[D0]
- For each month entry, X[k]["M0"] contains the metric for year k (same order as years above)
  ("M0" is "Sum(OTP_Monthly_Route_Avg.OTP_Pct)" in your sample).
These correspond to the structure observed in the uploaded file.  # See conversation notes.
"""

import os
import re
import glob
import json
import csv
import argparse
import math
from typing import Dict, List, Any, Tuple, Optional


TIMESTAMP_TAIL_RE = re.compile(
    r"""                # e.g., _2026_02_02-19_48
    _\d{4}_\d{2}_\d{2}-\d{2}_\d{2}$
    """,
    re.VERBOSE,
)


def guess_route_name_from_filename(path: str) -> str:
    """
    Extract a readable route name from a file path.
    Strategy:
    - Drop directory and extension.
    - If name ends with "_YYYY_MM_DD-HH_mm", strip that tail.
    - Return the remaining string as the route name.
    """
    base = os.path.splitext(os.path.basename(path))[0]
    route = TIMESTAMP_TAIL_RE.sub("", base)
    return route


def get_nested(d: Dict[str, Any], keys: List[Any], default=None):
    """Safely get nested keys: keys may include ints for list indexing."""
    cur = d
    for k in keys:
        if isinstance(k, int):
            if not isinstance(cur, list) or k >= len(cur):
                return default
            cur = cur[k]
        else:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
    return cur


def extract_years(ds: Dict[str, Any]) -> List[str]:
    """
    Extract the ordered list of years from the DS block.
    Expected at dsr.DS[0].SH[0].DM1[*].G1
    """
    dm1 = get_nested(ds, ["results", 0, "result", "data", "dsr", "DS", 0, "SH", 0, "DM1"], default=[])
    years: List[str] = []
    for item in dm1 or []:
        g1 = item.get("G1")
        if g1 is not None:
            years.append(str(g1))
    return years


def extract_month_names(ds: Dict[str, Any]) -> List[str]:
    """
    Extract the month name dictionary; typically ValueDicts.D0 holds
    ["Jan", "Feb", ..., "Dec"], referenced by DN:"D0" in PH.DM0. If absent,
    fall back to a 12-month sequence ["Jan",...,"Dec"].
    """
    months = get_nested(ds, ["results", 0, "result", "data", "dsr", "DS", 0, "ValueDicts", "D0"])
    if isinstance(months, list) and len(months) == 12:
        return months
    # fallback
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def extract_month_entries(ds: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract the monthly PH entries; expected at dsr.DS[0].PH[0].DM0 with
    each item containing 'G0' (0..11) and 'X' (list per-year values).
    """
    dm0 = get_nested(ds, ["results", 0, "result", "data", "dsr", "DS", 0, "PH", 0, "DM0"], default=[])
    # Ensure sorted by G0 index if present
    def sort_key(item):
        return item.get("G0", 0)
    return sorted(dm0, key=sort_key)


def coerce_numeric(val: Any) -> Optional[float]:
    """
    Coerce numeric values that may be encoded as strings (e.g., "0.123", "1e-4").
    Returns None if the value cannot be parsed as a finite float.
    """
    if isinstance(val, (int, float)):
        num = float(val)
        return num if math.isfinite(num) else None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        s = s.replace(",", "")
        try:
            num = float(s)
            return num if math.isfinite(num) else None
        except ValueError:
            return None
    return None


def pick_metric_key(x_item: Dict[str, Any]) -> Optional[str]:
    """
    Find the metric key inside an X entry. Prefer 'M0' but fall back to
    the first key that starts with 'M'.
    """
    if "M0" in x_item:
        return "M0"
    for k in x_item.keys():
        if isinstance(k, str) and k.startswith("M"):
            return k
    return None


def extract_route_values(ds: Dict[str, Any]) -> Tuple[List[str], Dict[str, float]]:
    """
    Return (years, values_by_col) for a single JSON file.
    values_by_col maps "YYYY-Mon" -> float.

    If a value is missing, it will simply be skipped (caller can leave blank).
    """
    years = extract_years(ds)
    months = extract_month_names(ds)
    month_entries = extract_month_entries(ds)

    values: Dict[str, float] = {}

    for m_entry in month_entries:
        # Month index -> month name
        m_idx = m_entry.get("G0")
        if not isinstance(m_idx, int) or m_idx < 0 or m_idx >= len(months):
            continue
        month_name = months[m_idx]
        x_list = m_entry.get("X", [])
        # Each x_list item corresponds to a year; when "I" appears it indicates
        # a missing prior year, so shift the JSON index forward for this and
        # subsequent items to align with the years list.
        offset = 0
        for x_pos, x_item in enumerate(x_list):
            if not isinstance(x_item, dict):
                continue
            if isinstance(x_item.get("I"), int):
                offset = max(offset, x_item["I"] - x_pos)
            year_idx = x_pos + offset
            if year_idx < 0 or year_idx >= len(years):
                continue
            year = years[year_idx]
            metric_key = pick_metric_key(x_item)
            if metric_key and metric_key in x_item:
                val = x_item[metric_key]
                num = coerce_numeric(val)
                if num is not None:
                    values[f"{year}-{month_name}"] = num

    return years, values


def build_header(all_years: List[str], months: List[str]) -> List[str]:
    """
    Build CSV header: Route, then for each year ascending, 12 months.
    """
    # Sort years as integers if possible
    def try_int(y):
        try:
            return int(y)
        except Exception:
            return y
    years_sorted = sorted(set(all_years), key=try_int)
    header = ["Route"]
    for y in years_sorted:
        for m in months:
            header.append(f"{y}-{m}")
    return header


def main():
    parser = argparse.ArgumentParser(description="Convert route JSON files into a single CSV (rows=routes, cols=months per year).")
    parser.add_argument(
        "--input",
        default="*.json",
        help="Glob pattern for input files (default: *.json). Example: 'exports/*.json'"
    )
    parser.add_argument(
        "--output",
        default="routes_by_month.csv",
        help="Output CSV filename (default: routes_by_month.csv)"
    )
    parser.add_argument(
        "--as-percent",
        action="store_true",
        help="If set, multiply values by 100 and write as percentages (e.g., 69.12)."
    )
    args = parser.parse_args()

    file_paths = sorted(glob.glob(args.input))
    if not file_paths:
        print("No input files matched. Use --input to point to your JSON files.")
        return

    # First pass: collect union of all years across files
    all_years: List[str] = []
    canonical_months: List[str] = None  # type: ignore
    per_route_rows: List[Tuple[str, Dict[str, float]]] = []

    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                ds = json.load(f)
        except Exception as e:
            print(f"Skipping {path} (failed to read/parse): {e}")
            continue

        years, values_map = extract_route_values(ds)
        route_name = guess_route_name_from_filename(path)

        if years:
            all_years.extend(years)
        if canonical_months is None:
            canonical_months = extract_month_names(ds)

        per_route_rows.append((route_name, values_map))

    if canonical_months is None:
        # If we never parsed any months (shouldn't happen), fall back to 12 months
        canonical_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    header = build_header(all_years, canonical_months)

    # Write CSV
    with open(args.output, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(header)

        for route_name, values_map in per_route_rows:
            row = [route_name]
            for col in header[1:]:
                val = values_map.get(col, "")
                if val == "":
                    row.append("")
                else:
                    if args.as_percent:
                        row.append(f"{val * 100:.2f}")
                    else:
                        row.append(f"{val:.4f}")
            writer.writerow(row)

    print(f"Wrote {args.output} with {len(per_route_rows)} route(s).")


if __name__ == "__main__":
    main()
