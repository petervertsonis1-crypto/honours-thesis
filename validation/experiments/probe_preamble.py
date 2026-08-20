#!/usr/bin/env python3
"""Probe Philip's ADS-B matched filter at a known-good (CRC-verified) index.

Asks: what rho does the template actually achieve on a real frame, and what
rho would it need to be reported as a hit?
"""
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from validation.tools.ground_truth import load_truth  # noqa: E402

from iq_preamble import (ADSB_PREAMBLE, PreambleBank, normalized_correlate,  # noqa: E402
                         threshold_for_pfa, _cfo_grid)

FS = 2.4e6


bank = PreambleBank()
tpl = ADSB_PREAMBLE
r = tpl.synth(FS)
grid = _cfo_grid(tpl.cfo_span, tpl.duration())

print(f"template: {tpl.name}")
print(f"  duration {tpl.duration()*1e6:.1f} us -> N = {r.size} samples @ {FS/1e6} MS/s")
print(f"  cfo grid: {grid.size} point(s)")

for name, t_us in load_truth().items():
    x = np.load(REPO / "captures" / name).astype(np.complex64)

    n_pos = max(1, int(4 * x.size / r.size))
    n_trials = n_pos * grid.size * max(1, len(bank.templates))
    thr = threshold_for_pfa(r.size, n_trials, bank.p_fa)
    required = thr * bank.min_margin

    rho, cfo = normalized_correlate(x, r, grid, FS)

    k_true = int(round(t_us * 1e-6 * FS))
    # our index is the preamble start; search a small window for the peak
    w = 12
    lo, hi = max(0, k_true - w), min(rho.size, k_true + w)
    k_local = lo + int(np.argmax(rho[lo:hi]))
    k_glob = int(np.argmax(rho))

    print(f"\n{name}")
    print(f"  threshold {thr:.4f}  x min_margin {bank.min_margin} "
          f"-> rho must exceed {required:.4f}")
    print(f"  rho at CRC-verified frame  = {rho[k_local]:.4f}  "
          f"(offset {k_local - k_true:+d} samples)")
    print(f"  rho peak anywhere in record = {rho[k_glob]:.4f} "
          f"at t={k_glob/FS*1e6:.1f} us")
    print(f"  margin at true frame = {rho[k_local]/thr:.3f}x  "
          f"-> {'HIT' if rho[k_local] >= required else 'no hit'}")

# What would the threshold need in the way of template length?
print("\n--- threshold vs template length (same n_trials scale) ---")
n_trials = max(1, int(4 * 262144 / 19)) * 1 * 9
print(f"n_trials = {n_trials:,}, p_fa = 1e-6, ln(n_trials/p_fa) = "
      f"{math.log(n_trials/1e-6):.2f}")
for fs_hz in (2.4e6, 4e6, 8e6, 12e6, 20e6):
    n = int(round(tpl.duration() * fs_hz))
    t = threshold_for_pfa(n, n_trials, 1e-6)
    print(f"  fs={fs_hz/1e6:5.1f} MS/s  N={n:4d}  threshold={t:.4f}"
          f"{'   (saturated at cap — unreachable)' if t >= 0.999 else ''}")