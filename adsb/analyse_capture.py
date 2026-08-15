import numpy as np

from adsb.adsb import ADSBPreambleDetector

FS = 2.4e6

samples = np.load("captures/adsb_candidate_006_lm.npy")
power = np.abs(samples) ** 2

detector = ADSBPreambleDetector(FS)

coarse_index, coarse_score = detector.find_coarse(power)

index, phase, correlation = detector.refine_timing(
    power,
    coarse_index,
)

true_start = index + phase

print(f"coarse index:        {coarse_index}")
print(f"coarse score:        {coarse_score:.6f}")
print(f"refined index:       {index}")
print(f"estimated phase:     {phase:.1f}")
print(f"true start:          {true_start:.1f}")
print(f"correlation:         {correlation:.4f}")

if index is not None:
    time_ms = index / FS * 1e3
    print(f"candidate time:      {time_ms:.3f} ms")

template_length = detector.phase_templates.shape[1]

window = power[
    index:index + template_length
]

phase, phase_score, phase_scores = (
    detector.score_phase_window(window)
)

print(f"estimated phase:      {phase:.1f}")
print(f"phase score:          {phase_score:.4f}")

for tested_phase, score in zip(
    detector.TIMING_PHASES,
    phase_scores,
):
    print(f"    phase {tested_phase:.1f}: {score:.4f}")