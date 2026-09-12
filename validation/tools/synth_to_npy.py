#!/usr/bin/env python3
"""
wifi_to_npy.py -- convert MATLAB's interleaved float32 .bin output into the
npy + json sidecar pair that run_sweep_id.py already reads.

MATLAB can't write .npy, so gen_wifi.m dumps raw interleaved float32. That
maps straight onto complex64 with no conversion -- np.fromfile reads I,Q pairs
as complex directly.

Usage:
    python validation/tools/wifi_to_npy.py
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
GEN_DIR = REPO / "captures" / "generated"


def read_sidecar(path):
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    bins = sorted(
        b for b in GEN_DIR.glob("*.bin")
        if not b.name.startswith(".")
    )
    if not bins:
        raise SystemExit(f"no .bin files in {GEN_DIR} -- run gen_wifi.m first")

    for b in bins:
        txt = b.with_suffix(".txt")
        if not txt.exists():
            print(f"{b.name}: no .txt sidecar, skipping")
            continue

        m = read_sidecar(txt)
        iq = np.fromfile(b, dtype=np.complex64)

        n_expected = int(m.get("n_samples", 0))
        if n_expected and len(iq) != n_expected:
            print(f"{b.name}: WARNING got {len(iq)}, sidecar says {n_expected}")

        peak = float(np.max(np.abs(iq)))
        mean_db = float(10 * np.log10(np.mean(np.abs(iq) ** 2) + 1e-30))
        peak_db = float(10 * np.log10(
            np.percentile(np.abs(iq) ** 2, 99.9) + 1e-30))

        base = GEN_DIR / b.stem
        np.save(base.with_suffix(".npy"), iq)
        base.with_suffix(".json").write_text(json.dumps(dict(
            name=b.stem,
            source=m.get("source", "matlab_generated"),
            centre_hz=float(m.get("centre_hz", 0)),
            fs_hz=float(m["fs_hz"]),
            gain_db=None, agc=None, antenna=None,
            duration_s=len(iq) / float(m["fs_hz"]),
            n_samples=len(iq), dtype="complex64",
            expect=m.get("expect", "Wi-Fi"),
            expected_mod=m.get("expected_mod", "OFDM"),
            snr_db=m.get("snr_db"),
            note=f"generated, {m.get('packets','?')} packets, "
                 f"{m.get('idle_s','?')} idle",
            captured_at=datetime.now().isoformat(timespec="seconds"),
            mean_power_db=round(mean_db, 1),
            peak_power_db=round(peak_db, 1),
            overflows=0, timeouts=0,
        ), indent=2))

        print(f"{b.stem:<22} {len(iq):>9} samples @ "
              f"{float(m['fs_hz'])/1e6:.1f} MS/s  peak {peak:.2f}  "
              f"peak-mean {peak_db - mean_db:>5.1f} dB")

    print(f"\nwritten to {GEN_DIR}")


if __name__ == "__main__":
    main()