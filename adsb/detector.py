import numpy as np
from dataclasses import dataclass

@dataclass
class ADSBCandidate:
    power: np.ndarray
    score: float
    median_score: float
    relative_score: float

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

    def find_coarse(
        self,
        power: np.ndarray,
    ) -> tuple[int | None, float]:
        scores = self.score(power)
    
        if len(scores) == 0:
            return None, float("-inf")
    
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
    
        return best_index, best_score

    def find_candidates(
        self,
        power: np.ndarray,
        threshold: float | None = None,
    ) -> list[tuple[int, float]]:
        scores = self.score(power)

        if len(scores) < 3:
            return []

        # Local maxima only.
        peak_mask = (
            (scores[1:-1] > scores[:-2])
            & (scores[1:-1] >= scores[2:])
        )

        peak_indices = np.flatnonzero(peak_mask) + 1

        if threshold is None:
            median = float(np.median(scores))
            mad = float(
                np.median(
                    np.abs(scores - median)
                )
            )

            threshold = median + 20.0 * mad

        candidates = [
            (int(index), float(scores[index]))
            for index in peak_indices
            if scores[index] > threshold
        ]

        return candidates

    def refine_timing(
        self,
        power: np.ndarray,
        coarse_index: int,
        search_radius: int = 2,
    ) -> tuple[int, float, float]:

        template_length = self.phase_templates.shape[1]

        best_index = None
        best_phase = None
        best_score = float("-inf")

        for index in range(
            coarse_index - search_radius,
            coarse_index + search_radius + 1,
        ):
            if index < 0:
                continue

            if index + template_length > len(power):
                continue

            window = power[
                index:index + template_length
            ]

            phase, score, _ = self.score_phase_window(
                window
            )

            # print(
            #     f"index={index}, "
            #     f"phase={phase:.1f}, "
            #     f"timing={index + phase:.1f}, "
            #     f"score={score:.4f}"
            # )

            if score > best_score:
                best_index = index
                best_phase = phase
                best_score = score

        return best_index, best_phase, best_score