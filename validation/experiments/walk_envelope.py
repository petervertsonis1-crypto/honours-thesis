#!/usr/bin/env python3
"""What envelope_cv *should* an ADS-B burst have, and what do we measure?"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sps

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))
from iq_protocol_id import detect_bursts  # noqa: E402

FS = 2.4e6


def stats(a):
    a = np.abs(a).astype(np.float64)
    cv = a.std() / (a.mean() + 1e-30)
    papr = 10 * np.log10(a.max() ** 2 / (np.mean(a ** 2) + 1e-30))
    return cv, papr


# --- 1. the textbook case: perfect on/off, 50% duty, no noise, no filtering ---
ideal = np.array([1.0, 0.0] * 500)
cv, papr = stats(ideal)
print(f"ideal square OOK, 50% duty   cv={cv:.3f}  papr={papr:.2f} dB")

# --- 2. simulated ADS-B frame: 1 Mchip/s PPM, sampled at various rates ------
def synth_adsb(fs, n_bits=112, snr_db=None, rng=None):
    """0.5 us pulse in each 1 us bit slot (PPM => always 50% duty)."""
    sps_bit = fs / 1e6                      # samples per 1 us bit
    n = int(round(n_bits * sps_bit))
    t = np.arange(n) / fs
    bit_phase = (t * 1e6) % 1.0             # position within each 1 us bit
    bits = (rng or np.random.default_rng(0)).integers(0, 2, n_bits)
    which = bits[np.minimum((t * 1e6).astype(int), n_bits - 1)]
    on = np.where(which == 1, bit_phase < 0.5, bit_phase >= 0.5)
    return on.astype(np.complex64)


print()
for fs in (2.4e6, 4.8e6, 9.6e6, 20e6):
    s = synth_adsb(fs)
    cv, papr = stats(s)
    print(f"synth ADS-B @ {fs/1e6:5.1f} MS/s  (pulse = {0.5*fs/1e6:4.1f} samples)"
          f"   cv={cv:.3f}  papr={papr:.2f} dB")

# --- 3. same, but through a receiver filter (bandwidth limiting) ------------
print()
s = synth_adsb(20e6)
for bw_mhz in (8, 5, 2.4, 1.5):
    h = sps.firwin(101, bw_mhz * 1e6 / (20e6 / 2))
    y = sps.lfilter(h, 1.0, s)
    d = int(20e6 / 2.4e6)
    y = y[::d]                              # then resample to 2.4 MS/s
    cv, papr = stats(y)
    print(f"synth ADS-B filtered to {bw_mhz:4.1f} MHz then @2.4 MS/s"
          f"   cv={cv:.3f}  papr={papr:.2f} dB")

# --- 4. add noise at various SNRs -------------------------------------------
print()
rng = np.random.default_rng(1)
s = synth_adsb(20e6)
h = sps.firwin(101, 2.4e6 / (20e6 / 2))
s = sps.lfilter(h, 1.0, s)[::int(20e6 / 2.4e6)]
sig_p = np.mean(np.abs(s) ** 2)
for snr in (30, 20, 15, 13.6, 10, 6):
    n_p = sig_p / (10 ** (snr / 10))
    noise = np.sqrt(n_p / 2) * (rng.standard_normal(s.size)
                                + 1j * rng.standard_normal(s.size))
    cv, papr = stats(s + noise)
    print(f"synth ADS-B, 2.4 MHz filter, SNR {snr:5.1f} dB"
          f"   cv={cv:.3f}  papr={papr:.2f} dB")

# --- 5. what we actually measured -------------------------------------------
x = np.load(REPO / "captures" / "adsb_candidate_001_lm.npy").astype(np.complex64)
bursts, noise_db = detect_bursts(x, FS)
b = [bb for bb in bursts if (bb.i1 - bb.i0) >= 64][0]
cv, papr = stats(x[b.i0:b.i1])
print(f"\nMEASURED capture 001 burst              cv={cv:.3f}  papr={papr:.2f} dB")
print(f"threshold for 'ook-pulsed'              cv > 0.70   papr > 2.0 dB")