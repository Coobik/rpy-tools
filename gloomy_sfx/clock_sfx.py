"""
Quartz Wall Clock Audio Synthesizer
Generates realistic mechanical ticking sounds using physical modeling synthesis.
"""

import argparse
import sys
import wave
import numpy as np


def synthesize_tick(
    sample_rate: int = 44100,
    volume: float = 0.8,
    resonance_freq: float = 1800.0,
    body_freq: float = 420.0,
    decay_rate: float = 140.0,
    transient_snap: float = 3600.0,
    rebound_delay: float = 0.022,
    rebound_gain: float = 0.35,
    noise_mix: float = 0.25,
    is_tock: bool = False,
) -> np.ndarray:
    """
    Synthesize an individual mechanical quartz movement event.
    Models the stepper motor snap, gear tooth impact, housing resonance,
    and mechanical backlash rebound.
    """

    # Subtle acoustic shift for alternating tick vs tock
    if is_tock:
        resonance_freq *= 0.94
        body_freq *= 0.96
        volume *= 0.92

    duration = 0.08  # 80 ms event window
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # 1. Primary rotor impulse (high-frequency transient snap)
    transient = np.sin(2 * np.pi * transient_snap * t) * np.exp(-450 * t)

    # 2. Clock casing resonance (exponentially decaying sine wave)
    case_resonance = np.sin(2 * np.pi * resonance_freq * t) * np.exp(-decay_rate * t)

    # 3. Wall coupling / hollow cavity low-frequency thump
    wall_thump = np.sin(2 * np.pi * body_freq * t) * np.exp(-90 * t) * 0.45

    # 4. Mechanical friction / burst noise
    noise = np.random.uniform(-1, 1, len(t)) * np.exp(-380 * t) * noise_mix

    primary = transient + case_resonance + wall_thump + noise

    # 5. Gear rebound / backlash (micro-click shortly after the main strike)
    delay_samples = int(sample_rate * rebound_delay)
    rebound = np.zeros_like(t)

    if delay_samples < len(t):
        t_sub = t[:-delay_samples]

        rebound_impulse = (
            np.sin(2 * np.pi * (resonance_freq * 1.12) * t_sub)
            * np.exp(-decay_rate * 1.2 * t_sub)
            * rebound_gain
            + np.sin(2 * np.pi * (transient_snap * 1.1) * t_sub)
            * np.exp(-500 * t_sub)
            * (rebound_gain * 0.7)
        )

        rebound[delay_samples:] = rebound_impulse

    sound_event = primary + rebound

    # Normalize peak and scale by volume
    peak = np.max(np.abs(sound_event))

    if peak > 0:
        sound_event = (sound_event / peak) * volume

    return sound_event


def generate_clock_track(
    output_path: str = "quartz_clock_tick.wav",
    ticks: int = 10,
    volume: float = 0.8,
    resonance_freq: float = 1800.0,
    body_freq: float = 420.0,
    decay_rate: float = 140.0,
    rebound: bool = True,
    tick_tock: bool = True,
    sample_rate: int = 44100,
):
    """Generate a multi-second audio track with ticks spaced every 1.0 second."""
    total_samples = int(sample_rate * ticks)
    track = np.zeros(total_samples, dtype=np.float32)

    for i in range(ticks):
        is_tock = tick_tock and (i % 2 == 1)

        tick_audio = synthesize_tick(
            sample_rate=sample_rate,
            volume=volume,
            resonance_freq=resonance_freq,
            body_freq=body_freq,
            decay_rate=decay_rate,
            rebound_delay=0.022 if rebound else 0.0,
            rebound_gain=0.35 if rebound else 0.0,
            is_tock=is_tock,
        )

        start = int(i * sample_rate)
        end = min(start + len(tick_audio), total_samples)
        track[start:end] += tick_audio[: end - start]

    # Clip to standard dynamic range and convert to 16-bit PCM
    track = np.clip(track, -1.0, 1.0)
    int_samples = (track * 32767).astype(np.int16)

    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int_samples.tobytes())

    print(f"Successfully generated {ticks} seconds of clock ticking into '{output_path}'.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Synthesize realistic quartz wall clock ticking sounds."
    )

    # Requested argument: Volume
    parser.add_argument(
        "--volume",
        "-v",
        type=float,
        default=0.8,
        help="Sound volume of the clock tick (range: 0.0 to 1.0, default: 0.8)",
    )

    # File & Duration parameters
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="quartz_clock_tick.wav",
        help="Output WAV file path (default: quartz_clock_tick.wav)",
    )

    parser.add_argument(
        "--ticks",
        "-n",
        type=int,
        default=10,
        help="Number of seconds / ticks to generate (default: 10)",
    )

    # Acoustic tuning parameters
    parser.add_argument(
        "--resonance",
        type=float,
        default=1800.0,
        help="Primary case resonance frequency in Hz (default: 1800.0; plastic=1800-2400, wood=900-1400)",
    )

    parser.add_argument(
        "--body-thump",
        type=float,
        default=420.0,
        help="Low-frequency wall coupling thump in Hz (default: 420.0)",
    )

    parser.add_argument(
        "--decay",
        type=float,
        default=140.0,
        help="Damping/decay speed of the case ring (default: 140.0; higher = drier/tighter click)",
    )

    parser.add_argument(
        "--no-rebound",
        action="store_true",
        help="Disable secondary gear rebound / backlash micro-click",
    )

    parser.add_argument(
        "--uniform",
        action="store_true",
        help="Disable subtle tick-tock alternation (makes every tick identical)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Audio sample rate in Hz (default: 44100)",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if not (0.0 <= args.volume <= 1.0):
        print("Error: --volume must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    generate_clock_track(
        output_path=args.output,
        ticks=args.ticks,
        volume=args.volume,
        resonance_freq=args.resonance,
        body_freq=args.body_thump,
        decay_rate=args.decay,
        rebound=not args.no_rebound,
        tick_tock=not args.uniform,
        sample_rate=args.sample_rate,
    )


if __name__ == "__main__":
    main()
