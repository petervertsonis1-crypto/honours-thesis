#!/usr/bin/env python3
"""
narrowband_check.py -- is detect_bursts() missing narrowband signals because
it measures power across the whole capture bandwidth?

AIS occupies ~14 kHz and POCSAG ~12.5 kHz inside a 2.4 MHz capture. Full-band
power measurement therefore integrates noise over ~170x the signal bandwidth,
costing roughly 20 dB of SNR before detection begins. DAB+ (1.536 MHz) fills
the window, which is consistent with it being the one band that worked.

This shifts the channel of interest to DC, low-pass filters, decimates, and
re-runs identify() at the reduced rate. If bursts appear that were invisible
at 2.4 MS/s, the sensitivity limit is the wideband measurement, not the air.

Usage:
    python validation/experiments/narrowband_check.py ais --offset -25000
    python validation/experiments/narrowband_check.py ais --offset  25000
    python validation/experiments/narrowband_check.py pager --offset 0
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import decimate, welch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from iq_protocol_id import identify, detect_bursts   # noqa: E402

SWEEP_DIR = REPO / "captures" / "sweep"


def latest(name):
    js = sorted(SWEEP_DIR.glob(f"{name}_*.json"))
    if not js:
        sys.exit(f"no capture named {name} in {SWEEP_DIR}")
    js = js[-1]
    return js.with_suffix(".npy"), json.loads(js.read_text())


def channelise(x, fs, offset_hz, target_fs):
    """Shift offset_hz to DC, then decimate in stages down to ~target_fs.

    Staged decimation because scipy's FIR decimate degrades badly at large
    single-step factors. Returns (y, actual_fs).
    """
    if offset_hz:
        n = np.arange(len(x), dtype=np.float64)
        x = x * np.exp(-2j * np.pi * offset_hz * n / fs).astype(np.complex64)

    total = int(round(fs / target_fs))
    y, cur = x, fs
    for f in staged_factors(total):
        y = decimate(y, f, ftype="fir", zero_phase=True)
        cur /= f
    return y.astype(np.complex64), cur


def staged_factors(n, cap=10):
    """Break n into factors <= cap, e.g. 50 -> [10, 5]."""
    out = []
    for f in (10, 8, 7, 6, 5, 4, 3, 2):
        while n % f == 0 and n > 1:
            out.append(f)
            n //= f
        if n == 1:
            break
    if n > 1:
        out.append(n)          # prime remainder, take the hit
    return [f for f in out if f > 1] or [1]


def band_profile(x, fs, label):
    """Where is the energy? Narrowband signal vs flat impulsive noise."""
    f, p = welch(x, fs, nperseg=min(4096, len(x)), return_onesided=False)
    order = np.argsort(f)
    f, p = f[order], p[order]
    peak = f[np.argmax(p)]
    flat = float(np.exp(np.mean(np.log(p + 1e-30))) / (np.mean(p) + 1e-30))
    print(f"  {label:<10} peak at {peak/1e3:>8.1f} kHz   "
          f"spectral flatness {flat:.3f}"
          f"   ({'flat/impulsive' if flat > 0.5 else 'structured'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("band")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="Hz from capture centre to bring to DC")
    ap.add_argument("--target-fs", type=float, default=48000.0)
    ap.add_argument("--max-samples", type=int, default=None)
    args = ap.parse_args()

    npy, meta = latest(args.band)
    fs = meta["fs_hz"]
    x = np.load(npy)
    if args.max_samples:
        x = x[: args.max_samples]

    print(f"{args.band}: {meta['centre_hz']/1e6:.3f} MHz, {len(x)} samples "
          f"@ {fs/1e6:.1f} MS/s")
    print(f"expected {meta['expect']}, shifting {args.offset/1e3:+.1f} kHz to DC\n")

    print("spectrum before/after:")
    band_profile(x[: 2_000_000], fs, "wideband")

    y, new_fs = channelise(x, fs, args.offset, args.target_fs)
    print(f"  channelised to {new_fs/1e3:.1f} kS/s, {len(y)} samples")
    band_profile(y, new_fs, "narrowband")

    # what the detector sees, before and after
    bw, nw = detect_bursts(x, fs)
    bn, nn = detect_bursts(y, new_fs)
    print(f"\nbursts at {fs/1e6:.1f} MS/s: {len(bw):>4}   "
          f"(noise floor {nw:.1f} dB)")
    print(f"bursts at {new_fs/1e3:.1f} kS/s: {len(bn):>4}   "
          f"(noise floor {nn:.1f} dB)")

    if not bn:
        print("\nnothing detected after channelisation either")
        return

    print(f"\nidentify() on the channelised signal:")
    results = identify(y, new_fs, rf_center_hz=meta["centre_hz"] + args.offset)
    for i, r in enumerate(results):
        b, ft = r.best, r.features
        label = b["name"] if b else "(nothing scored)"
        score = f"{b['score']:.2f}" if b else "  - "
        mark = "*" if r.confident else " "
        print(f"  {mark} burst {i:<2} {ft.duration*1e3:>7.2f} ms  "
              f"snr {ft.snr_db:>5.1f} dB  cv {ft.envelope_cv:>5.2f}  "
              f"score {score}  {label}")


if __name__ == "__main__":
    main()