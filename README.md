# polymarket-nvidia-ceo-forecast-01 — round 2

Forecasts the Yes price of every trading market of Polymarket's
"Next CEO of NVIDIA?" event, minute by minute, for the 240 minutes after
each checkpoint, as five quantiles (5%, 25%, 50%, 75%, 95%) per minute.

## How it works

For each market, independently, using only that case's own price history:

1. **Empirical change quantiles at anchor horizons.** For horizons of 1, 2,
   4, 8, 16, 32, 64, 128 and 240 minutes, collect the overlapping price
   changes over that many minutes across the most recent 12 hours of
   prices, and take the empirical quantiles of those changes. Prices here
   move in steps — flat for minutes, then a tick, sometimes a jump — so the
   change distribution is mostly zero with occasional large moves. The
   empirical quantiles capture a centre far narrower than a Gaussian
   spread would suggest, and tails far fatter and asymmetric.
2. **Shrinkage toward persistence, median centred.** Each anchor's
   forecast quantiles are centred on the last price (the empirical median
   change is mostly noise) and blended 60% toward the flat persistence
   forecast (last price held constant), so the forecast is not
   overconfident about moves it has only seen a few of.
3. **Local-volatility scaling of the spread.** The spread is multiplied by
   a factor from the market's own recent volatility: the root-mean-square
   of its 1-minute moves over the most recent 60 minutes, divided by the
   same over the most recent 12 hours, square-rooted and clipped to
   [0.7, 1.5]. Prices cluster in quiet stretches and jumpy stretches —
   the last hour's volatility predicts the next four hours' better than
   the 12-hour average does (correlation about 0.45 on the practice cases,
   against 0.23 for the 12-hour average) — so a market that has sat still
   lately gets a narrower forecast and one that just moved gets a wider
   one, instead of every market getting the same 12-hour spread.
4. **Interpolation.** Horizons between anchors are interpolated in the
   square root of the horizon, matching how a random walk's spread grows.
5. **Cleanup.** Every value is clamped to [0, 1], rounded to 6 decimals,
   and each row is sorted so the five quantiles are non-decreasing.

## Validation (practice cases p00–p05)

Mean pinball loss (×100) on the six practice cases, scored against the
reconstructed answers:

| forecaster | mean | p00–p02 | p03–p05 |
|---|---|---|---|
| house baseline | 0.372 | 0.442 | 0.302 |
| round 1 (no local-vol factor) | 0.312 | 0.397 | 0.228 |
| **round 2 (this entry)** | **0.307** | **0.393** | **0.221** |

Round 2 beats round 1 on both halves of the practice and on 5 of the 6
cases. Ideas that were tried and rejected: a mean-reversion drift on the
last 60 minutes' move (looks good in aggregate but its coefficient
collapses once the two or three biggest moves are removed, and it hurts
the case that follows the biggest jump); taking the 5%/95% tails from a
72-hour window (much worse — the early window is a different regime);
cross-market information from the sum of the 24 prices or from other
markets' moves (no predictive power once the market's own move is known).

## Running it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

It reads every `*.in` case file in the input directory and writes one
`<id>.out` forecast file per case into the output directory. Python 3.13,
standard library only, deterministic, no network access. A run over all
six practice cases takes about half a second on one CPU, and two runs
produce byte-identical output.

## License

MIT — see `LICENSE`.
