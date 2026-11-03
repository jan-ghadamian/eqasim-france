import pandas as pd
import os

"""
Custom projection stage — reads a user-defined CSV instead of the official
INSEE projection file. This gives full control over target population counts
per département, sex, and age band.
"""

def configure(context):
    context.config("data_path")
    context.config("custom_projection_path", "projections/custom_projection.csv")

def execute(context):
    path = os.path.join(
        context.config("data_path"),
        context.config("custom_projection_path")
    )

    df = pd.read_csv(path, dtype={"department_id": str})

    # Validate required columns
    required = {"department_id", "sex", "minimum_age", "maximum_age", "weight"}
    assert required.issubset(df.columns), "Missing columns: {}".format(required - set(df.columns))

    # Ensure types match what ipu.py expects
    df["minimum_age"] = df["minimum_age"].astype(float)
    df["maximum_age"] = df["maximum_age"].astype(float)
    df["weight"]      = df["weight"].astype(float)
    df["sex"]         = df["sex"].astype(str)

        # ── confirmation prints ──────────────────────────────────────────
    print("\n[custom_projection] successful. Using custom projection file:")
    print("  Path:         {}".format(path))
    print("  Rows loaded:  {}".format(len(df)))
    print("  Départements: {}".format(sorted(df["department_id"].unique().tolist())))
    print("  Total target population: {:,.0f}".format(df["weight"].sum()))
    print("  Age bands:    {}".format(
        sorted(df[["minimum_age","maximum_age"]].drop_duplicates().values.tolist())
    ))
    # ────────────────────────────────────────────────────────────────

    return df[["department_id", "sex", "minimum_age", "maximum_age", "weight"]]

def validate(context):
    path = os.path.join(
        context.config("data_path"),
        context.config("custom_projection_path")
    )
    if not os.path.exists(path):
        raise RuntimeError("Custom projection file not found at: {}".format(path))
    return os.path.getsize(path)