'''
Gets array of complex IQ samples via SoapySDR.

TODO: 
- Right now includes ADSB packet info / plotting - remove soon, should only return IQ.
- Interface with future `source` class
'''

import numpy as np
import SoapySDR
import matplotlib.pyplot as plt

from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
from adsb.adsb import ADSBReceiver

FS = 2.4e6
FC = 1090e6
NUM_SAMPLES = 262144

devices = SoapySDR.Device.enumerate()

if not devices:
    raise RuntimeError("No SDR devices found.")

device = SoapySDR.Device(devices[0])
receiver = ADSBReceiver(FS)

device.setSampleRate(SOAPY_SDR_RX, 0, FS)
device.setFrequency(SOAPY_SDR_RX, 0, FC)
device.setGainMode(SOAPY_SDR_RX, 0, True)

stream = device.setupStream(
    SOAPY_SDR_RX,
    SOAPY_SDR_CF32,
    [0],
)

samples = np.empty(NUM_SAMPLES, dtype=np.complex64)

device.activateStream(stream)

num_received = 0

while num_received < NUM_SAMPLES:
    '''
    `device.readStream()` doesn't always return `NUM_SAMPLES` samples.
    This loop is an attempt to make sure it does. 
    '''
    result = device.readStream(
        stream,
        [samples[num_received:]],
        NUM_SAMPLES - num_received,
    )

    if result.ret < 0:
        raise RuntimeError(
            f"SoapySDR readStream failed with code {result.ret}"
        )

    print(
        f"requested={NUM_SAMPLES - num_received}, "
        f"received={result.ret}"
    )

    num_received += result.ret

print("\n------------CAPTURE INFO------------")
print(f"total received: {num_received}")
print(result)
print(samples.dtype)
print(samples.shape)
print(samples[:10])
print("------------------------------------\n")

candidate = receiver.process(samples)

if candidate is None:
    print("No ADS-B candidate detected.")
else:
    print("ADS-B candidate detected")
    np.save("captures/adsb_candidate.npy", samples)
    print(f"score:          {candidate.score:.6f}")
    print(f"median score:   {candidate.median_score:.6f}")
    print(f"relative score: {candidate.relative_score:.2f}")

    time_us = (
        np.arange(len(candidate.power))
        / FS
        * 1e6
    )

    # Whole packet plot.
    plt.plot(time_us, candidate.power)
    plt.xlabel("Time (µs)")
    plt.ylabel("Power")
    plt.title("Detected ADS-B candidate")
    plt.show()

    # Preamble - shows discrete samples.
    n = int(12e-6 * FS)

    plt.stem(
        time_us[:n],
        candidate.power[:n],
    )

    plt.xlabel("Time (µs)")
    plt.ylabel("Power")
    plt.title("Candidate preamble")
    plt.grid()
    plt.show()

device.deactivateStream(stream)
device.closeStream(stream)

