#!/usr/bin/env python3
"""
capture_sweep.py -- grab short IQ captures across several bands so Philip's
protocol ID pipeline can be run against a variety of real signals.

Each capture writes two files into captures/sweep/:
    <name>_<timestamp>.npy    complex64 IQ
    <name>_<timestamp>.json   metadata (fs, centre freq, gain, expected protocol)

The JSON sidecar matters: identify() needs fs, and the evaluation needs to know
what we *expected* to be there so a prediction can be scored.

GAIN IS MANUAL, DELIBERATELY. soapy_capture.py uses setGainMode(True) for the
live decoder, which is right there -- AGC keeps weak aircraft in range. It is
wrong here. AGC adjusts gain in response to signal level, which compresses the
difference between loud and quiet parts of the capture. That difference is
exactly what envelope_cv measures. Manual gain also keeps power levels
comparable between bands.

NOTE ON FREQUENCIES: ADS-B, ISM 433, AU915, DAB+ 9A and the quiet control are
solid. Airband and paging are unverified guesses -- check with a waterfall
before believing a null result, since "classifier found nothing" and "nothing
was transmitting" produce identical files.

ANTENNA. A quarter wave is ~6.9 cm at 1090 MHz but ~70 cm at 100 MHz, so no
single antenna covers this table well. Each band is tagged whip (long
telescopic, good at VHF) or stub (short, good at UHF and above), and --antenna
selects one group. Run it twice, swapping antennas between passes. The choice
is recorded in the sidecar because it materially affects received power.

Usage:
    python capture_sweep.py --list
    python capture_sweep.py --duration 0.5      # quick recon pass
    python capture_sweep.py --antenna whip      # pass 1: VHF/low UHF
    python capture_sweep.py --antenna stub      # pass 2: after swapping antenna
    python capture_sweep.py --only quiet        # re-run the control per pass
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import SoapySDR
from SoapySDR import (
    SOAPY_SDR_RX,
    SOAPY_SDR_CF32,
    SOAPY_SDR_TIMEOUT,
    SOAPY_SDR_OVERFLOW,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "captures" / "sweep"
FS = 2.4e6              # RTL-SDR is unreliable above ~2.4-3.2 MS/s
SETTLE_S = 0.3          # discard this much after retuning; PLL + AGC settling
READ_SAMPLES = 131072   # same buffer size as soapy_capture.py
STALL_FACTOR = 3.0      # give up if a capture takes this much longer than asked

# name, centre Hz, tuner gain dB, dwell s, antenna, what we expect to find
BANDS = [
    # --- known-good reference, we already have ground truth here ---
    dict(name="adsb",     freq=1090.000e6, gain=40.0, dur=5.0, ant="stub",
         expect="ADS-B / Mode S", mod="OOK (PPM)",
         note="bursty, ~120 us frames; our CRC oracle works here"),

    # --- continuous signals: easy, and a good contrast to bursty ones ---
    dict(name="fm_bcast", freq=102.500e6, gain=25.0, dur=2.0, ant="whip",
         expect="FM broadcast", mod="WBFM",
         note="PICK A STRONG LOCAL STATION -- 102.5 is a guess"),

    dict(name="dab",      freq=202.928e6, gain=35.0, dur=3.0, ant="whip",
         expect="DAB+", mod="OFDM (DQPSK)",
         note="Sydney block 9A; 1.536 MHz wide so it fits in 2.4 MS/s"),

    # --- bursty narrowband: the interesting cases for burst detection ---
    dict(name="ais",      freq=162.000e6, gain=40.0, dur=10.0, ant="whip",
         expect="AIS", mod="GMSK",
         note="straddles 161.975/162.025; long dwell, harbour traffic is sparse"),

    dict(name="airband",  freq=120.500e6, gain=40.0, dur=10.0, ant="whip",
         expect="Airband voice", mod="AM",
         note="UNVERIFIED -- use Sydney ATIS from ERSA, it loops continuously"),

    dict(name="ism433",   freq=433.920e6, gain=40.0, dur=10.0, ant="whip",
         expect="ISM devices", mod="OOK / FSK",
         note="remotes, weather stations, TPMS; good OOK contrast to ADS-B"),

    dict(name="ism915",   freq=917.000e6, gain=40.0, dur=10.0, ant="stub",
         expect="LoRa / ISM", mod="CSS / FSK",
         note="AU915 band; LoRa chirps are a good stress test for the classifier"),

    dict(name="pager",    freq=148.600e6, gain=32.0, dur=15.0, ant="whip",
         expect="POCSAG paging", mod="2-FSK",
         note="LOW CONFIDENCE on this frequency, verify before believing a null"),

    # --- deliberate negative control ---
    dict(name="quiet",    freq=250.000e6, gain=40.0, dur=2.0, ant="whip",
         expect="nothing", mod="none",
         note="noise floor only; identify() should NOT confidently label this"),
]


def open_device():
    devices = SoapySDR.Device.enumerate()
    if not devices:
        raise RuntimeError("No SDR devices found.")
    return SoapySDR.Device(devices[0])


def capture(device, freq, gain, dur):
    """Tune, settle, then read dur seconds of IQ.

    Returns (iq, stats). Timeouts are counted and retried rather than raised --
    a quiet band legitimately produces them, and those are the bands we most
    want long dwells on.
    """
    device.setSampleRate(SOAPY_SDR_RX, 0, FS)
    device.setFrequency(SOAPY_SDR_RX, 0, freq)
    device.setGainMode(SOAPY_SDR_RX, 0, False)      # manual -- see module docstring
    device.setGain(SOAPY_SDR_RX, 0, gain)

    stream = device.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
    device.activateStream(stream)
    try:
        n_total = int(FS * (dur + SETTLE_S))
        buf = np.empty(n_total, np.complex64)
        chunk = np.empty(READ_SAMPLES, np.complex64)

        got = 0
        overflows = 0
        timeouts = 0
        deadline = time.time() + (dur + SETTLE_S) * STALL_FACTOR + 5.0

        while got < n_total:
            if time.time() > deadline:
                raise RuntimeError(
                    f"stalled at {got}/{n_total} samples "
                    f"({timeouts} timeouts, {overflows} overflows)"
                )

            result = device.readStream(
                stream, [chunk], len(chunk), timeoutUs=1_000_000
            )

            if result.ret == SOAPY_SDR_TIMEOUT:
                timeouts += 1
                continue
            if result.ret == SOAPY_SDR_OVERFLOW:
                overflows += 1
                continue
            if result.ret < 0:
                raise RuntimeError(f"readStream failed with code {result.ret}")

            take = min(result.ret, n_total - got)
            buf[got:got + take] = chunk[:take]
            got += take
    finally:
        device.deactivateStream(stream)
        device.closeStream(stream)

    iq = buf[int(FS * SETTLE_S):]
    return iq, dict(overflows=overflows, timeouts=timeouts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="NAME",
                    help="capture only these bands")
    ap.add_argument("--duration", type=float,
                    help="override dwell time for every band (seconds)")
    ap.add_argument("--antenna", choices=["whip", "stub"],
                    help="only capture bands suited to this antenna")
    ap.add_argument("--list", action="store_true",
                    help="show the band table and exit")
    args = ap.parse_args()

    bands = BANDS
    if args.only:
        bands = [b for b in BANDS if b["name"] in args.only]
        missing = set(args.only) - {b["name"] for b in bands}
        if missing:
            ap.error(f"unknown band(s): {', '.join(sorted(missing))}")

    if args.antenna:
        bands = [b for b in bands if b["ant"] == args.antenna]
        if not bands:
            ap.error(f"no bands match antenna '{args.antenna}'")

    if args.list:
        print(f"{'name':<10} {'freq MHz':>10} {'gain':>5} {'dwell':>6} "
              f"{'ant':<5}  expect")
        for b in BANDS:
            print(f"{b['name']:<10} {b['freq']/1e6:>10.3f} {b['gain']:>5.0f} "
                  f"{b['dur']:>5.1f}s {b['ant']:<5}  {b['expect']}")
        return

    total_s = sum(args.duration or b["dur"] for b in bands)
    mb = total_s * FS * 8 / 1e6         # complex64 = 8 bytes/sample
    pass_note = f", {args.antenna} antenna" if args.antenna else ""
    print(f"{len(bands)} bands, {total_s:.0f}s of IQ, "
          f"about {mb:.0f} MB on disk{pass_note}")
    print(f"writing to {OUT_DIR}\n")

    device = open_device()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for b in bands:
        dur = args.duration or b["dur"]
        print(f"[{b['name']:<9}] {b['freq']/1e6:>9.3f} MHz  {dur:>5.1f}s  "
              f"{b['ant']:<5} ", end="", flush=True)

        t0 = time.time()
        try:
            iq, stats = capture(device, b["freq"], b["gain"], dur)
        except RuntimeError as e:
            print(f"FAILED: {e}")
            continue

        # peak-minus-mean: a rough read on whether there is on/off structure.
        # under ~3 dB and detect_bursts() takes its continuous fallback.
        mean_db = 10 * np.log10(np.mean(np.abs(iq) ** 2) + 1e-30)
        peak_db = 10 * np.log10(np.percentile(np.abs(iq) ** 2, 99.9) + 1e-30)

        base = OUT_DIR / f"{b['name']}_{stamp}"
        np.save(base.with_suffix(".npy"), iq)
        base.with_suffix(".json").write_text(json.dumps(dict(
            name=b["name"], centre_hz=b["freq"], fs_hz=FS, gain_db=b["gain"],
            agc=False, antenna=b["ant"], duration_s=dur, n_samples=len(iq), dtype="complex64",
            expect=b["expect"], expected_mod=b["mod"], note=b["note"],
            captured_at=datetime.now().isoformat(timespec="seconds"),
            mean_power_db=round(float(mean_db), 1),
            peak_power_db=round(float(peak_db), 1),
            **stats,
        ), indent=2))

        flags = []
        if stats["overflows"]:
            flags.append(f"{stats['overflows']} overflow")
        if stats["timeouts"]:
            flags.append(f"{stats['timeouts']} timeout")
        print(f"{len(iq):>9} samples  peak-mean {peak_db - mean_db:>5.1f} dB  "
              f"{time.time() - t0:>4.1f}s  {', '.join(flags)}")

    print(f"\nwritten to {OUT_DIR}")


if __name__ == "__main__":
    main()