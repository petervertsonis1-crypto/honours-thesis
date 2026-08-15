from dataclasses import dataclass
import numpy as np

MODE_S_POLYNOMIAL = 0xFFF409

def mode_s_crc(message: bytes) -> int:
    """
    Calculate the 24-bit Mode S CRC remainder.

    For a valid 112-bit DF17 ADS-B message, calculating the
    remainder over all 14 bytes should produce zero.
    """
    remainder = 0

    for byte in message:
        remainder ^= byte << 16

        for _ in range(8):
            if remainder & 0x800000:
                remainder = (
                    (remainder << 1)
                    ^ MODE_S_POLYNOMIAL
                )
            else:
                remainder <<= 1

            remainder &= 0xFFFFFF

    return remainder

@dataclass
class ADSBPacket:
    raw: bytes
    bits: np.ndarray
    bit_confidence: np.ndarray
    downlink_format: int
    crc_remainder: int

    @property
    def crc_ok(self) -> bool:
        return self.crc_remainder == 0

    @property
    def hex(self) -> str:
        return self.raw.hex().upper()

class ADSBPacketDecoder:
    PREAMBLE_DURATION_US = 8.0
    BIT_DURATION_US = 1.0
    HALF_BIT_DURATION_US = 0.5

    SHORT_MESSAGE_BITS = 56
    LONG_MESSAGE_BITS = 112

    def __init__(self, fs: float):
        self.fs = fs

        self.samples_per_us = fs / 1e6

        self.preamble_samples = (
            self.PREAMBLE_DURATION_US
            * self.samples_per_us
        )

        self.bit_samples = (
            self.BIT_DURATION_US
            * self.samples_per_us
        )

        self.half_bit_samples = (
            self.HALF_BIT_DURATION_US
            * self.samples_per_us
        )

    @staticmethod
    def _integrate_sample_power(
        power: np.ndarray,
        start: float,
        end: float,
    ) -> float:
        """
        Approximate the power integral over [start, end).

        Each ADC sample at index n represents the interval:

            [n - 0.5, n + 0.5)

        Fractional boundary samples are weighted by how much of
        their interval overlaps [start, end).
        """
        if end <= start:
            raise ValueError("end must be greater than start")

        if start < -0.5 or end > len(power) - 0.5:
            raise ValueError(
                "Not enough power samples to decode this interval"
            )

        first_index = max(
            0,
            int(np.floor(start - 0.5)),
        )

        final_index = min(
            len(power) - 1,
            int(np.ceil(end + 0.5)),
        )

        integral = 0.0

        for index in range(first_index, final_index + 1):
            sample_start = index - 0.5
            sample_end = index + 0.5

            overlap_start = max(start, sample_start)
            overlap_end = min(end, sample_end)
            overlap = max(0.0, overlap_end - overlap_start)

            integral += overlap * float(power[index])

        return integral

    def _decode_bits(
        self,
        power: np.ndarray,
        preamble_index: int,
        phase: float,
        nbits: int,
        samples_per_bit: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:

        if samples_per_bit is None:
            samples_per_bit = self.bit_samples

        half_bit_samples = samples_per_bit / 2.0

        true_preamble_start = preamble_index + phase
        data_start = true_preamble_start + self.preamble_samples

        bits = np.empty(nbits, dtype=np.uint8)
        confidence = np.empty(nbits, dtype=np.float64)

        for bit_index in range(nbits):
            bit_start = (
                data_start
                + bit_index * samples_per_bit
            )

            middle = (
                bit_start
                + half_bit_samples
            )

            bit_end = (
                bit_start
                + samples_per_bit
            )

            first_half_power = self._integrate_sample_power(
                power,
                bit_start,
                middle,
            )

            second_half_power = self._integrate_sample_power(
                power,
                middle,
                bit_end,
            )

            difference = (
                first_half_power
                - second_half_power
            )

            bits[bit_index] = difference > 0.0

            total_power = (
                first_half_power
                + second_half_power
            )

            confidence[bit_index] = (
                abs(difference)
                / (total_power + 1e-12)
            )

        return bits, confidence

    def decode(
        self,
        power: np.ndarray,
        preamble_index: int,
        phase: float,
        samples_per_bit: float | None = None,
    ) -> ADSBPacket:

        power = np.asarray(
            power,
            dtype=np.float64,
        )

        # First decode only enough bits to determine
        # the Downlink Format.
        df_bits, _ = self._decode_bits(
            power=power,
            preamble_index=preamble_index,
            phase=phase,
            nbits=5,
            samples_per_bit=samples_per_bit,
        )

        downlink_format = 0

        for bit in df_bits:
            downlink_format = (
                downlink_format << 1
            ) | int(bit)

        # For the formats we're currently working with:
        #
        # DF0  -> short Mode S message
        # DF17 -> long ADS-B extended squitter
        if downlink_format == 0:
            message_bits = self.SHORT_MESSAGE_BITS

        elif downlink_format == 17:
            message_bits = self.LONG_MESSAGE_BITS

        else:
            raise ValueError(
                f"Unsupported Downlink Format: "
                f"DF{downlink_format}"
            )

        # Now decode the complete frame.
        bits, confidence = self._decode_bits(
            power=power,
            preamble_index=preamble_index,
            phase=phase,
            nbits=message_bits,
            samples_per_bit=samples_per_bit,
        )

        raw = np.packbits(
            bits,
            bitorder="big",
        ).tobytes()

        crc_remainder = mode_s_crc(raw)

        return ADSBPacket(
            raw=raw,
            bits=bits,
            bit_confidence=confidence,
            downlink_format=downlink_format,
            crc_remainder=crc_remainder,
        )