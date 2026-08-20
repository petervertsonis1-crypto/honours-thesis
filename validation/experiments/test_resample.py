#!/usr/bin/env python3
"""If the ADS-B template only fails because N=19 makes the threshold
unreachable, then interpolating the capture (adding no new information)
should make it fire. That distinguishes 'threshold problem' from
'signal problem'.

Also measures the empirical false-alarm rate on noise-only records, because
resampling inflates N without adding independent samples — the p_fa
derivation assumes independence, so the claimed 1e-6 may not survive.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sps

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from validation.tools.ground_truth import load_truth  # noqa: E402

from iq_preamble import ADSB_PREAMBLE, PreambleBank  # noqa: E402

FS = 2.4e6
UP = 4                      # 2.4 -> 9.6 MS/s

bank = PreambleBank([ADSB_PREAMBLE])
fs_up = FS * UP
print(f"resampling {FS/1e6} -> {fs_up/1e6} MS/s "
      f"(N = {int(ADSB_PREAMBLE.duration()*fs_up)} samples)\n")

for name, t_us in load_truth().items():
    x = np.load(REPO / "captures" / name).astype(np.complex64)
    xu = sps.resample_poly(x, UP, 1).astype(np.complex64)
    hits = bank.scan(xu, fs_up, rf_center_hz=1090e6)
    print(f"{name}  (true frame at {t_us:.1f} us)")
    if not hits:
        print("   no hit")
    for h in hits[:3]:
        err = h.t0 * 1e6 - t_us
        print(f"   rho={h.rho:.4f} thr={h.threshold:.4f} "
              f"margin={h.margin:.2f}x  t0={h.t0*1e6:9.1f} us "
              f"({err:+8.1f} us vs truth)  implied SNR={h.est_snr_db:+.1f} dB")

# --- false alarm check on noise only ---------------------------------------
print("\n--- noise-only trials (should fire ~never at p_fa=1e-6) ---")
rng = np.random.default_rng(0)
n = 262144
fires = 0
TRIALS = 20
for i in range(TRIALS):
    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)).astype(np.complex64)
    nu = sps.resample_poly(noise, UP, 1).astype(np.complex64)
    h = bank.scan(nu, fs_up, rf_center_hz=1090e6)
    if h:
        fires += 1
        print(f"   trial {i}: FALSE ALARM rho={h[0].rho:.4f} "
              f"thr={h[0].threshold:.4f} margin={h[0].margin:.2f}x")
print(f"   {fires}/{TRIALS} noise records produced a hit")