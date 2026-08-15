import numpy as np
import SoapySDR

from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32

from adsb.adsb import ADSBReceiver


FS = 2.4e6
FC = 1090e6

BUFFER_SAMPLES = 131072

OVERLAP_SAMPLES = int(
    np.ceil(130e-6 * FS)
)

tail = np.empty(
    0,
    dtype=np.complex64,
)

devices = SoapySDR.Device.enumerate()

if not devices:
    raise RuntimeError("No SDR devices found.")

device = SoapySDR.Device(devices[0])

device.setSampleRate(SOAPY_SDR_RX, 0, FS)
device.setFrequency(SOAPY_SDR_RX, 0, FC)
device.setGainMode(SOAPY_SDR_RX, 0, True)

stream = device.setupStream(
    SOAPY_SDR_RX,
    SOAPY_SDR_CF32,
    [0],
)

receiver = ADSBReceiver(FS)

samples = np.empty(
    BUFFER_SAMPLES,
    dtype=np.complex64,
)

try:
    device.activateStream(stream)

    while True:
        result = device.readStream(
            stream,
            [samples],
            BUFFER_SAMPLES,
            timeoutUs=1_000_000,
        )

        if result.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
            print("readStream timeout")
            continue

        if result.ret < 0:
            raise RuntimeError(
                f"readStream failed with code {result.ret}"
            )

        new_samples = samples[:result.ret]

        old_tail_len = len(tail)

        iq = np.concatenate([
            tail,
            new_samples,
        ])

        detections = receiver.process(iq)

        tail = iq[-OVERLAP_SAMPLES:].copy()

        for detection in detections:

            packet = detection.packet

            packet_duration_samples = int(
                np.ceil(
                    (8 + len(packet.bits))
                    * 1e-6
                    * FS
                )
            )

            packet_end = (
                detection.preamble_index
                + packet_duration_samples
            )

            # Skip packets that were completely contained
            # in the previous block's overlap.
            if packet_end <= old_tail_len:
                continue

            print()
            print("Mode-S packet detected")
            print(f"  DF:           DF{packet.downlink_format}")
            print(f"  Message:      {packet.hex}")
            print(f"  CRC valid:    {packet.crc_ok}")
            print(
                f"  Correlation:  "
                f"{detection.timing_correlation:.3f}"
            )

            if detection.message is not None:
                print()
                print(detection.message)

except KeyboardInterrupt:
    print("\nStopping receiver...")

finally:
    device.deactivateStream(stream)
    device.closeStream(stream)