#!/usr/bin/env python3
"""Does a faster SDR fix symbol rate estimation for ADS-B?

Simulates a 112-bit ADS-B frame at a range of sample rates, adds noise at a
realistic SNR, and runs both of Philip's estimators on it.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sps

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))
from iq_protocol_id import estimate_symbol_rate, estimate_pulse_rate  # noqa: E402

TRUE_RATE = 1e6
SNR_DB = 13.6


def synth(fs, n_bits=112, seed=0):
    """0.5 us pulse in each 1 us slot, band-limited, with noise."""
    rng = np.random.default_rng(seed)
    over = 40                                   # build at 40x then decimate
    fs_hi = TRUE_RATE * over
    n = int(n_bits * over)
    bits = rng.integers(0, 2, n_bits)
    env = np.zeros(n)
    for i, b in enumerate(bits):
        s = i * over + (0 if b else over // 2)
        env[s:s + over // 2] = 1.0
    # receiver front-end filter, then resample to fs
    h = sps.firwin(201, min(0.9, 2.6e6 / (fs_hi / 2)))
    env = sps.lfilter(h, 1.0, env)
    m = int(round(n_bits * 1e-6 * fs))
    y = sps.resample(env, m).astype(np.complex64)
    p = np.mean(np.abs(y) ** 2)
    npow = p / (10 ** (SNR_DB / 10))
    y = y + np.sqrt(npow / 2) * (rng.standard_normal(m)
                                 + 1j * rng.standard_normal(m)).astype(np.complex64)
    return y


def fmt(d):
    if d is None:
        return "None"
    return f"{d['symbol_rate']/1e6:.3f} MHz  ({d['method']})"


print(f"true chip rate {TRUE_RATE/1e6:.1f} MHz, 112-bit frame, SNR {SNR_DB} dB\n")
print(f"{'fs':>8} {'smp/chip':>9} {'total smp':>10}   "
      f"{'run-length':<32} spectral")
print("-" * 100)
for fs in (2.4e6, 4e6, 6e6, 8e6, 12e6, 20e6, 40e6):
    y = synth(fs)
    a = np.abs(y).astype(float)
    cv = a.std() / a.mean()
    pr = estimate_pulse_rate(y, fs)
    sr = estimate_symbol_rate(y, fs, bw_hint=4e6)
    print(f"{fs/1e6:6.1f}M {fs/TRUE_RATE/2:9.1f} {y.size:10d}   "
          f"{fmt(pr):<32} {fmt(sr)}")
    print(f"{'':>8} {'cv=':>9}{cv:.3f}")