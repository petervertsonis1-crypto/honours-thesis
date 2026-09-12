#!/usr/bin/env python3
"""
run_sweep_id.py -- feed the sweep captures through Philip's identify() and
score the answers against the expected protocol from each JSON sidecar.

Uses the library API rather than the CLI: Philip's main() never passes a
preamble_bank, so stage 2 is unreachable from the command line.

Usage:
    python validation/experiments/run_sweep_id.py
    python validation/experiments/run_sweep_id.py --only ais pager
    python validation/experiments/run_sweep_id.py --verbose
    python validation/experiments/run_sweep_id.py --max-samples 12000000
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "external" / "doodles" / "wprotocol" / "preamble"))

from iq_protocol_id import identify, format_report   # noqa: E402

# band name -> substring that should appear in the winning database entry.
# None means there is no correct answer available and we are only observing.
EXPECT = {
    "adsb":     "ADS-B",
    "fm_bcast": "FM broadcast",
    "dab":      "DAB+",
    "ais":      "AIS",
    "ism433":   "ISM OOK",
    "ism915":   "LoRa",
    "pager":    "POCSAG",
    "wifi_ht20": "Wi-Fi 802.11g/n/ax 20 MHz",
    "wifi11b":   "Wi-Fi 802.11b/g",
    "wifi_ht20": "Wi-Fi 802.11g/n/ax 20 MHz",
    "wifi_ht40": "Wi-Fi 802.11n/ac/ax 40 MHz",
    "bluetooth_le1m": "Bluetooth LE 1M",
    "bluetooth_le2m": "Bluetooth LE 2M",
    "zigbee_oqpsk": "Zigbee / 802.15.4 O-QPSK DSSS",
    # AM voice. Philip's database has "Analog FM voice / NBFM" but no AM entry,
    # so there is nothing here that could be right. Coverage gap, not a failure.
    "airband":  None,
    # negative control: any confident answer at all is a false positive.
    "quiet":    None,
}


def latest_captures(directory, only=None):
    found = {}
    for js in sorted(directory.glob("*.json")):
        if js.name.startswith("."):
            continue
        npy = js.with_suffix(".npy")
        if not npy.exists():
            print("not npy.exists()")
            continue
        meta = json.loads(js.read_text())
        name = meta["name"]
        if only and name not in only:
            continue
        found[name] = (npy, meta)
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="NAME")
    ap.add_argument("--max-samples", type=int, default=None,
                    help="truncate each capture (useful for a fast first pass)")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--max-bursts", type=int, default=12)
    ap.add_argument("--verbose", action="store_true",
                    help="print Philip's full per-burst report")
    ap.add_argument("--dir", default="sweep",
                    help="subdirectory under captures/ (sweep, generated)")
    args = ap.parse_args()

    cap_dir = REPO / "captures" / args.dir
    caps = latest_captures(cap_dir, args.only)
    if not caps:
        sys.exit(f"no captures found in {cap_dir}")

    summary = []

    for name, (npy, meta) in sorted(caps.items()):
        fs = meta["fs_hz"]
        centre = meta["centre_hz"]
        x = np.load(npy)
        if args.max_samples:
            x = x[: args.max_samples]

        print(f"\n{'=' * 70}")
        print(f"{name}  --  {centre/1e6:.3f} MHz, {len(x)} samples @ {fs/1e6:.1f} MS/s")
        print(f"expected: {meta['expect']}  ({meta['expected_mod']})")
        print(f"antenna: {meta.get('antenna', '?')}  gain: {meta['gain_db']} dB")
        print("=" * 70)

        results = identify(x, fs, rf_center_hz=centre,
                           top=args.top, max_bursts=args.max_bursts)

        if not results:
            print("no bursts extracted")
            summary.append((name, 0, None, False, "no bursts"))
            continue

        if args.verbose:
            print(format_report(results, verbose=True))

        # per-burst one-liners
        confident = [r for r in results if r.confident]
        for i, r in enumerate(results):
            b = r.best
            ft = r.features
            label = b["name"] if b else "(nothing scored)"
            score = f"{b['score']:.2f}" if b else "  - "
            mark = "*" if r.confident else " "
            print(f"  {mark} burst {i:<2} {ft.duration*1e3:>7.2f} ms  "
                  f"snr {ft.snr_db:>5.1f} dB  cv {ft.envelope_cv:>5.2f}  "
                  f"score {score}  {label}")

        # score against expectation
        want = next((v for k, v in EXPECT.items() if name.startswith(k)), None)
        winners = [r.best["name"] for r in confident if r.best]
        if want is None:
            hit = None
            note = (f"{len(confident)} confident -- expected none"
                    if confident else "nothing confident (correct)")
        else:
            hit = any(want.lower() in w.lower() for w in winners)
            note = "CORRECT" if hit else f"missed (wanted {want})"

        print(f"  -> {len(results)} bursts, {len(confident)} confident. {note}")
        summary.append((name, len(results), len(confident), hit, note))

    print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}")
    print(f"{'band':<10} {'bursts':>7} {'conf':>5}  result")
    for name, nb, nc, hit, note in summary:
        print(f"{name:<10} {nb:>7} {str(nc):>5}  {note}")


if __name__ == "__main__":
    main()