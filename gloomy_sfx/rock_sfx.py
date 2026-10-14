import argparse
from typing import Tuple
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile
from scipy.signal import butter, lfilter


def butter_bandpass(
    lowcut: float, highcut: float, fs: int, order: int = 4
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return b, a


def apply_bandpass(
    data: NDArray[np.float64],
    lowcut: float,
    highcut: float,
    fs: int,
    order: int = 3,
) -> NDArray[np.float64]:
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return lfilter(b, a, data)


def apply_distortion(
    data: NDArray[np.float64], drive: float = 5.0
) -> NDArray[np.float64]:
    return np.tanh(data * drive)


# ==========================================
# 1. CROWD SYNTHESIS (NO WHISTLES / NO PULSES)
# ==========================================
def generate_crowd(
    t: NDArray[np.float64], sample_rate: int
) -> NDArray[np.float64]:
    num_samples = len(t)
    noise = np.random.normal(0, 1, num_samples)

    # Broadband low/mid crowd roar (capped at 1200Hz to eliminate whistling)
    base_roar = apply_bandpass(noise, 100, 1200, sample_rate, order=3)

    # Smooth, non-periodic randomized envelope (replaces periodic sine LFO)
    raw_env = np.random.normal(0, 1, num_samples)
    b_low, a_low = butter(2, 0.4 / (0.5 * sample_rate), btype="low")
    smooth_env = lfilter(b_low, a_low, raw_env)
    smooth_env = (smooth_env - np.min(smooth_env)) / (
        np.max(smooth_env) - np.min(smooth_env) + 1e-8
    )

    # Warm mid-frequency crowd body (400Hz - 1300Hz)
    mid_cheer = apply_bandpass(noise, 400, 1300, sample_rate, order=3)

    return (base_roar * 0.5) + (mid_cheer * smooth_env * 0.5)


# ==========================================
# 2. ABSTRACT ROCK CONCERT SYNTHESIS
# ==========================================
def generate_rock_tracks(
    t: NDArray[np.float64], sample_rate: int
) -> NDArray[np.float64]:
    num_samples = len(t)

    # Distorted Power Chord Drones (E-B-E)
    f_root, f_fifth, f_octave = 82.41, 123.47, 164.81
    guitar_raw = (
        0.5 * np.sin(2 * np.pi * f_root * t)
        + 0.4 * np.sin(2 * np.pi * f_fifth * t)
        + 0.3 * np.sin(2 * np.pi * f_octave * t)
        + 0.15 * np.random.normal(0, 0.1, num_samples)
    )

    # Overdrive & Cabinet Emulation (capped under 3800Hz to prevent high chirps)
    distorted_guitar = apply_distortion(guitar_raw, drive=6.0)
    guitar_cab = apply_bandpass(
        distorted_guitar, 180, 3800, sample_rate, order=4
    )

    # Drums (120 BPM)
    bpm = 120.0
    beat_freq = bpm / 60.0
    beat_phase = np.mod(t * beat_freq, 1.0)

    # Kick Drum
    kick_env = np.exp(-10.0 * beat_phase)
    kick_freq = 45.0 + 75.0 * np.exp(-25.0 * beat_phase)
    kick = np.sin(2 * np.pi * kick_freq * t) * kick_env

    # Snare Drum (Backbeat on beats 2 & 4)
    snare_phase = np.mod((t * beat_freq) + 0.5, 1.0)
    snare_env = np.exp(-15.0 * snare_phase)
    snare_noise = (
        apply_bandpass(
            np.random.normal(0, 1, num_samples), 600, 3500, sample_rate
        )
        * snare_env
    )
    snare = snare_noise * 0.6

    # Bass Line
    bass_raw = np.sin(2 * np.pi * 41.2 * t) + 0.5 * np.sin(
        2 * np.pi * 82.4 * t
    )
    bass = apply_distortion(bass_raw, drive=2.5) * 0.5

    return (guitar_cab * 0.5) + (kick * 0.75) + (snare * 0.4) + (bass * 0.4)


# ==========================================
# 3. MIX & MASTERING
# ==========================================
def generate_concert_ambience(
    duration_sec: float = 20.0,
    sample_rate: int = 44100,
    output_filename: str = "rock_concert_crowd.wav",
    crowd_weight: float = 0.5,
    rock_weight: float = 0.6,
) -> None:
    num_samples = int(duration_sec * sample_rate)
    t: NDArray[np.float64] = np.linspace(
        0, duration_sec, num_samples, endpoint=False
    )

    crowd_signal = generate_crowd(t, sample_rate)
    rock_signal = generate_rock_tracks(t, sample_rate)

    # Slap-back reverb
    delay_samples = int(sample_rate * 0.08)
    reverb_rock = np.zeros_like(rock_signal)
    reverb_rock[delay_samples:] = rock_signal[:-delay_samples] * 0.3

    mixed_signal = (
        (crowd_signal * crowd_weight)
        + (rock_signal * rock_weight)
        + reverb_rock
    )

    # Master low-pass filter to ensure soft venue dampening
    master_audio = apply_bandpass(mixed_signal, 50, 6000, sample_rate, order=2)

    max_val = float(np.max(np.abs(master_audio)))
    if max_val > 0:
        master_audio = (master_audio / max_val) * 0.89

    audio_int16: NDArray[np.int16] = (master_audio * 32767).astype(np.int16)
    wavfile.write(output_filename, sample_rate, audio_int16)
    print(f"Clean rock concert audio generated: {output_filename} ({duration_sec}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate clean rock concert and crowd noise without whistle pulses."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="rock_concert_crowd.wav",
        help="Output WAV file path",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=20.0,
        help="Duration in seconds",
    )
    parser.add_argument(
        "--crowd-weight",
        type=float,
        default=0.5,
        help="Gain of crowd noise",
    )
    parser.add_argument(
        "--rock-weight",
        type=float,
        default=0.6,
        help="Gain of rock elements",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Sample rate in Hz",
    )

    args = parser.parse_args()

    generate_concert_ambience(
        duration_sec=args.duration,
        sample_rate=args.sample_rate,
        output_filename=args.output,
        crowd_weight=args.crowd_weight,
        rock_weight=args.rock_weight,
    )


if __name__ == "__main__":
    main()
