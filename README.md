# RF Protocol Identification

Honours thesis project investigating the detection and identification of wireless protocols from raw IQ samples, with particular focus on preamble detection and automated protocol analysis.

## Setup

System dependencies (macOS):

```
brew install soapysdr soapyrtlsdr
```

Python environment:
```
python3.14 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To run:
```
python -m sources.soapy_capture
```