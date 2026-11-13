# polymarket-nvidia-ceo-forecast-01

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
   forecast quantiles (last price plus the quantiles of change) are blended
   60% toward the flat persistence forecast (last price held constant), so
   the forecast is not overconfident about moves it has only seen a few
   of. The median is kept exactly at the last price: the empirical median
   change is mostly noise — a few jumps dominate it — and letting it drag
   the median costs more than it saves. Only the spread around the median
   comes from the empirical quantiles.
3. **Interpolation.** Horizons between anchors are interpolated in the
   square root of the horizon, matching how a random walk's spread grows.
4. **Cleanup.** Every value is clamped to [0, 1], rounded to 6 decimals,
   and each row is sorted so the five quantiles are non-decreasing.

## Running it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

It reads every `*.in` case file in the input directory and writes one
`<id>.out` forecast file per case into the output directory. Python 3.13,
standard library only, deterministic, no network access.

## License

MIT — see `LICENSE`.
