#!/usr/bin/env python3
"""Run Philip's blind classifier + preamble bank on saved .npy IQ captures.

His CLI uses np.fromfile, which would read the 128-byte NPY header as IQ
samples, so we call identify() as a library instead.

Usage:
    python run_protocol_id.py captures/adsb_candidate_001_lm.npy
    python run_protocol_id.py captures/*.npy --quiet
"""
import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from iq_preamble import PreambleBank, ADSB_PREAMBLE, default_templates  # noqa: E402
from iq_protocol_id import identify, format_report  # noqa: E402

FS = 2.4e6
FC = 1090e6


def run(path, bank, fs, fc, verbose=True):
    x = np.load(path).astype(np.complex64)
    print(f"\n{'=' * 70}\n{Path(path).name}  "
          f"({x.size} samples, {x.size / fs * 1e3:.1f} ms @ {fs / 1e6:.1f} MS/s)"
          f"\n{'=' * 70}")

    results = identify(x, fs, rf_center_hz=fc, preamble_bank=bank)
    print(format_report(results, verbose=verbose))

    # Preamble-stage detail: this is the part we actually care about validating.
    hits = [r.preamble for r in results if r.preamble is not None]
    if hits:
        print(f"\n  preamble hits ({len(hits)}):")
        for h in hits:
            print(f"    {h.name} @ t0={h.t0 * 1e6:.1f} us  "
                  f"rho={h.rho:.4f}  thr={h.threshold:.4f}  "
                  f"margin={h.margin:.2f}x  N={h.n_template}  "
                  f"gain={h.processing_gain_db:.1f} dB  "
                  f"implied SNR={h.est_snr_db:+.1f} dB")
    else:
        print("\n  preamble hits: none")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures", nargs="+")
    ap.add_argument("--fs", type=float, default=FS)
    ap.add_argument("--fc", type=float, default=FC)
    ap.add_argument("--adsb-only", action="store_true",
                    help="restrict the bank to the ADS-B template")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    templates = [ADSB_PREAMBLE] if a.adsb_only else default_templates()
    bank = PreambleBank(templates)
    print(f"bank: {len(bank.templates)} template(s), p_fa={bank.p_fa:g}, "
          f"min_margin={bank.min_margin}")

    for c in a.captures:
        run(c, bank, a.fs, a.fc, verbose=not a.quiet)


if __name__ == "__main__":
    main()