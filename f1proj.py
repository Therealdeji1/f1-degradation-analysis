"""
F1 Fuel-Corrected Tire Degradation Analysis
=============================================
Pulls lap timing data via FastF1, filters for clean racing-condition laps,
removes fuel load effect (bounded sensitivity range), flags traffic-affected
laps, and fits per-driver degradation rate for a single stint.

Filter logic validated across two races with different flag conditions
(Bahrain: yellow flags only; Australia: VSC period) — see validate_filter()
at the bottom, run separately if you want to reproduce that check.

Assumptions / limitations — see README.md for full detail:
- Linear fuel burn assumed (110kg -> 0kg over race distance)
- Fuel correction applied as a range (0.025-0.04 s/kg), not a single value,
  since no authoritative public constant exists
- Traffic filter is a proxy (position change vs. previous lap only) — does
  not catch a car stuck behind a rival without an actual position change
- Linear trend fit — real degradation may be non-linear (a "cliff")
- Single stint / single race in this base analysis — a starter project
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import fastf1


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CACHE_DIR = "f1_cache"
FUEL_START_KG = 110
FUEL_COEF_LOW = 0.025   # s per kg, lower bound
FUEL_COEF_HIGH = 0.04   # s per kg, upper bound
DRIVERS_TO_PLOT = ["VER", "PER", "LEC", "SAI"]
STINT_TO_PLOT = 1


def load_session(year, gp, session_code="R"):
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)
    session = fastf1.get_session(year, gp, session_code)
    session.load()
    return session


def build_clean_laps(session):
    """
    Filters out:
      - laps flagged IsAccurate == False
      - laps with null LapTime
      - laps under any non-green TrackStatus (yellow, VSC, SC, etc.)
        (exact match on '1' — TrackStatus is a string, sometimes a
        concatenation like '12' for overlapping conditions)
    Also adds a PositionChanged flag for laps where the driver's Position
    differs from their previous lap — a proxy for overtakes/battles that
    distort pace independent of tire wear. These laps are kept (not
    dropped) so they can be shown but excluded from trend fits.
    """
    laps = session.laps.copy()

    clean = laps[
        (laps["IsAccurate"] == True)
        & (laps["LapTime"].notna())
        & (laps["TrackStatus"] == "1")
    ].copy()

    clean = clean.sort_values(["Driver", "LapNumber"])
    clean["PositionChanged"] = clean.groupby("Driver")["Position"].diff() != 0

    return clean


def validate_filter(clean_laps, session):
    """
    Sanity checks to run when validating the filter on a new race.
    Not required for the main plotting pipeline — call manually.
    """
    print("Total laps:", session.laps.shape[0], "-> Clean laps:", clean_laps.shape[0])
    print("\nTrackStatus value counts (raw):")
    print(session.laps["TrackStatus"].value_counts())
    print("\nIsAccurate counts among non-green laps:")
    print(session.laps[session.laps["TrackStatus"] != "1"]["IsAccurate"].value_counts())


def apply_fuel_correction(clean_laps, race_laps):
    df = clean_laps.copy()
    df["FuelRemaining"] = FUEL_START_KG * (1 - df["LapNumber"] / race_laps)
    df["LapTimeSeconds"] = df["LapTime"].dt.total_seconds()
    df["CorrectedLow"] = df["LapTimeSeconds"] - (df["FuelRemaining"] * FUEL_COEF_LOW)
    df["CorrectedHigh"] = df["LapTimeSeconds"] - (df["FuelRemaining"] * FUEL_COEF_HIGH)
    return df


def plot_degradation(corrected_laps, drivers, stint, save_path="degradation_fit.png"):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10.colors

    for i, driver in enumerate(drivers):
        color = colors[i % len(colors)]
        stint_data = corrected_laps[
            (corrected_laps["Driver"] == driver) & (corrected_laps["Stint"] == stint)
        ]
        if stint_data.empty:
            continue

        mid = (stint_data["CorrectedLow"] + stint_data["CorrectedHigh"]) / 2

        ax.plot(stint_data["LapNumber"], mid, color=color, alpha=0.4, label=f"{driver} (raw)")
        ax.fill_between(
            stint_data["LapNumber"],
            stint_data["CorrectedLow"],
            stint_data["CorrectedHigh"],
            alpha=0.08,
            color=color,
        )

        flagged = stint_data[stint_data["PositionChanged"]]
        ax.scatter(
            flagged["LapNumber"],
            (flagged["CorrectedLow"] + flagged["CorrectedHigh"]) / 2,
            color=color,
            marker="x",
            s=70,
            zorder=5,
        )

        fit_data = stint_data[~stint_data["PositionChanged"]]
        if len(fit_data) >= 2:
            coeffs = np.polyfit(
                fit_data["LapNumber"], (fit_data["CorrectedLow"] + fit_data["CorrectedHigh"]) / 2, 1
            )
            trend = np.poly1d(coeffs)
            x_range = np.linspace(fit_data["LapNumber"].min(), fit_data["LapNumber"].max(), 50)
            ax.plot(
                x_range,
                trend(x_range),
                color=color,
                linewidth=2.5,
                label=f"{driver} fit: {coeffs[0]:.3f} s/lap",
            )

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Fuel-Corrected Lap Time (s)")
    ax.set_title(
        f"Fuel-Corrected Degradation, Stint {stint}\n"
        "(x marks laps with a position change, excluded from fit)"
    )
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()


if __name__ == "__main__":
    session = load_session(2024, "Bahrain", "R")

    clean_laps = build_clean_laps(session)
    validate_filter(clean_laps, session)

    race_laps = session.laps["LapNumber"].max()
    corrected_laps = apply_fuel_correction(clean_laps, race_laps)

    plot_degradation(corrected_laps, DRIVERS_TO_PLOT, STINT_TO_PLOT)

    # Optional: validate filter against a second race with different flag
    # conditions (VSC instead of yellow-only) before trusting it elsewhere.
    # session2 = load_session(2024, "Australia", "R")
    # clean_laps2 = build_clean_laps(session2)
    # validate_filter(clean_laps2, session2)
