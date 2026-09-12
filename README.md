# RF Protocol Identification from Raw IQ

Honours thesis project investigating **blind wireless protocol identification from raw complex IQ samples**, with a particular focus on preamble detection, physical-layer feature extraction, and the limitations of heuristic protocol classifiers.

The project began with ADS-B preamble detection using an RTL-SDR and has expanded into systematic validation of a feature-based protocol-identification pipeline across multiple wireless standards, sample rates, SNRs, and controlled impairments.

The current research workflow is deliberately experimental:

1. generate or capture a known wireless signal;
2. pass the raw IQ through the protocol classifier;
3. inspect the extracted features and predicted protocol;
4. vary SNR, sample rate, modulation, timing, or other conditions;
5. record reproducible failure modes;
6. use those failures to inform later classifier redesign.

The objective is not simply to obtain a protocol label, but to understand **where and why the identification pipeline succeeds or fails**.

---

## Project structure

```text
honours-thesis/
├── adsb/
│   └── ADS-B preamble detection, packet extraction and decoding
│
├── sources/
│   └── SDR acquisition code, including SoapySDR capture
│
├── validation/
│   ├── gen/
│   │   └── MATLAB synthetic waveform generators
│   │
│   ├── tools/
│   │   └── data conversion / preprocessing utilities
│   │
│   └── experiments/
│       └── classifier validation and sweep runners
│
├── captures/
│   └── local raw/generated IQ datasets
│       (ignored by Git)
│
├── external/
│   └── external protocol-classifier code
│       (ignored by Git)
│
├── requirements.txt
└── README.md
```

`captures/` and `external/` are intentionally excluded from version control.

---

## Current validation pipeline

The main experimental pipeline is:

```text
MATLAB waveform generator / SDR capture
                │
                ▼
        raw complex IQ samples
          .bin + .txt
                │
                ▼
 validation/tools/synth_to_npy.py
                │
                ▼
          .npy + .json
                │
                ▼
validation/experiments/run_sweep_id.py
                │
                ▼
   feature extraction + protocol scoring
                │
                ▼
 per-burst classification / verbose report
```

Despite its legacy filename, `wifi_to_npy.py` is now used as the general converter for MATLAB-generated protocol captures.

The classifier currently used for baseline validation is Philip Leong's feature-based protocol identification code from the `phwl/doodles` repository.

The baseline classifier is intentionally being tested before major redesign so that reproducible weaknesses can be mapped first.

---

# Setup

## Python

On macOS:

```bash
brew install soapysdr soapyrtlsdr
```

Create the Python environment:

```bash
python3.14 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Activate the environment whenever returning to the project:

```bash
source .venv/bin/activate
```

---

## External classifier

The validation runner expects Philip's classifier at:

```text
external/doodles/wprotocol/preamble/iq_protocol_id.py
```

If the GitHub CLI is installed:

```bash
mkdir -p external
gh repo clone phwl/doodles external/doodles
```

`external/` is ignored by Git so the upstream classifier is not committed into this repository.

---

## MATLAB

Synthetic waveform generation uses MATLAB and, depending on the protocol, toolboxes including:

* Communications Toolbox
* WLAN Toolbox
* Bluetooth Toolbox
* 5G Toolbox
* Signal Processing Toolbox
* DSP System Toolbox

Generators live under:

```text
validation/gen/
```

Recent validation waveforms include protocols such as:

* Wi-Fi
* Bluetooth LE 1M / 2M
* Bluetooth Classic BR
* Zigbee / IEEE 802.15.4
* P25 Phase 1 C4FM
* GSM / GMSK
* 5G NR OFDM

---

# Capture storage

Generated and recorded IQ data can become large and are therefore not tracked by Git.

By default, MATLAB generators write to:

```text
captures/generated/
```

using:

```matlab
outdir = gen_outdir();
```

On the development machine this directory may instead be symlinked to an external SSD.

For example:

```bash
mkdir -p /Volumes/MySSD/honours-thesis/generated-captures
mkdir -p captures
ln -s /Volumes/MySSD/honours-thesis/generated-captures captures/generated
```

Only create the symlink if `captures/generated` does not already exist.

This allows scripts to continue using:

```text
captures/generated/
```

while the actual IQ files live on external storage.

---

# Typical research workflow

## 1. Generate synthetic captures

Run the desired MATLAB generator from `validation/gen/`.

For example:

```matlab
gen_p25
```

or:

```matlab
gen_gsm
```

or:

```matlab
gen_nr30
```

Most generators create a clean waveform together with an SNR sweep such as:

```text
clean
+30 dB
+20 dB
+15 dB
+10 dB
+5 dB
0 dB
-5 dB
-10 dB
```

The standard output format is:

```text
<name>.bin
<name>.txt
```

The `.bin` file contains interleaved float32 IQ data.

The `.txt` sidecar contains metadata such as:

```text
fs_hz
centre_hz
expect
expected_mod
snr_db
n_samples
```

Additional protocol-specific parameters may also be recorded.

Where practical, generators use fixed random seeds so experiments can be reproduced.

---

## 2. Convert generated IQ to NumPy

After running a MATLAB generator:

```bash
python validation/tools/wifi_to_npy.py
```

This converts:

```text
.bin + .txt
```

into:

```text
.npy + .json
```

for the Python validation pipeline.

The resulting files remain under:

```text
captures/generated/
```

---

## 3. Inspect a clean capture first

Before running the full SNR sweep, inspect the clean case in verbose mode.

Example:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only p25_c4fm_clean \
    --verbose
```

Another example:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only nr30_clean \
    --verbose
```

Verbose output exposes the intermediate features used by the classifier, including quantities such as:

```text
modulation family
BW99 / RMS bandwidth
burst duration
envelope CV
PAPR
spectral flatness
symbol-rate estimate
FSK tone count / deviation
OFDM CP / FFT / SCS estimate
candidate protocol scores
```

This is normally the most useful first step when a new protocol behaves unexpectedly.

---

## 4. Save verbose output

To keep a copy of an experiment while still viewing it in the terminal:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only gsm_gmsk_clean \
    --verbose \
    2>&1 | tee gsm_clean_verbose.txt
```

Likewise:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only nr30_clean \
    --verbose \
    2>&1 | tee nr30_clean_verbose.txt
```

---

## 5. Run an SNR sweep

The current pushed version of `run_sweep_id.py` treats `--only` values as exact capture names.

For example, an NR sweep can be run with:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only \
    nr30_clean \
    nr30_snr+30 \
    nr30_snr+20 \
    nr30_snr+15 \
    nr30_snr+10 \
    nr30_snr+05 \
    nr30_snr+00 \
    nr30_snr-05 \
    nr30_snr-10 \
    2>&1 | tee nr30_snr_sweep.txt
```

To run every converted capture under `captures/generated/`:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated
```

For full feature reports:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --verbose
```

---

## 6. Limit the amount of data during debugging

The experiment runner supports several useful options.

Limit the number of samples:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --max-samples 12000000
```

Limit the number of bursts inspected:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --max-bursts 12
```

Change the number of candidate protocols shown:

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --top 5
```

These are useful when performing a quick first pass before running a larger experiment.

---

# Adding a new protocol

The usual procedure when introducing a new protocol is:

### 1. Create a waveform generator

Add a generator under:

```text
validation/gen/
```

Prefer:

* a standards-based MATLAB generator where available;
* reproducible random data;
* explicit quiet intervals between bursts;
* known sample rate and RF centre frequency;
* a clean capture;
* the standard SNR sweep.

---

### 2. Write IQ and metadata

Each generated capture should produce:

```text
capture_name.bin
capture_name.txt
```

At minimum, metadata should contain:

```text
fs_hz
centre_hz
expect
expected_mod
snr_db
n_samples
```

Useful additional fields include:

```text
symbol_rate_hz
samples_per_symbol
bursts
packets
burst_s
idle_s
channel_bw_hz
```

---

### 3. Convert the capture

```bash
python validation/tools/wifi_to_npy.py
```

---

### 4. Add the expected protocol

Update the `EXPECT` mapping in:

```text
validation/experiments/run_sweep_id.py
```

For example:

```python
"p25_c4fm": "P25 Phase 1",
```

or:

```python
"nr30": "5G NR (OFDM, 30 kHz SCS)",
```

This allows the experiment runner to compare classifier output with the known generated protocol.

---

### 5. Run the clean case first

```bash
python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only <exact_clean_capture_name> \
    --verbose
```

Before adding noise, check that basic waveform properties look physically reasonable.

Useful checks include:

* burst duration;
* modulation family;
* occupied bandwidth;
* known symbol rate;
* FSK deviation or tone count;
* OFDM cyclic-prefix / SCS estimates.

---

### 6. Run the full SNR sweep

Once the clean waveform is understood, run the remaining SNR levels.

At this stage the main objective is usually to collect numbers:

* bursts detected;
* confident classifications;
* correct protocol classifications;
* incorrect confident classifications;
* approximate SNR at which segmentation fails.

Verbose analysis is only required when a genuinely new failure mode appears.

---

# Interpreting failures

A useful way to analyse classifier errors is to determine **which stage failed first**.

```text
raw IQ
  │
  ▼
burst segmentation
  │
  ▼
feature estimation
  │
  ▼
modulation classification
  │
  ▼
protocol database scoring
```

Typical failure categories include:

### Burst-detection failure

The detector fragments a packet into many small bursts or merges an entire recording into one continuous burst.

Once this happens, downstream protocol classification is generally no longer meaningful.

### Feature-estimation failure

The burst is correctly isolated but one or more measurements are wrong or unstable.

Examples include:

* occupied bandwidth;
* symbol rate;
* FSK tone count;
* frequency deviation;
* cyclic-prefix detection;
* subcarrier spacing.

### Modulation-family failure

The extracted features cause the signal to be assigned to the wrong broad modulation family.

### Protocol ambiguity

The physical-layer features are measured correctly but multiple protocol entries occupy effectively the same feature space.

In this case the limitation is structural rather than simply an estimator bug.

### Open-set failure

The classifier returns a known protocol for noise or for a waveform that is not represented in the protocol database.

---

# Important note about experiment summaries

`run_sweep_id.py` currently reports a capture as:

```text
CORRECT
```

when **at least one confident burst** matches the expected protocol.

It does **not** currently mean that all bursts were classified correctly.

For meaningful accuracy analysis, inspect the individual burst results or count the per-burst winners directly.

The final capture-level summary should therefore be treated as a quick diagnostic rather than a formal accuracy metric.

---

# ADS-B / live SDR work

The repository also contains the earlier ADS-B receiver work.

The current SoapySDR source is configured for:

```text
centre frequency: 1090 MHz
sample rate:      2.4 MS/s
```

To run the live receiver:

```bash
python -m sources.soapy_capture
```

The capture code reads complex IQ from the attached SDR, maintains overlap between blocks, runs the ADS-B detector, and prints decoded Mode-S packets when detections are found.

---

# Research philosophy

The current stage of the project is primarily **baseline characterisation**.

Rather than immediately modifying the classifier whenever a failure is observed, the current approach is to:

```text
generate controlled input
        ↓
observe failure
        ↓
reproduce it
        ↓
identify the pipeline stage responsible
        ↓
record the result
        ↓
continue testing
```

Once a sufficiently broad failure map has been collected across modulation families and operating conditions, those results can be used to motivate a more robust protocol-identification architecture.

This repository should therefore be treated as both an implementation and an evolving experimental record for the honours thesis.
