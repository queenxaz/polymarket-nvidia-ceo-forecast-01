#!/usr/bin/env python3
"""Forecast Polymarket Next-CEO-of-NVIDIA Yes prices, minute by minute, 4h ahead.

Method (per market, per case, using only that case's own prices):
  * Anchor horizons of 1, 2, 4, 8, 16, 32, 64, 128 and 240 minutes.
  * For each anchor, take the overlapping price changes over that many
    minutes across the most recent 12 hours of prices and read off the
    empirical quantiles (0.05/0.25/0.5/0.75/0.95) of those changes.
    Prices move in steps -- flat for minutes, then a tick, sometimes a
    jump -- so the change distribution is a mixture that is mostly zero
    with occasional large moves; the empirical quantiles capture a centre
    far narrower than a spread-based estimate would suggest and tails far
    fatter and asymmetric.
  * Add each anchor's quantiles of change to the last price, then shrink
    them partway toward the flat persistence forecast (last price held
    constant) so the forecast is not overconfident.
  * For horizons between anchors, interpolate the anchor forecasts in the
    square root of the horizon. Clamp to [0, 1], round to 6 decimals and
    sort each row so the five quantiles are non-decreasing.

Standard library only, deterministic, no network, no model calls.
Reads every *.in in $MAKEFUN_INPUT_DIR (else /input) and writes one
<id>.out per case into $MAKEFUN_OUTPUT_DIR (else /output).
"""

import json
import math
import os
from pathlib import Path

ANCHORS = (1, 2, 4, 8, 16, 32, 64, 128, 240)
LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
WINDOW_MINUTES = 720  # most recent 12 hours of prices
BLEND = 0.60  # weight on the empirical anchor quantiles vs persistence
CENTER_MEDIAN = True  # keep the median forecast at the last price:
# the empirical median change is mostly noise (a few jumps dominate it)
# and dragging the median after it costs more than it saves; only the
# spread around the median comes from the empirical quantiles.


def empirical_quantiles(values, levels):
    """Linear-interpolation quantiles of a sorted sample (type-7 style)."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return [0.0 for _ in levels]
    if n == 1:
        return [ordered[0] for _ in levels]
    out = []
    for tau in levels:
        pos = tau * (n - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)
    return out


def anchor_forecasts(prices):
    """Return {anchor: [q05, q25, q50, q75, q95]} of absolute prices."""
    last = prices[-1]
    recent = prices[-WINDOW_MINUTES:] if len(prices) > WINDOW_MINUTES else prices
    n = len(recent)
    result = {}
    for anchor in ANCHORS:
        lag = min(anchor, n - 1) if n > 1 else 1
        if lag < 1:
            result[anchor] = [last] * len(LEVELS)
            continue
        changes = [recent[i] - recent[i - lag] for i in range(lag, n)]
        deltas = empirical_quantiles(changes, LEVELS)
        if CENTER_MEDIAN:
            median_delta = deltas[LEVELS.index(0.5)]
            deltas = [d - median_delta for d in deltas]
        result[anchor] = [
            last + BLEND * d for d in deltas
        ]
    return result


def interpolate_rows(anchors_q, horizon):
    """Forecast rows for minutes 1..horizon by sqrt-horizon interpolation."""
    sqrt_anchors = [math.sqrt(a) for a in ANCHORS]
    rows = []
    for h in range(1, horizon + 1):
        s = math.sqrt(h)
        if h <= ANCHORS[0]:
            base = anchors_q[ANCHORS[0]]
            rows.append(list(base))
            continue
        if h >= ANCHORS[-1]:
            base = anchors_q[ANCHORS[-1]]
            rows.append(list(base))
            continue
        j = 0
        while j + 1 < len(ANCHORS) and ANCHORS[j + 1] < h:
            j += 1
        a_lo, a_hi = ANCHORS[j], ANCHORS[j + 1]
        s_lo, s_hi = sqrt_anchors[j], sqrt_anchors[j + 1]
        w = (s - s_lo) / (s_hi - s_lo) if s_hi > s_lo else 0.0
        q_lo = anchors_q[a_lo]
        q_hi = anchors_q[a_hi]
        rows.append([q_lo[k] * (1.0 - w) + q_hi[k] * w for k in range(len(LEVELS))])
    return rows


def forecast_market(market, horizon):
    prices = [float(p) for p in market["prices"]]
    if not prices:
        return [[0.5] * len(LEVELS) for _ in range(horizon)]
    if len(prices) == 1:
        x = prices[0]
        return [[round(x, 6)] * len(LEVELS) for _ in range(horizon)]
    anchors_q = anchor_forecasts(prices)
    rows = interpolate_rows(anchors_q, horizon)
    cleaned = []
    for row in rows:
        vals = [min(1.0, max(0.0, v)) for v in row]
        vals = [round(v, 6) for v in vals]
        vals.sort()
        cleaned.append(vals)
    return cleaned


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for case_path in sorted(in_dir.glob("*.in")):
        with open(case_path, "r", encoding="utf-8") as f:
            case = json.load(f)
        horizon = int(case.get("horizon_minutes", 240))
        forecasts = []
        for market in case["markets"]:
            forecasts.append(
                {"id": market["id"], "q": forecast_market(market, horizon)}
            )
        out_path = out_dir / (case_path.stem + ".out")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"forecasts": forecasts}, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
