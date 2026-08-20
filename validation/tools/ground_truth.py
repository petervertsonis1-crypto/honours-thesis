#!/usr/bin/env python3
"""Ground truth for validating Philip's identify().

Runs our own gated ADSBReceiver over every capture and records which frames
decode with a valid CRC. A CRC-OK row is an independent oracle: an ADS-B frame
is definitely present at that sample offset.

Writes validation/ground_truth.json so the experiment scripts can read the same
numbers rather than hardcoding them.

Usage:
    python validation/tools/ground_truth.py
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from adsb.adsb import ADSBReceiver  # noqa: E402

FS = 2.4e6
OUT = REPO / "validation" / "ground_truth.json"


def main():
    rows = []
    for path in sorted(glob.glob(str(REPO / "captures" / "*.npy"))):
        name = Path(path).name
        x = np.load(path)
        try:
            dets = ADSBReceiver(FS).process(x)
        except Exception as e:  # noqa: BLE001
            print(f"{name:32s} ERROR {type(e).__name__}: {e}")
            continue
        if not dets:
            print(f"{name:32s} no detection")
            continue
        for d in dets:
            pkt = d.packet
            rows.append(dict(
                capture=name,
                sample=int(d.preamble_index),
                t_us=d.preamble_index / FS * 1e6,
                df=int(pkt.downlink_format),
                crc_ok=bool(pkt.crc_ok),
                hex=pkt.hex,
            ))
            print(f"{name:32s} t0={rows[-1]['t_us']:9.1f} us  "
                  f"DF{rows[-1]['df']:<3} crc_ok={rows[-1]['crc_ok']}  "
                  f"{rows[-1]['hex']}")

    OUT.write_text(json.dumps(dict(fs=FS, detections=rows), indent=2))
    ok = sum(r["crc_ok"] for r in rows)
    print(f"\n{len(rows)} detections, {ok} CRC-verified -> {OUT.relative_to(REPO)}")


def load_truth(crc_only=True):
    """Helper for the experiment scripts: {capture_name: t_us}."""
    if not OUT.exists():
        raise SystemExit(f"{OUT} missing — run validation/tools/ground_truth.py first")
    d = json.loads(OUT.read_text())
    return {r["capture"]: r["t_us"] for r in d["detections"]
            if r["crc_ok"] or not crc_only}


if __name__ == "__main__":
    main()