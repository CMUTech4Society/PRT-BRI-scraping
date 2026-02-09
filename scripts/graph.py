#!/usr/bin/env python3
import re
import pandas as pd
import plotly.express as px

# --- SETTINGS ---
CSV_PATH = "routes_by_month.csv"  # change to your CSV filename
VALUE_IS_PERCENT = False          # set True if values are 0–100 rather than 0–1

# --- LOAD ---
df_wide = pd.read_csv(CSV_PATH)

# Expect columns: "Route", "2019-Jan", "2019-Feb", ... "2025-Dec"
# Identify time columns (Year-MonAbbr)
time_cols = [c for c in df_wide.columns if c != "Route" and re.match(r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$", c)]

# --- RESHAPE TO LONG ---
df_long = df_wide.melt(id_vars="Route", value_vars=time_cols,
                       var_name="YearMonth", value_name="Value")

# Drop all-empty cells (if any)
df_long = df_long.dropna(subset=["Value"])

# If your CSV stores proportions (0.6912) but you want percent (69.12), set VALUE_IS_PERCENT accordingly
if not VALUE_IS_PERCENT:
    # If values are proportions and you want to show percent on hover, keep as proportion.
    # If you actually want to scale to percent for y-axis, uncomment the next line:
    # df_long["Value"] = df_long["Value"] * 100
    pass

# --- BUILD A REAL DATE ---
# Split "YYYY-Mon" into parts
df_long[["Year", "MonAbbr"]] = df_long["YearMonth"].str.split("-", expand=True)
month_map = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
df_long["Month"] = df_long["MonAbbr"].map(month_map)
df_long["Year"] = df_long["Year"].astype(int)

# Use first-of-month for a proper datetime axis
df_long["Date"] = pd.to_datetime(dict(year=df_long["Year"], month=df_long["Month"], day=1))

# Sort for clean lines
df_long = df_long.sort_values(["Route", "Date"])

# --- PLOT ---
# One chart with one line per route
fig = px.line(
    df_long,
    x="Date",
    y="Value",
    color="Route",
    markers=True,
    title="On-Time Performance by Route (Monthly)",
    labels={
        "Date": "Month",
        "Value": "Value",
        "Route": "Route"
    },
)

# Optional: format y-axis as percent (if your Value is already 0–1)
# fig.update_yaxes(tickformat=".0%")

# A few styling niceties
fig.update_layout(
    hovermode="x unified",
    legend_title_text="Route",
    xaxis=dict(dtick="M1", tickformat="%b\n%Y")  # month tick with year on new line
)

fig.show()
