# validation/

Verification of Philip's multi-protocol detector (`phwl/doodles`,
`wprotocol/preamble`) against real ADS-B captures.

## Setup

Both `captures/` and `external/` are gitignored, so a fresh clone needs:

```bash
git clone https://github.com/phwl/doodles.git external/doodles
pip install -r requirements.txt          # numpy, scipy, matplotlib
```

Captures are `.npy` files of `complex64` IQ recorded at 2.4 MS/s, centred on
1090 MHz, via `sources/soapy_capture.py`.

Run everything from the repository root.

## tools/

`ground_truth.py` — runs our own gated `ADSBReceiver` over every capture and
records which frames decode with a valid CRC. Writes `ground_truth.json`. The
CRC acts as an independent oracle: it confirms a frame is present without
relying on anything in Philip's pipeline. **Run this first** — the experiment
scripts read its output.

`run_protocol_id.py` — calls Philip's `identify()` on a `.npy` capture and
prints his report plus preamble-hit detail. His CLI can't read `.npy` (it uses
`np.fromfile`, which would treat the 128-byte header as IQ samples), so this
calls the library directly.

```bash
python validation/tools/ground_truth.py
python validation/tools/run_protocol_id.py captures/adsb_candidate_001_lm.npy
```

## experiments/

`probe_preamble.py` — computes the ADS-B matched-filter correlation at each
CRC-verified frame index and compares it against the threshold the bank
requires. Shows that at 2.4 MS/s the 8 µs template is only 19 samples, which
drives `threshold_for_pfa` into its 0.999 cap; with `min_margin = 1.05` the
required correlation exceeds 1.0 and can never be reached at any SNR.

`test_resample.py` — interpolates 4x to 9.6 MS/s to make the threshold
reachable, confirming the filter itself locates frames correctly. Also runs
noise-only trials: all of them produce hits, because interpolation inflates the
template length without adding independent noise samples, so the p_fa = 1e-6
claim does not survive.

`walk_envelope.py` — compares the measured `envelope_cv` of a real burst
against ideal OOK and against simulations with band-limiting and noise. Explains
why a real ADS-B burst measures 0.43 against the 0.70 needed for the
`ook-pulsed` modulation class.

`test_rate_vs_fs.py` — runs both symbol rate estimators on simulated ADS-B
across sample rates. Both start working around 3 samples per pulse (~6 MS/s for
ADS-B). Note the run-length estimator reports ~2x the chip rate because it
measures the 0.5 µs pulse, not the 1 µs bit — which is why the ADS-B database
entry uses a `rate` range of 0.9–2.6 MHz.

`sweep_rate_limit.py` — sweeps symbol rate with the sample rate fixed at
2.4 MS/s to locate the operating envelope. Spectral estimator needs ~3 samples
per symbol (up to ~800 kHz here); run-length needs ~3 samples per shortest pulse
(up to ~400 kHz).

## Findings so far

Four captures are CRC-verified: 001, 003, 010, 011.

1. The blind classifier measures `envelope_cv = 0.433` on a real ADS-B burst
   against a 0.70 gate, so it returns `linear-shaped`. `MOD_COMPAT` has no path
   from `linear-shaped` to `ook-pulsed`, so ADS-B scores zero and is dropped
   before ranking. Forcing `ook-pulsed` makes ADS-B win at 100%, with
   Mode A/C/S second at 81.6% — everything downstream is fine.

2. The preamble bank cannot fire at 2.4 MS/s for arithmetic reasons, not
   signal reasons. The correlation peaks on the correct frame in 3 of 4
   captures.

3. Symbol rate estimation is unavailable for this protocol at this sample rate:
   the spectral method is too noisy on a 288-sample frame, and the run-length
   method is below its resolution limit at 1.2 samples per pulse.

All three trace to the same cause: 2.4 MS/s gives 1.2 samples per 0.5 µs pulse.

## Open

- `estimate_symbol_rate` returns 1.28–1.36x the true rate on GFSK at 50–100 kHz,
  where it has 24–48 samples per symbol and should be comfortable. Not a
  resolution problem — likely the harmonic walk in `_fundamental`.