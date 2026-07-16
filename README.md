# f1-degradation-analysis

# F1 Fuel-Corrected Tire Degradation Analysis

Analyzes tire degradation using real F1 telemetry (via the FastF1 API) by
separating it from the fuel-burn effect that normally masks it in raw lap
time data.

## What this does
1. Pulls lap timing data for a race session
2. Filters for clean, racing-condition laps
3. Removes the effect of decreasing fuel load (which speeds the car up
   independent of tire wear)
4. Flags laps affected by overtakes/traffic
5. Fits a per-driver degradation rate (seconds/lap) for one stint

## Method

**Data source**: [FastF1](https://github.com/theOehrly/Fast-F1), 2024 Bahrain GP race session.

**Filtering**: Laps excluded if flagged `IsAccurate == False`, if `LapTime`
is null, or if `TrackStatus` is not exactly `'1'` (green flag). This
excludes pit in/out laps, yellow-flag laps, VSC, and safety car periods.

This filter was validated against the 2024 Australian GP — a race with a
different flag profile (VSC period, no full safety car) — to confirm the
logic generalizes rather than being tuned to one race's specific conditions.

**Fuel correction**: Fuel burn is assumed linear (110kg at race start,
0kg at the end). The cost of fuel weight on lap time has no single
agreed-upon public constant — published estimates range roughly
0.025–0.04 seconds per kg, and the most commonly cited figure traces back
to an unverified TV broadcast comment rather than a published source.
Rather than pick one number, this analysis applies both bounds and shows
the resulting uncertainty as a shaded band on the chart.

**Traffic flag**: Laps where a driver's `Position` differs from their
previous lap are flagged (an overtake or being overtaken happened) and
excluded from the trend fit, since these laps reflect racing incidents,
not tire performance. This is a proxy, not a complete traffic filter — it
does not catch a car stuck behind a rival without an actual position
change (following in dirty air).

**Fit**: Linear regression per driver, on one stint, excluding flagged laps.

## Limitations
- Single stint, single race (Bahrain), 4 drivers — a starter analysis
- Linear fit assumption — real tire degradation can be non-linear (a "cliff")
  late in a stint, which a straight-line fit would understate
- Track evolution (grip increasing over a race as more rubber goes down)
  is not separated from tire degradation — this analysis cannot fully
  distinguish the two effects
- Fuel correction constant is a range, not a verified precise value
- Traffic filter only catches active position changes, not all dirty-air laps

## Results
Degradation rates for Bahrain 2024, stint 1: ~0.08–0.09 s/lap across the
four drivers analyzed (VER, PER, LEC, SAI).



