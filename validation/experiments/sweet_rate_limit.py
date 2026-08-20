#!/usr/bin/env python3
"""Where does symbol rate estimation break at 2.4 MS/s?

Sweeps symbol rate with the sample rate fixed at the RTL-SDR's 2.4 MS/s and
runs both of Philip's estimators. Two signal types, because the two estimators
target different things: pulsed OOK (run-length path) and GFSK (spectral path).

Reports, for each rate: how often an estimate is returned at all, and how
accurate it is when it is.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sps

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))
from iq_protocol_id import estimate_symbol_rate, estimate_pulse_rate  # noqa: E402

FS = 2.4e6
SNR_DB = 15.0
N_SYM = 200
TRIALS = 8


def synth_ook(rate, seed):
    """Pulsed OOK: half-symbol pulse in each slot (ADS-B-like)."""
    rng = np.random.default_rng(seed)
    over = 40
    fs_hi = rate * over
    bits = rng.integers(0, 2, N_SYM)
    env = np.zeros(N_SYM * over)
    for i, b in enumerate(bits):
        s = i * over + (0 if b else over // 2)
        env[s:s + over // 2] = 1.0
    h = sps.firwin(201, min(0.9, 3.0 * rate / (fs_hi / 2)))
    env = sps.lfilter(h, 1.0, env)
    return resample_noise(env, rate, seed)


def synth_gfsk(rate, seed):
    """2-FSK with deviation = half the symbol rate."""
    rng = np.random.default_rng(seed + 999)
    over = 40
    fs_hi = rate * over
    bits = rng.integers(0, 2, N_SYM) * 2.0 - 1.0
    f = np.repeat(bits, over) * (rate / 2.0)
    g = sps.windows.gaussian(over * 3, over / 3.0)
    f = np.convolve(f, g / g.sum(), mode="same")
    ph = 2 * np.pi * np.cumsum(f) / fs_hi
    return resample_noise(np.exp(1j * ph), rate, seed)


def resample_noise(sig, rate, seed):
    rng = np.random.default_rng(seed + 7)
    m = int(round(N_SYM / rate * FS))
    y = sps.resample(sig, m).astype(np.complex64)
    p = np.mean(np.abs(y) ** 2)
    npow = p / (10 ** (SNR_DB / 10))
    return y + np.sqrt(npow / 2) * (rng.standard_normal(m)
                                    + 1j * rng.standard_normal(m)).astype(np.complex64)


print(f"fs fixed at {FS/1e6} MS/s, {N_SYM} symbols, SNR {SNR_DB} dB, "
      f"{TRIALS} trials each\n")

for kind, synth, est in (
        ("pulsed OOK", synth_ook, "run-length"),
        ("GFSK", synth_gfsk, "spectral")):
    print(f"=== {kind} ===")
    print(f"{'symbol rate':>12} {'smp/sym':>8}   {'returned':>9}   "
          f"{'median estimate':>15}   ratio to truth")
    print("-" * 74)
    for rate in (50e3, 100e3, 200e3, 300e3, 400e3, 600e3, 800e3,
                 1.0e6, 1.2e6, 1.5e6):
        got = []
        for t in range(TRIALS):
            y = synth(rate, t)
            if kind == "pulsed OOK":
                d = estimate_pulse_rate(y, FS)
            else:
                d = estimate_symbol_rate(y, FS, bw_hint=3 * rate)
            if d:
                got.append(d["symbol_rate"])
        n = len(got)
        if n:
            med = float(np.median(got))
            print(f"{rate/1e3:10.0f}k {FS/rate:8.1f}   {n:4d}/{TRIALS:<4d}   "
                  f"{med/1e3:12.0f}k     {med/rate:.2f}x")
        else:
            print(f"{rate/1e3:10.0f}k {FS/rate:8.1f}   {n:4d}/{TRIALS:<4d}   "
                  f"{'—':>13}     —")
    print()