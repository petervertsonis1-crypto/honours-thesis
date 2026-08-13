from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

import argparse
import importlib.util

import adsb

def load_detector_class():
    """Load the uploaded module despite the '(1)' in its filename."""
    module_path = Path(__file__).with_name("adsb.py")
    spec = importlib.util.spec_from_file_location("adsb", module_path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ADSBPreambleDetector


def verify_templates(detector):
    templates = detector.phase_templates

    assert templates.shape == (5, 21)
    assert np.all(np.isin(templates, (0.0, 1.0)))

    # For phase 0.4, the first four ADC samples occur at
    # -0.167, 0.250, 0.667 and 1.083 us relative to the preamble.
    np.testing.assert_array_equal(
        templates[2, :4],
        np.array([0.0, 1.0, 0.0, 1.0]),
    )


def print_templates(detector):
    print(f"sample rate: {detector.fs / 1e6:g} MS/s")
    print(f"template length: {detector.phase_templates.shape[1]} samples")

    for phase, template in zip(
        detector.TIMING_PHASES,
        detector.phase_templates,
    ):
        samples = "".join(str(value) for value in template.astype(int))
        high_indices = np.flatnonzero(template).tolist()
        print(
            f"phase {phase:.1f}: {samples}  "
            f"high indices={high_indices}"
        )

    unique_templates = np.unique(detector.phase_templates, axis=0)
    print(
        f"\n{len(unique_templates)} distinct binary patterns "
        f"from {len(detector.TIMING_PHASES)} phase hypotheses."
    )

    if len(unique_templates) < len(detector.TIMING_PHASES):
        print(
            "Some phases are indistinguishable with ideal point sampling; "
            "this is expected and motivates pulse-shape modelling."
        )


def plot_templates(detector):
    import matplotlib.pyplot as plt

    sample_indices = np.arange(detector.phase_templates.shape[1])
    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(10, 7))

    for axis, phase, template in zip(
        axes,
        detector.TIMING_PHASES,
        detector.phase_templates,
    ):
        axis.step(sample_indices, template, where="mid")
        axis.set_ylim(-0.15, 1.15)
        axis.set_ylabel(f"{phase:.1f}")
        axis.grid(alpha=0.25)

    axes[0].set_title("Ideal ADS-B preamble templates by timing phase")
    axes[-1].set_xlabel("ADC sample index relative to integer candidate start")
    fig.supylabel("Phase (samples) / expected level")
    fig.tight_layout()
    plt.show()

def sigmoid(x):
    """
    Smooth transition from 0 to 1.
    """
    x = np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-x))


def shaped_pulse(
    t_us,
    start_us,
    end_us,
    edge_width_us,
):
    rising = sigmoid(
        (t_us - start_us) / edge_width_us
    )

    falling = sigmoid(
        (t_us - end_us) / edge_width_us
    )

    return rising - falling

def shaped_preamble_envelope(
    detector,
    t_us,
    edge_width_us=0.06,
):
    """
    Evaluate a smoothly shaped ADS-B preamble at the requested times.

    Returns amplitude values between 0 and 1.
    """
    t_us = np.asarray(t_us, dtype=np.float64)
    envelope = np.zeros_like(t_us)

    for pulse_start, pulse_end in detector.PREAMBLE_PULSES_US:
        rising_edge = sigmoid(
            (t_us - pulse_start) / edge_width_us
        )

        falling_edge = sigmoid(
            (t_us - pulse_end) / edge_width_us
        )

        envelope += rising_edge - falling_edge

    return np.clip(envelope, 0.0, 1.0)

def shaped_adsb_packet_envelope(
    detector,
    t_us,
    bits,
    edge_width_us=0.06,
):
    t_us = np.asarray(t_us, dtype=np.float64)
    envelope = np.zeros_like(t_us)

    # Four ADS-B preamble pulses.
    for pulse_start, pulse_end in detector.PREAMBLE_PULSES_US:
        envelope += shaped_pulse(
            t_us,
            pulse_start,
            pulse_end,
            edge_width_us,
        )

    # The data field begins after the 8 us preamble.
    for bit_index, bit in enumerate(bits):
        bit_start = 8.0 + bit_index

        if bit == 1:
            pulse_start = bit_start
        else:
            pulse_start = bit_start + 0.5

        envelope += shaped_pulse(
            t_us,
            pulse_start,
            pulse_start + 0.5,
            edge_width_us,
        )

    return np.clip(envelope, 0.0, 1.0)

def simulate_received_packet(
    detector,
    message,
    actual_phase,
    signal_power=9.0,
    noise_power=1.0,
    edge_width_us=0.06,
    rng=None,
):
    if rng is None:
        rng = np.random.default_rng()

    bits = np.unpackbits(
        np.frombuffer(message, dtype=np.uint8),
        bitorder="big",
    )

    # 130 us gives us some spare samples beyond the packet.
    sample_count = int(np.ceil(
        130e-6 * detector.fs
    ))

    sample_indices = np.arange(
        sample_count,
        dtype=np.float64,
    )

    samples_per_us = detector.fs / 1e6

    relative_times_us = (
        sample_indices - actual_phase
    ) / samples_per_us

    clean_envelope = shaped_adsb_packet_envelope(
        detector=detector,
        t_us=relative_times_us,
        bits=bits,
        edge_width_us=edge_width_us,
    )

    carrier_phase = rng.uniform(
        0.0,
        2.0 * np.pi,
    )

    clean_iq = (
        np.sqrt(signal_power)
        * clean_envelope
        * np.exp(1j * carrier_phase)
    )

    noise_std = np.sqrt(noise_power / 2.0)

    noise_iq = noise_std * (
        rng.standard_normal(sample_count)
        + 1j * rng.standard_normal(sample_count)
    )

    received_iq = clean_iq + noise_iq
    received_power = np.abs(received_iq) ** 2

    return received_power

def verify_phase_scoring(detector):
    """
    Check that noisy synthetic preambles recover their known phase.
    """
    rng = np.random.default_rng(3405)

    baseline_power = 2.0
    pulse_amplitude = 3.0
    noise_std = 0.15

    for expected_phase, known_template in zip(
        detector.TIMING_PHASES,
        detector.phase_templates,
    ):
        noise = rng.normal(
            loc=0.0,
            scale=noise_std,
            size=known_template.shape,
        )

        window = (
            baseline_power
            + pulse_amplitude * known_template
            + noise
        )

        best_phase, best_score, scores = (
            detector.score_phase_window(window)
        )

        assert best_phase == expected_phase
        assert best_score == np.max(scores)

def demonstrate_phase_scoring(detector):
    """
    Print one known-phase example for inspection.
    """
    rng = np.random.default_rng(1090)

    expected_phase = 0.8

    phase_index = int(np.flatnonzero(
        detector.TIMING_PHASES == expected_phase
    )[0])

    known_template = detector.phase_templates[phase_index]

    baseline_power = 2.0
    pulse_amplitude = 3.0
    noise_std = 0.15

    noise = rng.normal(
        loc=0.0,
        scale=noise_std,
        size=known_template.shape,
    )

    window = (
        baseline_power
        + pulse_amplitude * known_template
        + noise
    )

    best_phase, best_score, scores = (
        detector.score_phase_window(window)
    )

    print("\nSynthetic phase-estimation example")
    print(f"known phase: {expected_phase:.1f}")

    for phase, score in zip(
        detector.TIMING_PHASES,
        scores,
    ):
        marker = "  <-- best" if phase == best_phase else ""

        print(
            f"phase {phase:.1f}: "
            f"score={score:.4f}{marker}"
        )

    print(
        f"estimated phase: {best_phase:.1f} "
        f"(score={best_score:.4f})"
    )

def simulate_received_preamble(
    detector,
    actual_phase,
    signal_power=9.0,
    noise_power=1.0,
    edge_width_us=0.06,
    rng=None,
):
    """
    Simulate one noisy ADS-B preamble reception.

    actual_phase is measured as a fraction of one ADC sample.
    """
    if rng is None:
        rng = np.random.default_rng()

    if not 0.0 <= actual_phase < 1.0:
        raise ValueError(
            "actual_phase must satisfy 0.0 <= phase < 1.0"
        )

    template_length = detector.phase_templates.shape[1]
    samples_per_us = detector.fs / 1e6

    sample_indices = np.arange(
        template_length,
        dtype=np.float64,
    )

    # Times at which the ADC samples the waveform, measured
    # relative to the true beginning of the preamble.
    relative_times_us = (
        sample_indices - actual_phase
    ) / samples_per_us

    # Sample the smoothly shaped preamble at those ADC times.
    clean_envelope = shaped_preamble_envelope(
        detector,
        relative_times_us,
        edge_width_us=edge_width_us,
    )

    # Give the baseband signal an arbitrary angle in the I/Q plane.
    carrier_phase = rng.uniform(0.0, 2.0 * np.pi)

    # Convert desired signal power into complex I/Q amplitude.
    clean_iq = (
        np.sqrt(signal_power)
        * clean_envelope
        * np.exp(1j * carrier_phase)
    )

    # Divide the total noise power equally between I and Q.
    noise_std = np.sqrt(noise_power / 2.0)

    noise_iq = noise_std * (
        rng.standard_normal(template_length)
        + 1j * rng.standard_normal(template_length)
    )

    # The SDR observes signal plus noise.
    received_iq = clean_iq + noise_iq

    # This matches iq.real**2 + iq.imag**2 in the real receiver.
    received_power = np.abs(received_iq) ** 2

    return received_power, clean_envelope

def demonstrate_realistic_off_grid_phase(
    detector,
    actual_phase,
    signal_power,
    noise_power,
    rng,
    plot=False,
):
    received_power, clean_envelope = simulate_received_preamble(
        detector=detector,
        actual_phase=actual_phase,
        signal_power=signal_power,
        noise_power=noise_power,
        edge_width_us=0.06,
        rng=rng,
    )

    estimated_phase, best_score, scores = (
        detector.score_phase_window(received_power)
    )

    print("\nRealistic noisy phase-estimation example")
    print(f"actual phase:    {actual_phase:.4f}")
    print(f"signal power:    {signal_power}")
    print(f"noise power:     {noise_power}")

    print(
        "clean envelope: ",
        np.array2string(
            clean_envelope,
            precision=3,
            suppress_small=True,
        ),
    )

    print(
        "received power: ",
        np.array2string(
            received_power,
            precision=3,
            suppress_small=True,
        ),
    )

    for tested_phase, score in zip(
        detector.TIMING_PHASES,
        scores,
        strict=True,
    ):
        marker = (
            "  <-- selected"
            if tested_phase == estimated_phase
            else ""
        )

        print(
            f"tested phase {tested_phase:.1f}: "
            f"score={score:.4f}{marker}"
        )

    print(f"estimated phase: {estimated_phase:.1f}")
    print(f"best score:      {best_score:.4f}")
    print(
        f"phase error:     "
        f"{estimated_phase - actual_phase:+.4f} samples"
    )

    if plot:
        plot_received_preamble(
            detector=detector,
            received_power=received_power,
            clean_envelope=clean_envelope,
            signal_power=signal_power,
            actual_phase=actual_phase,
            estimated_phase=estimated_phase,
            scores=scores,
        )

def plot_received_preamble(
    detector,
    received_power,
    clean_envelope,
    signal_power,
    actual_phase,
    estimated_phase,
    scores,
):
    sample_indices = np.arange(len(received_power))

    # The envelope represents amplitude, so square it for power.
    clean_power = signal_power * clean_envelope**2

    fig, (ax_power, ax_scores) = plt.subplots(
        2,
        1,
        figsize=(10, 7),
        constrained_layout=True,
    )

    # Received and ideal power samples
    ax_power.stem(
        sample_indices,
        received_power,
        linefmt="C0-",
        markerfmt="C0o",
        basefmt=" ",
        label="Received noisy power",
    )

    ax_power.plot(
        sample_indices,
        clean_power,
        "C1o--",
        linewidth=2,
        label="Expected clean power",
    )

    ax_power.set_title(
        f"ADS-B preamble reception: "
        f"actual phase={actual_phase:.4f}, "
        f"estimated phase={estimated_phase:.1f}"
    )
    ax_power.set_xlabel("Sample index")
    ax_power.set_ylabel("Power")
    ax_power.set_xticks(sample_indices)
    ax_power.grid(alpha=0.25)
    ax_power.legend()

    # Phase-template scores
    ax_scores.bar(
        detector.TIMING_PHASES,
        scores,
        width=0.12,
        color="C2",
        edgecolor="black",
    )

    ax_scores.axvline(
        actual_phase,
        color="C1",
        linestyle="--",
        label=f"Actual phase: {actual_phase:.4f}",
    )

    ax_scores.axvline(
        estimated_phase,
        color="C3",
        linestyle=":",
        linewidth=2,
        label=f"Selected phase: {estimated_phase:.1f}",
    )

    ax_scores.set_xlabel("Phase hypothesis (samples)")
    ax_scores.set_ylabel("Normalized correlation")
    ax_scores.set_xticks(detector.TIMING_PHASES)
    ax_scores.set_ylim(0.0, 1.05)
    ax_scores.grid(axis="y", alpha=0.25)
    ax_scores.legend()

    plt.show()

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

def verify_known_adsb_crc():
    message = bytes.fromhex(
        "8D40621D58C382D690C8AC2863A7"
    )

    assert len(message) == 14
    assert message[0] >> 3 == 17
    assert mode_s_crc(message) == 0

    print("Known DF17 CRC check passed.")

def verify_synthetic_packet_decoding(detector):
    expected_message = bytes.fromhex(
        "8D40621D58C382D690C8AC2863A7"
    )

    actual_phase = 0.532
    rng = np.random.default_rng(1090)

    received_power = simulate_received_packet(
        detector=detector,
        message=expected_message,
        actual_phase=actual_phase,
        signal_power=9.0,
        noise_power=1,
        rng=rng,
    )

    estimated_phase, preamble_score, _ = (
        detector.score_phase_window(
            received_power[
                :detector.phase_templates.shape[1]
            ]
        )
    )

    decoder = adsb.ADSBPacketDecoder(detector.fs)

    packet = decoder.decode(
        power=received_power,
        preamble_index=0,
        phase=estimated_phase,
    )

    print("\nSynthetic complete-packet test")
    print(f"actual phase:       {actual_phase:.4f}")
    print(f"estimated phase:    {estimated_phase:.1f}")
    print(f"preamble score:     {preamble_score:.4f}")
    print(f"expected message:   {expected_message.hex().upper()}")
    print(f"decoded message:    {packet.hex}")
    print(f"downlink format:    DF{packet.downlink_format}")
    print(f"CRC remainder:      0x{packet.crc_remainder:06X}")
    print(f"CRC valid:          {packet.crc_ok}")
    print(
        f"weakest bit:        "
        f"{np.min(packet.bit_confidence):.4f}"
    )

    expected_bits = np.unpackbits(
        np.frombuffer(expected_message, dtype=np.uint8),
        bitorder="big",
    )
    
    wrong_bits = np.flatnonzero(
        packet.bits != expected_bits
    )
    
    different_bytes = sum(
        actual != expected
        for actual, expected in zip(
            packet.raw,
            expected_message,
            strict=True,
        )
    )
    
    print(f"different bytes:    {different_bytes}")
    print(f"bit errors:         {len(wrong_bits)}")
    print(f"wrong bit indices:  {wrong_bits.tolist()}")
    print(
        "their confidence:  ",
        packet.bit_confidence[wrong_bits],
    )

    print(f"different bytes:    {different_bytes}")

    assert packet.raw == expected_message
    assert packet.downlink_format == 17
    assert packet.crc_ok

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Display the five phase templates with Matplotlib",
    )
    args = parser.parse_args()

    detector_class = load_detector_class()
    detector = detector_class(fs=2.4e6)

    verify_templates(detector)
    print("Template checks passed.\n")

    print_templates(detector)

    verify_synthetic_packet_decoding(detector)

if __name__ == "__main__":
    main()