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
    MESSAGE_BITS = 112
    BIT_DURATION_US = 1.0
    HALF_BIT_DURATION_US = 0.5

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

    def decode(
        self,
        power: np.ndarray,
        preamble_index: int,
        phase: float,
    ) -> ADSBPacket:
        """
        Decode one 112-bit ADS-B packet.

        preamble_index:
            Integer sample index selected by the preamble detector.

        phase:
            Estimated fractional preamble position, such as
            0.0, 0.2, 0.4, 0.6 or 0.8 samples.
        """
        power = np.asarray(power, dtype=np.float64)

        true_preamble_start = preamble_index + phase

        data_start = (
            true_preamble_start
            + self.preamble_samples
        )

        bits = np.empty(
            self.MESSAGE_BITS,
            dtype=np.uint8,
        )

        confidence = np.empty(
            self.MESSAGE_BITS,
            dtype=np.float64,
        )

        for bit_index in range(self.MESSAGE_BITS):
            bit_start = (
                data_start
                + bit_index * self.bit_samples
            )

            middle = bit_start + self.half_bit_samples
            bit_end = bit_start + self.bit_samples

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

            # ADS-B pulse-position modulation:
            #
            # first half high  -> 1
            # second half high -> 0
            bits[bit_index] = difference > 0.0

            total_power = (
                first_half_power
                + second_half_power
            )

            confidence[bit_index] = (
                abs(difference)
                / (total_power + 1e-12)
            )

        raw = np.packbits(
            bits,
            bitorder="big",
        ).tobytes()

        downlink_format = raw[0] >> 3
        crc_remainder = mode_s_crc(raw)

        return ADSBPacket(
            raw=raw,
            bits=bits,
            bit_confidence=confidence,
            downlink_format=downlink_format,
            crc_remainder=crc_remainder,
        )

@dataclass
class ADSBCandidate:
    power: np.ndarray
    score: float
    median_score: float
    relative_score: float
    
class ADSBReceiver:
    def __init__(self, fs: float):
        self.fs = fs
        self.detector = ADSBPreambleDetector(fs)

        self.packet_samples = int(
            np.ceil(130e-6 * fs)
        )

        self.pre_samples = 2

    def process(
        self,
        iq: np.ndarray,
    ) -> ADSBCandidate | None:
        power = iq.real**2 + iq.imag**2

        scores = self.detector.score(power)

        if len(scores) == 0:
            return None

        index = int(np.argmax(scores))
        best_score = float(scores[index])
        
        pulse_indices = index + self.detector.pulse_offsets
        gap_indices = index + self.detector.gap_offsets
        
        pulse_values = power[pulse_indices]
        gap_values = power[gap_indices]
        
        gap_level = float(np.mean(gap_values))
        pulse_threshold = 4.0 * gap_level
        
        if not np.all(pulse_values > pulse_threshold):
            return None

        median_score = float(
            np.median(scores)
        )

        score_mad = float(
            np.median(
                np.abs(scores - median_score)
            )
        )

        if score_mad > 0:
            relative_score = (
                best_score - median_score
            ) / score_mad
        else:
            relative_score = 0.0

        start = index - self.pre_samples
        end = index + self.packet_samples
        
        if start < 0:
            return None
        
        if end > len(power):
            return None
        
        candidate = ADSBCandidate(
            power=power[start:end].copy(),
            score=best_score,
            median_score=median_score,
            relative_score=relative_score,
        )

        bits = self.decode_payload(
            candidate.power,
            nbits=112,
        )

        print(
            "".join(str(bit) for bit in bits[:32])
        )

        return candidate

    def decode_payload(
        self,
        candidate_power: np.ndarray,
        nbits: int = 112,
    ) -> np.ndarray:
        """
        Decode ADS-B PPM by comparing interpolated power at the
        centre of each half-bit.
        """
        preamble_start = float(self.pre_samples)
        payload_start = preamble_start + 8e-6 * self.fs
    
        samples_per_bit = self.fs * 1e-6
    
        sample_indices = np.arange(len(candidate_power))
        bits = np.empty(nbits, dtype=np.uint8)
    
        for bit_index in range(nbits):
            bit_start = (
                payload_start
                + bit_index * samples_per_bit
            )
    
            first_half_centre = (
                bit_start
                + 0.25 * samples_per_bit
            )
    
            second_half_centre = (
                bit_start
                + 0.75 * samples_per_bit
            )
    
            if second_half_centre >= len(candidate_power) - 1:
                return bits[:bit_index]
    
            first_half_power = np.interp(
                first_half_centre,
                sample_indices,
                candidate_power,
            )
    
            second_half_power = np.interp(
                second_half_centre,
                sample_indices,
                candidate_power,
            )
    
            bits[bit_index] = (
                1
                if first_half_power > second_half_power
                else 0
            )
    
        return bits
        

class ADSBPreambleDetector:
    PREAMBLE_DURATION_US = 8.0

    PREAMBLE_PULSES_US = (
        (0.0, 0.5),
        (1.0, 1.5),
        (3.5, 4.0),
        (4.5, 5.0),
    )

    # Fractional sample positions tested at 2.4 MS/s.
    TIMING_PHASES = np.arange(5, dtype=np.float64) / 5.0

    PULSE_TIMES_US = np.array([0.0, 1.0, 3.5, 4.5])

    GAP_TIMES_US = np.array([0.5, 1.5, 2.0, 2.5, 3.0, 4.0,
        5.0, 5.5, 6.0, 6.5, 7.0, 7.5])

    def __init__(self, fs: float):
        self.fs = fs

        self.phase_templates = np.stack([
            self.make_phase_template(phase)
            for phase in self.TIMING_PHASES
        ])

        self.pulse_offsets = np.round(
            self.PULSE_TIMES_US * 1e-6 * self.fs
        ).astype(int)

        self.gap_offsets = np.round(
            self.GAP_TIMES_US * 1e-6 * self.fs
        ).astype(int)

        self.preamble_samples = int(
            np.ceil(8e-6 * self.fs)
        )

    @classmethod
    def ideal_preamble(cls, t_us: np.ndarray) -> np.ndarray:
        """
        Evaluate the ideal ADS-B preamble at arbitrary times.

        `t_us` is measured in microseconds relative to the beginning
        of the preamble. A returned 1 means that instant falls inside
        one of the four ideal 0.5 us pulses; otherwise it returns 0.
        """
        t_us = np.asarray(t_us, dtype=np.float64)
        level = np.zeros_like(t_us)

        for pulse_start, pulse_end in cls.PREAMBLE_PULSES_US:
            inside_pulse = (
                (t_us >= pulse_start)
                & (t_us < pulse_end)
            )
            level[inside_pulse] = 1.0

        return level

    def make_phase_template(self, phase: float) -> np.ndarray:
        """
        Sample the ideal preamble for one fractional-start hypothesis.

        For example, phase=0.4 means the preamble is hypothesised to
        begin 0.4 sample periods after integer ADC index zero. The
        returned array predicts what the ADC samples at integer indices
        0, 1, 2, ... should observe under that hypothesis.
        """
        if not 0.0 <= phase < 1.0:
            raise ValueError("phase must satisfy 0.0 <= phase < 1.0")

        samples_per_us = self.fs / 1e6
        num_samples = (
            int(np.ceil(self.PREAMBLE_DURATION_US * samples_per_us))
            + 1
        )

        sample_indices = np.arange(num_samples, dtype=np.float64)
        relative_sample_positions = sample_indices - phase
        relative_times_us = relative_sample_positions / samples_per_us

        return self.ideal_preamble(relative_times_us)

    @staticmethod
    def normalized_score(
        window: np.ndarray,
        template: np.ndarray,
    ) -> float:
        """
        Return the normalized correlation between two arrays.
    
        Mean-centring removes sensitivity to constant background power.
        Normalization removes sensitivity to overall signal amplitude.
        """
        window = np.asarray(window, dtype=np.float64)
        template = np.asarray(template, dtype=np.float64)
    
        if window.shape != template.shape:
            raise ValueError(
                "window and template must have the same shape"
            )
    
        # Remove each array's average level
        window_centered = window - np.mean(window)
        template_centered = template - np.mean(template)
    
        denominator = (
            np.linalg.norm(window_centered)
            * np.linalg.norm(template_centered)
        )
    
        # Avoid division by zero for constant arrays
        if denominator == 0.0:
            return 0.0
    
        return float(
            np.dot(window_centered, template_centered)
            / denominator
        )

    def score_phase_window(
        self,
        window: np.ndarray,
    ) -> tuple[float, float, np.ndarray]:
        """
        Choose the timing phase that best explains one power window.
    
        Returns:
            best_phase
            best_score
            score_for_each_phase
        """
        window = np.asarray(window, dtype=np.float64)
    
        template_length = self.phase_templates.shape[1]
    
        if window.shape != (template_length,):
            raise ValueError(
                f"window must contain exactly "
                f"{template_length} samples"
            )
    
        scores = np.array([
            self.normalized_score(window, template)
            for template in self.phase_templates
        ])
    
        best_index = int(np.argmax(scores))
    
        return (
            float(self.TIMING_PHASES[best_index]),
            float(scores[best_index]),
            scores,
        )

    def score_candidate(
        self,
        power: np.ndarray,
        start: int,
    ) -> float:
        """
        Score one possible preamble beginning at `start`.

        A good candidate has:
            - high power at expected pulse positions;
            - low power at expected gap positions.
        """
        pulse_indices = start + self.pulse_offsets
        gap_indices = start + self.gap_offsets

        pulse_power = np.mean(power[pulse_indices])
        gap_power = np.mean(power[gap_indices])

        return float(pulse_power - gap_power)

    def score(self, power: np.ndarray) -> np.ndarray:
        """
        Calculate one score for every possible preamble start.
    
        This vectorised implementation is equivalent to repeatedly
        calling score_candidate(), but evaluates all start positions
        using NumPy array operations.
        """
        num_candidates = (
            len(power)
            - self.preamble_samples
            + 1
        )
    
        if num_candidates <= 0:
            return np.empty(0, dtype=np.float64)
    
        pulse_power = np.zeros(
            num_candidates,
            dtype=np.float64,
        )
    
        gap_power = np.zeros(
            num_candidates,
            dtype=np.float64,
        )
    
        for offset in self.pulse_offsets:
            pulse_power += power[
                offset:offset + num_candidates
            ]
    
        for offset in self.gap_offsets:
            gap_power += power[
                offset:offset + num_candidates
            ]
    
        pulse_power /= len(self.pulse_offsets)
        gap_power /= len(self.gap_offsets)
    
        return pulse_power - gap_power

    def find_best(
        self,
        power: np.ndarray,
    ) -> tuple[int | None, float]:
        scores = self.score(power)
    
        if len(scores) == 0:
            return None, float("-inf")
    
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
    
        return best_index, best_score