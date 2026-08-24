#!/usr/bin/env python3
"""
interp_check.py — does envelope_cv recover when we interpolate?

Case 1 (fixable in software): the dips between pulses exist in the capture,
we're just not sampling them. cv climbs toward 1.0 with interpolation.
Case 2 (hardware limit): the radio's filter already smoothed them away.
cv stays flat no matter how fine the grid.

results:
        rate   samples      cv
       2.4 MS/s       288   0.521
       4.8 MS/s       576   0.510
       9.6 MS/s      1152   0.512
      19.2 MS/s      2304   0.512
      38.4 MS/s      4608   0.512
    
Case 2.
"""

import numpy as np
from pathlib import Path
import sys
from scipy.signal import resample_poly

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from iq_protocol_id import detect_bursts

CAPTURE = "captures/adsb_candidate_001_lm.npy"
FS = 2.4e6
FRAME_SAMPLES = int(120e-6 * FS)   # ADS-B frame is 120 us


def envelope_cv(iq):
    """Coefficient of variation of the envelope: std/mean of |x|."""
    env = np.abs(iq)
    return float(np.std(env) / np.mean(env))

def main(start_idx):
    iq = np.load(CAPTURE)
    frame = iq[start_idx : start_idx + FRAME_SAMPLES]

    print(f"frame at {start_idx}, {len(frame)} samples @ {FS/1e6:.1f} MS/s\n")
    print(f"{'rate':>12}  {'nbursts':>7}  {'i0':>6}  {'i1':>6}  {'cv_burst':>8}  {'cv_full':>7}")

    for up in (1, 2, 4, 8, 16):
        x = frame if up == 1 else resample_poly(frame, up, 1)
        fs = FS * up
        bursts, noise_db = detect_bursts(x, fs)
        b = max(bursts, key=lambda b: b.i1 - b.i0)   # largest burst
        seg = x[b.i0:b.i1]
        print(f"{fs/1e6:>10.1f} MS/s  {len(bursts):>7}  {b.i0:>6}  {b.i1:>6}  "
              f"{envelope_cv(seg):>8.3f}  {envelope_cv(x):>7.3f}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]))