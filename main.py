"""gta6-twitch-ccu-forecast-01 entry: an ensemble day-shape forecaster.

Model: a launch day's Twitch curve, hour by hour, resembles other big
launches' curves once each is measured relative to its own first hour.
For every past launch in the case's `comparables` we take its release-day
curve (the 24 UTC hours from its `day_start`), anchor it at its hour-1
count a_c, and form log-ratios r_c(h) = ln(v_c(h)) - ln(v_c(1)). Per hour
the r_c are combined with a trimmed weighted mean into a central curve
r_hat(h), and the spread s(h) is their weighted standard deviation.

Weights favour the launches most like this one: a Gaussian kernel on
|ln(a_c) - ln(p)| (p is the case's hour-1 print), times a boost for
launches that, like this case's game, unlocked at rolling local midnight
(their surge pattern through the UTC day is the same archetype; launches
with a single global unlock or long early access peak in hour 1 and stay
flat, which smears the ensemble's shape if they dominate).

The median forecast is q50(h) = p * exp(r_hat(h)), with positive r_hat
(growth hours) scaled by GROWTH_LIFT: the ensemble centre still
understates how hard a rolling-midnight launch surges once the US unlocks
and prime time arrive. The five quantiles are
q_tau(h) = q50(h) * exp(z_tau * s(h)) with s floored and capped.

A comparable whose name is the case game's own name (or begins with it)
is left out: in the final, the Grand Theft Auto VI category's own
comparable is its pre-release premiere curve, not a launch; the
"<game> category before release" curve is likewise never a launch day.
If no comparable survives, the forecast falls back to persistence with a
widening spread (the house baseline's shape).

Deterministic: pure arithmetic over the input, iteration in file order,
no randomness, no clock. Standard library only, no network.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves this file's directory off sys.path: put it back first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.674490, 0.0, 0.674490, 1.644854]

# --- model constants (tuned on the four practice cases) ---
BANDWIDTH = 0.5         # Gaussian kernel width on |ln(a_c) - ln(p)|
UNLOCK_BOOST = 2.5      # weight multiplier for rolling-midnight comparables (case is one too)
GROWTH_LIFT = 1.4       # multiplier on positive r_hat (growth hours); dips are used as-is
SPREAD_MULT = 0.85      # global multiplier on the per-hour weighted dispersion
SPREAD_FLOOR = 0.10     # smallest log-spread at any hour
SPREAD_CAP = 0.85       # largest log-spread at any hour
TRIM = 0.2              # weight trimmed from each tail of the per-hour ratio distribution
MIN_DAY_POINTS = 10     # a comparable needs at least this many known release-day hours


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up; whole numbers come back as int."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def _epoch(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def release_day_curve(comp: dict) -> list[float] | None:
    """The comparable's release-day hourly viewers, hours 1..24, or None.

    Missing hours are filled by interpolation in log space (flat beyond the
    known ends). Returns None when the day is too sparse or hour 1 is absent.
    """
    start = _epoch(comp["day_start"])
    known: dict[int, float] = {}
    for row in comp.get("hourly") or []:
        try:
            idx = int(round((_epoch(row["from"]) - start) / 3600.0))
            v = row.get("viewers")
        except Exception:
            continue
        if 0 <= idx <= 23 and v is not None and v > 0:
            known[idx] = float(v)
    if 0 not in known or len(known) < MIN_DAY_POINTS:
        return None
    idxs = sorted(known)
    curve = []
    for i in range(24):
        if i in known:
            curve.append(known[i])
            continue
        lo = max((j for j in idxs if j < i), default=None)
        hi = min((j for j in idxs if j > i), default=None)
        if lo is None:
            curve.append(known[hi])
        elif hi is None:
            curve.append(known[lo])
        else:
            frac = (i - lo) / (hi - lo)
            curve.append(math.exp(math.log(known[lo]) + frac * (math.log(known[hi]) - math.log(known[lo]))))
    return curve


def trimmed_weighted_mean(pairs: list[tuple[float, float]]) -> float:
    """Weighted mean of (value, weight) pairs, TRIM of the weight cut per tail."""
    ordered = sorted(pairs)
    total = sum(w for _, w in ordered)
    lo_cut = TRIM * total
    hi_cut = (1.0 - TRIM) * total
    acc = 0.0
    num = 0.0
    den = 0.0
    for value, w in ordered:
        start = acc
        acc += w
        keep = min(acc, hi_cut) - max(start, lo_cut)
        if keep > 0:
            num += value * keep
            den += keep
    return num / den if den > 0 else ordered[len(ordered) // 2][0]


def comparable_curves(case: dict, p: float) -> list[tuple[float, list[float]]]:
    """(weight, log-ratio curve for hours 2..24) for each usable comparable."""
    game_name = (case.get("game") or {}).get("name") or ""
    case_rolling = "midnight" in (case.get("notes") or "").lower()
    log_p = math.log(p)
    out = []
    for comp in case.get("comparables") or []:
        name = comp.get("name") or ""
        if game_name and (name == game_name or name.startswith(game_name)):
            continue
        if "category before release" in name:
            continue
        curve = release_day_curve(comp)
        if curve is None:
            continue
        anchor = curve[0]
        log_anchor = math.log(anchor)
        w = math.exp(-0.5 * ((log_anchor - log_p) / BANDWIDTH) ** 2)
        if case_rolling and "midnight" in (comp.get("unlock") or "").lower():
            w *= UNLOCK_BOOST
        ratios = [math.log(curve[i]) - log_anchor for i in range(1, 24)]
        out.append((w, ratios))
    return out


def ensemble(case: dict, p: float) -> tuple[list[float], list[float]]:
    """(r_hat, spread) per forecast hour, hours 2..24 in order."""
    curves = comparable_curves(case, p)
    if not curves:
        return [0.0] * 23, [0.15 * math.sqrt(h - 1) for h in range(2, 25)]
    r_hat = []
    spread = []
    for j in range(23):
        pairs = [(ratios[j], w) for w, ratios in curves]
        centre = trimmed_weighted_mean(pairs)
        wsum = sum(w for _, w in pairs)
        var = sum(w * (r - centre) ** 2 for r, w in pairs) / wsum
        s = SPREAD_MULT * math.sqrt(var)
        if centre > 0:
            centre *= GROWTH_LIFT
        r_hat.append(centre)
        spread.append(min(SPREAD_CAP, max(SPREAD_FLOOR, s)))
    return r_hat, spread


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p = max(1.0, float(first["viewers"]))
    r_hat, spread = ensemble(case, p)
    rows = []
    for row in case["forecast"]:
        j = row["hour"] - 2
        med = p * math.exp(r_hat[j])
        q = [round2(med * math.exp(z * spread[j])) for z in Z]
        rows.append({"hour": row["hour"], "q": q})
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
