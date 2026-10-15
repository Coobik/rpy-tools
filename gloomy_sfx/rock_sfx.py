import argparse
from typing import Tuple
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile
from scipy.signal import butter, lfilter


def butter_bandpass(
    lowcut: float, highcut: float, fs: int, order: int = 3
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
    order: int = 2,
) -> NDArray[np.float64]:
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return lfilter(b, a, data)


def tube_overdrive(
    data: NDArray[np.float64], drive: float = 3.5
) -> NDArray[np.float64]:
    """Simulates asymmetric tube amp distortion."""
    x = data * drive
    return np.where(x > 0, np.tanh(x), 0.8 * np.tanh(x))


# ==========================================
# 1. 1960s ROCK BAND SYNTHESIS (DYNAMIC RIFFS)
# ==========================================
def generate_rock_band(
    t: NDArray[np.float64], sample_rate: int
) -> NDArray[np.float64]:
    num_samples = len(t)
    bpm = 116.0
    beat_duration = 60.0 / bpm
    total_beats = int(t[-1] / beat_duration) + 1

    guitar_signal = np.zeros(num_samples)
    bass_signal = np.zeros(num_samples)
    drums_signal = np.zeros(num_samples)

    # Progression (Hey Joe / Hendrix style): C -> G -> D -> A -> E
    chord_freqs = [
        [130.81, 164.81, 196.00],  # C major
        [146.83, 185.00, 220.00],  # D major
        [110.00, 138.59, 164.81],  # A major
        [82.41, 123.47, 164.81, 207.65],  # E7/E9
    ]

    # --- GUITAR & BASS GENERATION ---
    for beat in range(total_beats):
        beat_start_time = beat * beat_duration
        beat_idx = int(beat_start_time * sample_rate)
        note_length = int(beat_duration * 0.95 * sample_rate)

        if beat_idx >= num_samples:
            break

        current_note_length = min(note_length, num_samples - beat_idx)
        t_note = np.linspace(
            0,
            current_note_length / sample_rate,
            current_note_length,
            endpoint=False,
        )

        # Pick attack envelope (sharp onset, smooth exponential decay)
        pluck_env = np.exp(-4.5 * t_note)

        # 6 Hz hand vibrato
        vibrato = 1.0 + 0.012 * np.sin(2 * np.pi * 6.0 * t_note)

        # Select chord based on 4-bar rhythm
        chord = chord_freqs[(beat // 2) % len(chord_freqs)]

        # Synthesize plucked guitar chord
        chord_wave = np.zeros(current_note_length)
        for freq in chord:
            # Fundamental + harmonics for rich string timbre
            string_sound = (
                0.6 * np.sin(2 * np.pi * freq * vibrato * t_note)
                + 0.3 * np.sin(2 * np.pi * freq * 2 * vibrato * t_note)
                + 0.15 * np.sin(2 * np.pi * freq * 3 * vibrato * t_note)
            )
            chord_wave += string_sound

        guitar_signal[beat_idx : beat_idx + current_note_length] += (
            chord_wave * pluck_env
        )

        # Bassline note (Root of current chord, pitched 1 octave down)
        bass_freq = chord[0] / 2.0
        bass_env = np.exp(-3.0 * t_note)
        bass_wave = (
            np.sin(2 * np.pi * bass_freq * t_note)
            + 0.4 * np.sin(2 * np.pi * bass_freq * 2 * t_note)
        ) * bass_env

        bass_signal[beat_idx : beat_idx + current_note_length] += bass_wave

    # Guitar Cabinet Emulation (Marshall 4x12 stack filter)
    distorted_guitar = tube_overdrive(guitar_signal, drive=4.5)
    guitar_cab = apply_bandpass(
        distorted_guitar, 220, 3800, sample_rate, order=3
    )

    # Bass Amp Filter
    bass_amp = apply_bandpass(
        tube_overdrive(bass_signal, drive=2.0), 40, 800, sample_rate, order=2
    )

    # --- DRUMS & CYMBALS ---
    beat_phase = np.mod(t * (bpm / 60.0), 1.0)
    eight_phase = np.mod(t * (bpm / 60.0) * 2.0, 1.0)

    # Kick Drum (Pitched punch)
    kick_env = np.exp(-12.0 * beat_phase)
    kick = np.sin(2 * np.pi * 55.0 * t) * kick_env

    # Snare Drum (Beat 2 & 4)
    snare_phase = np.mod((t * (bpm / 60.0)) + 0.5, 1.0)
    snare_env = np.exp(-16.0 * snare_phase)
    snare_noise = (
        apply_bandpass(
            np.random.normal(0, 1, num_samples), 500, 3200, sample_rate, order=2
        )
        * snare_env
    )

    # Hi-Hat & Cymbal Shimmer (High-pass white noise on 8th notes)
    hihat_env = np.exp(-25.0 * eight_phase)
    hihat = (
        apply_bandpass(
            np.random.normal(0, 1, num_samples), 4500, 11000, sample_rate, order=2
        )
        * hihat_env
    )

    drums_signal = (kick * 0.7) + (snare_noise * 0.45) + (hihat * 0.25)

    return (guitar_cab * 0.5) + (bass_amp * 0.4) + drums_signal


# ==========================================
# 2. STADIUM CROWD CHEERS
# ==========================================
def generate_crowd(
    t: NDArray[np.float64], sample_rate: int
) -> NDArray[np.float64]:
    num_samples = len(t)
    white = np.random.normal(0, 1, num_samples)

    # Pink noise base for stadium atmosphere
    b_pink, a_pink = butter(1, 1000 / (0.5 * sample_rate), btype="low")
    pink = lfilter(b_pink, a_pink, white)

    base_roar = apply_bandpass(pink, 150, 850, sample_rate, order=2)

    # Dynamic swell envelopes
    raw_env1 = np.random.normal(0, 1, num_samples)
    b_env, a_env = butter(1, 0.2 / (0.5 * sample_rate), btype="low")
    env1 = lfilter(b_env, a_env, raw_env1)
    env1 = np.clip((env1 - np.mean(env1)) / (np.std(env1) + 1e-8), 0, None) ** 2

    cheers = apply_bandpass(pink, 300, 1400, sample_rate, order=2) * env1

    return (base_roar * 0.35) + (cheers * 0.65)


# ==========================================
# 3. MAIN MIX & EXPORT
# ==========================================
def generate_concert_ambience(
    duration_sec: float = 20.0,
    sample_rate: int = 44100,
    output_filename: str = "rock_concert.wav",
    crowd_weight: float = 0.45,
    rock_weight: float = 0.6,
) -> None:
    num_samples = int(duration_sec * sample_rate)
    t: NDArray[np.float64] = np.linspace(
        0, duration_sec, num_samples, endpoint=False
    )

    rock_signal = generate_rock_band(t, sample_rate)
    crowd_signal = generate_crowd(t, sample_rate)

    # Slap-back stadium echo (90ms delay)
    delay_samples = int(sample_rate * 0.09)
    echo = np.zeros_like(rock_signal)
    echo[delay_samples:] = rock_signal[:-delay_samples] * 0.28

    master_mix = (
        (rock_signal * rock_weight) + (crowd_signal * crowd_weight) + echo
    )

    # Overall venue master filter
    master_audio = apply_bandpass(master_mix, 45, 9000, sample_rate, order=2)

    # Normalize to -1 dB
    max_val = float(np.max(np.abs(master_audio)))
    if max_val > 0:
        master_audio = (master_audio / max_val) * 0.89

    audio_int16: NDArray[np.int16] = (master_audio * 32767).astype(np.int16)
    wavfile.write(output_filename, sample_rate, audio_int16)
    print(f"Rock concert audio generated: {output_filename} ({duration_sec}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 1960s live rock concert ambience."
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="rock_concert.wav",
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
        default=0.45,
        help="Gain of crowd noise",
    )

    parser.add_argument(
        "--rock-weight",
        type=float,
        default=0.6,
        help="Gain of rock band elements",
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
