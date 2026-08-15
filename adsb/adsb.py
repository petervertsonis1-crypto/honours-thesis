from dataclasses import dataclass

import numpy as np

from .detector import ADSBPreambleDetector
from .decoder import ADSBPacket, ADSBPacketDecoder
from .messages import decode_message

@dataclass
class ADSBDetection:
    packet: ADSBPacket
    message: object | None

    coarse_score: float
    timing_correlation: float

    preamble_index: int
    phase: float

class ADSBReceiver:
    def __init__(self, fs: float):
        self.fs = fs

        self.detector = ADSBPreambleDetector(fs)
        self.decoder = ADSBPacketDecoder(fs)

    def process(
        self,
        iq: np.ndarray,
    ) -> list[ADSBDetection]:

        power = np.abs(iq) ** 2

        coarse_candidates = (
            self.detector.find_candidates(power)    
        )

        detections = []

        for coarse_index, coarse_score in coarse_candidates:

            pulse_indices = (
                coarse_index
                + self.detector.pulse_offsets
            )

            gap_indices = (
                coarse_index
                + self.detector.gap_offsets
            )

            pulse_values = power[pulse_indices]
            gap_values = power[gap_indices]

            gap_level = float(
                np.mean(gap_values)
            )

            if not np.all(
                pulse_values > 4.0 * gap_level
            ):
                continue

            index, phase, correlation = (
                self.detector.refine_timing(
                    power,
                    coarse_index,
                )
            )

            try:
                packet = self.decoder.decode(
                    power,
                    preamble_index=index,
                    phase=phase,
                )

                message = None
            
                if packet.downlink_format == 17:
                    if packet.crc_ok:
                        message = decode_message(packet)
    
                elif packet.downlink_format == 0:
                    message = decode_message(packet)
    
                detections.append(
                    ADSBDetection(
                        packet=packet,
                        message=message,
                        coarse_score=coarse_score,
                        timing_correlation=correlation,
                        preamble_index=index,
                        phase=phase,
                    )
                )

            except ValueError:
                continue

        return detections