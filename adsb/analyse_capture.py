'''
For testing ADSB
'''

import numpy as np

from .detector import ADSBPreambleDetector
from .decoder import ADSBPacketDecoder
from .messages import decode_message

FS = 2.4e6

samples = np.load("captures/adsb_candidate_009_sm.npy")
power = np.abs(samples) ** 2

detector = ADSBPreambleDetector(FS)
decoder  = ADSBPacketDecoder(FS)

coarse_index, coarse_score = (
    detector.find_coarse(power)
)

index, phase, correlation = (
    detector.refine_timing(
        power,
        coarse_index,
    )
)

packet = decoder.decode(
    power,
    preamble_index=index,
    phase=phase,
)

message = decode_message(packet)

print(f"Downlink Format: DF{packet.downlink_format}")
print(f"Message:         {packet.hex}")
print(f"CRC valid:       {packet.crc_ok}")

print(message)