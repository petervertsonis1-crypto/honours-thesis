#!/usr/bin/env python3
"""
noise_baseline.py  --  what does the classifier say when there is no signal?

Motivation
----------
The wifi_ht20_snr-15 run returned a CONFIDENT match (score 0.87) on
"Wi-Fi 802.11b/g (DSSS/CCK)" from a capture whose envelope statistics were
indistinguishable from complex Gaussian noise (CV 0.523, PAPR 10.9 dB,
flatness 0.99).

Hypothesis: pure noise has a *preferred wrong answer*, and the DSSS entry is
it, because that entry (a) has the lowest symbol-rate window in the database,
(b) accepts three modclasses so the modulation gate never penalises it, and
(c) has a bandwidth window wide enough to swallow "signal fills the capture".

This script measures the false-positive distribution instead of arguing
about it.

Two-stage on purpose: stage 1 writes .npy captures in the same layout your
sweep tool already reads, stage 2 parses the verbose text it prints. Nothing
here imports Philip's code, so there is no chance of calling identify()
differently from how run_sweep_id.py calls it.

Usage
-----
Run everything from the thesis root (~/Desktop/thesis).

  # 1. smoke test: one file, eyeball it
  python validation/experiments/noise_baseline.py gen --n 1
  python validation/experiments/run_sweep_id.py --dir noise --verbose

  # 2. if that looks sane, do the real run
  python validation/experiments/noise_baseline.py gen --n 20
  python validation/experiments/run_sweep_id.py --dir noise --verbose \
      | tee noise_out.txt
  python validation/experiments/noise_baseline.py tally noise_out.txt

Captures are written to captures/noise/ by default, alongside the other
capture sets. Note that captures/ is the frozen reference set in git -- add
captures/noise/ to .gitignore unless you actually want these committed.
"""

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


# ----------------------------------------------------------------------
# stage 1: generate
# ----------------------------------------------------------------------

def make_noise(n_samples, rate_hz, bandlimit=None, rng=None):
    """
    Complex Gaussian noise, unit average power.

    bandlimit: if given, a fraction of the sample rate (0 < f <= 1.0) to
    keep. 1.0 (default) is white across the whole capture -- what an ideal
    receiver would see. Something like 0.8 mimics the RTL-SDR decimation
    filter rolling off before the band edge.

    The bandlimited variant is the one that tests whether BW99 is capped by
    the filter rather than by the noise pedestal. Run both.
    """
    rng = rng or np.random.default_rng()

    # real and imaginary parts each variance 1/2 -> |x|^2 averages to 1
    x = (rng.standard_normal(n_samples) +
         1j * rng.standard_normal(n_samples)) / np.sqrt(2.0)

    if bandlimit is not None and bandlimit < 1.0:
        X = np.fft.fftshift(np.fft.fft(x))
        keep = int(n_samples * bandlimit / 2)
        mid = n_samples // 2
        mask = np.zeros(n_samples, dtype=bool)
        mask[mid - keep: mid + keep] = True
        X[~mask] = 0
        x = np.fft.ifft(np.fft.ifftshift(X))
        # renormalise: zeroing bins removed power
        x = x / np.sqrt(np.mean(np.abs(x) ** 2))

    return x.astype(np.complex64)


def load_sidecar_template(template_path):
    """
    Copy the JSON schema from an existing capture rather than guessing at
    your key names. Point this at any file in generated/.
    """
    with open(template_path) as f:
        return json.load(f)


def cmd_gen(args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    template = {}
    if args.template:
        template = load_sidecar_template(args.template)
        print(f"merging under schema from {args.template}")

    for i in range(args.n):
        seed = args.seed + i
        rng = np.random.default_rng(seed)
        x = make_noise(args.samples, args.rate,
                       bandlimit=args.bandlimit, rng=rng)

        # Scale to the same mean power as the Wi-Fi captures (-7.2 dB). The
        # envelope statistics are dimensionless so this changes nothing about
        # CV or flatness, but if detect_bursts uses any absolute threshold
        # then matching the level keeps this a controlled comparison rather
        # than introducing a second variable.
        x = x * (10.0 ** (args.mean_power_db / 20.0))

        power = np.abs(x) ** 2
        mean_power_db = 10.0 * np.log10(power.mean())
        peak_power_db = 10.0 * np.log10(power.max())

        tag = "bl" if args.bandlimit and args.bandlimit < 1.0 else "white"
        name = f"noise_{tag}_{i:03d}"

        np.save(out_dir / f"{name}.npy", x)

        # Schema copied verbatim from captures/generated/*.json so the sweep
        # tool reads these identically to a real capture. Key names are not
        # guessable -- note centre_hz (British), fs_hz, n_samples, expect.
        meta = dict(template)
        meta.update({
            "name": name,
            "source": "synthetic_noise_baseline",
            "centre_hz": args.centre,
            "fs_hz": args.rate,
            "gain_db": None,
            "agc": None,
            "antenna": None,
            "duration_s": args.samples / args.rate,
            "n_samples": args.samples,
            "dtype": "complex64",
            # A sentinel rather than null: the sweep tool compares this
            # against the winning entry name, and a string that can never
            # match keeps that comparison from tripping over None. Every
            # capture will report "missed", which is correct -- there is no
            # right answer. Read confidence off the '*' marker instead.
            "expect": "(none - noise control)",
            "expected_mod": "(none - noise control)",
            "snr_db": "-inf",
            "note": f"synthetic complex gaussian noise, seed={seed}, "
                    f"bandlimit={args.bandlimit}",
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mean_power_db": round(float(mean_power_db), 1),
            "peak_power_db": round(float(peak_power_db), 1),
            "overflows": 0,
            "timeouts": 0,
        })
        with open(out_dir / f"{name}.json", "w") as f:
            json.dump(meta, f, indent=2)

    print(f"\nwrote {args.n} captures to {out_dir}/")
    print(f"  {args.samples} samples @ {args.rate/1e6:.1f} MS/s "
          f"({args.samples/args.rate*1e3:.2f} ms each)")
    print(f"  bandlimit: {args.bandlimit}")
    # run_sweep_id.py may resolve --dir against a captures root rather than
    # the cwd (that is how --dir generated finds captures/generated). Print
    # both forms so whichever one it wants is already to hand.
    leaf = out_dir.name
    print(f"\nnext -- try the bare name first:")
    print(f"  python validation/experiments/run_sweep_id.py "
          f"--dir {leaf} --verbose | tee noise_out.txt")
    if str(out_dir) != leaf:
        print(f"\n...and if that says the directory does not exist:")
        print(f"  python validation/experiments/run_sweep_id.py "
              f"--dir {out_dir} --verbose | tee noise_out.txt")


# ----------------------------------------------------------------------
# stage 2: parse the verbose output and tally
# ----------------------------------------------------------------------

RE_HEADER = re.compile(
    r"^(\S+)\s+--\s+([\d.]+) MHz, (\d+) samples @ ([\d.]+) MS/s")
RE_CLASS = re.compile(r"^\s+class\s+(\S+)")
RE_BW = re.compile(
    r"^\s+BW99 / RMS\s+([\d.]+) (kHz|MHz) / ([\d.]+) (kHz|MHz)")
RE_ENV = re.compile(
    r"^\s+env CV / PAPR\s+([\d.]+) / ([-\d.]+) dB\s+flatness ([\d.]+)")
RE_SYMRATE = re.compile(r"^\s+symbol rate\s+([\d.]+) (kHz|MHz)")
RE_ESTIMATOR = re.compile(r"^\s+·\s+symbol rate from (\S+)")
RE_BURST = re.compile(
    r"^\s*(\*?)\s*burst (\d+)\s+([\d.]+) ms\s+snr\s+([-\d.]+) dB"
    r"\s+cv\s+([\d.]+)\s+score ([\d.]+)\s+(.+?)\s*$")
RE_NOMATCH = re.compile(r"NO CONFIDENT MATCH")


def to_hz(value, unit):
    return float(value) * (1e3 if unit == "kHz" else 1e6)


def parse_verbose(text):
    """
    Walk the verbose output and pull one record per burst.

    Deliberately tolerant: if a field is missing the record just carries
    None for it rather than crashing, because a run that produces zero
    bursts is itself a result worth counting.
    """
    records = []
    current_band = None
    pending = {}

    for line in text.splitlines():
        m = RE_HEADER.match(line)
        if m:
            current_band = m.group(1)
            pending = {}
            continue

        m = RE_CLASS.match(line)
        if m:
            pending["modclass"] = m.group(1)
            continue

        m = RE_BW.match(line)
        if m:
            pending["bw99_hz"] = to_hz(m.group(1), m.group(2))
            pending["rms_bw_hz"] = to_hz(m.group(3), m.group(4))
            continue

        m = RE_ENV.match(line)
        if m:
            pending["env_cv"] = float(m.group(1))
            pending["papr_db"] = float(m.group(2))
            pending["flatness"] = float(m.group(3))
            continue

        m = RE_SYMRATE.match(line)
        if m:
            pending["symrate_hz"] = to_hz(m.group(1), m.group(2))
            continue

        m = RE_ESTIMATOR.match(line)
        if m:
            pending["estimator"] = m.group(1)
            continue

        if RE_NOMATCH.search(line):
            pending["no_confident_match"] = True
            continue

        m = RE_BURST.match(line)
        if m:
            rec = dict(pending)
            rec.update({
                "band": current_band,
                "confident": m.group(1) == "*",
                "burst_idx": int(m.group(2)),
                "duration_ms": float(m.group(3)),
                "snr_db": float(m.group(4)),
                "cv_reported": float(m.group(5)),
                "score": float(m.group(6)),
                "winner": m.group(7).strip(),
            })
            records.append(rec)
            pending = {}
            continue

    return records


# theoretical values for complex Gaussian noise -- the reference we compare to
RAYLEIGH_CV = np.sqrt(4.0 / np.pi - 1.0)   # 0.5227


def expected_papr_db(n):
    """Peak-to-average for complex Gaussian over n samples: ~ln(n)."""
    return 10.0 * np.log10(np.log(n))


def cmd_tally(args):
    text = Path(args.logfile).read_text()
    recs = parse_verbose(text)

    if not recs:
        print("no bursts parsed. either the pipeline found no bursts at all")
        print("(itself a finding -- note it), or the verbose format has")
        print("shifted and the regexes need updating.")
        return

    print(f"parsed {len(recs)} bursts across "
          f"{len(set(r['band'] for r in recs))} captures\n")

    # --- the headline number ---
    confident = [r for r in recs if r["confident"]]
    print(f"CONFIDENT MATCHES ON PURE NOISE: "
          f"{len(confident)}/{len(recs)} "
          f"({100.0*len(confident)/len(recs):.0f}%)")
    print()

    # --- which protocol does noise prefer? ---
    print("winner distribution (all bursts):")
    for name, count in Counter(r["winner"] for r in recs).most_common():
        share = 100.0 * count / len(recs)
        print(f"  {count:3d}  ({share:4.0f}%)  {name}")
    print()

    if confident:
        print("winner distribution (CONFIDENT only):")
        for name, count in Counter(
                r["winner"] for r in confident).most_common():
            share = 100.0 * count / len(confident)
            print(f"  {count:3d}  ({share:4.0f}%)  {name}")
        print()

    # --- the estimator switch, which is what actually drove snr-15 ---
    print("symbol-rate estimator used:")
    by_est = defaultdict(list)
    for r in recs:
        by_est[r.get("estimator", "(none)")].append(r)
    for est, group in sorted(by_est.items(),
                             key=lambda kv: -len(kv[1])):
        rates = [g["symrate_hz"] for g in group if g.get("symrate_hz")]
        conf_n = sum(1 for g in group if g["confident"])
        line = f"  {len(group):3d}  {est:<28s} {conf_n} confident"
        if rates:
            line += (f"   symrate median {np.median(rates)/1e6:.3f} MHz"
                     f"  range {min(rates)/1e6:.3f}-{max(rates)/1e6:.3f}")
        print(line)
    print()

    # --- modclass, since this is what gates everything downstream ---
    print("modclass assigned to noise:")
    for name, count in Counter(
            r.get("modclass", "?") for r in recs).most_common():
        print(f"  {count:3d}  {name}")
    print()

    # --- sanity: does the noise actually look like noise? ---
    cvs = [r["env_cv"] for r in recs if r.get("env_cv") is not None]
    paprs = [r["papr_db"] for r in recs if r.get("papr_db") is not None]
    n_samp = args.samples
    if cvs:
        print("sanity check against Rayleigh theory:")
        print(f"  env CV   measured {np.mean(cvs):.4f} "
              f"+/- {np.std(cvs):.4f}   theory {RAYLEIGH_CV:.4f}")
    if paprs:
        print(f"  PAPR dB  measured {np.mean(paprs):.2f} "
              f"+/- {np.std(paprs):.2f}     theory "
              f"{expected_papr_db(n_samp):.2f}")
    print()

    # --- bandwidth, for the DAB BW99 question ---
    bw99 = [r["bw99_hz"] for r in recs if r.get("bw99_hz")]
    if bw99:
        print("bandwidth reported for noise-only:")
        print(f"  BW99 median {np.median(bw99)/1e6:.3f} MHz "
              f"(range {min(bw99)/1e6:.3f}-{max(bw99)/1e6:.3f})")
        print(f"  as fraction of sample rate: "
              f"{np.median(bw99)/args.rate:.3f}")
        print("  -> if this is pinned near a constant fraction regardless of")
        print("     content, BW99 is capped by the filter, not the pedestal.")
    print()

    if args.csv:
        import csv
        keys = sorted({k for r in recs for k in r})
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(recs)
        print(f"per-burst records written to {args.csv}")


# ----------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="write noise captures")
    g.add_argument("--n", type=int, default=20,
                   help="how many realisations (default 20)")
    g.add_argument("--out", default="captures/noise",
                   help="output directory, relative to the thesis root "
                        "(default captures/noise/)")
    g.add_argument("--samples", type=int, default=220800,
                   help="samples per capture (default 220800, matches wifi)")
    g.add_argument("--rate", type=float, default=20e6,
                   help="sample rate Hz (default 20e6, matches wifi)")
    g.add_argument("--centre", type=float, default=2437e6,
                   help="nominal centre freq for the sidecar")
    g.add_argument("--mean-power-db", type=float, default=-7.2,
                   help="scale noise to this mean power, matching the "
                        "wifi_ht20 captures (default -7.2)")
    g.add_argument("--bandlimit", type=float, default=None,
                   help="keep this fraction of the band, e.g. 0.8. "
                        "omit for white noise across the full capture")
    g.add_argument("--seed", type=int, default=1000)
    g.add_argument("--template", default=None,
                   help="optional: an existing sidecar .json to merge under "
                        "the fields written here. Not needed -- the schema "
                        "is already matched to captures/generated/")
    g.set_defaults(func=cmd_gen)

    t = sub.add_parser("tally", help="parse run_sweep_id.py verbose output")
    t.add_argument("logfile")
    t.add_argument("--samples", type=int, default=220800,
                   help="samples per capture, for the PAPR theory line")
    t.add_argument("--rate", type=float, default=20e6)
    t.add_argument("--csv", default=None,
                   help="also dump per-burst records to CSV")
    t.set_defaults(func=cmd_tally)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()