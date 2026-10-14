import argparse
from typing import Tuple
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile
from scipy.signal import butter, lfilter


def butter_bandpass(
    lowcut: float, highcut: float, fs: int, order: int = 5
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


def generate_huey_ambience(
    duration_sec: float = 15.0,
    sample_rate: int = 44100,
    output_filename: str = "woodstock_huey_cockpit.wav",
    rotor_weight: float = 0.55,
    static_weight: float = 0.25,
    chatter_weight: float = 0.12,
) -> None:
    num_samples: int = int(duration_sec * sample_rate)
    t: NDArray[np.float64] = np.linspace(
        0, duration_sec, num_samples, endpoint=False
    )

    # ==========================================
    # 1. HELICOPTER ROTOR SYNTHESIS (Bell UH-1 "Huey")
    # ==========================================
    # Huey main rotor: ~324 RPM = ~5.4 Hz rotation. 2 blades = 10.8 Hz BPF.
    bpf: float = 10.8

    # Sharp rotor "thump" impulses
    pulse_phase: NDArray[np.float64] = np.mod(t * bpf, 1.0)
    rotor_envelope: NDArray[np.float64] = np.exp(-12.0 * pulse_phase)

    # Low-end thump (60Hz - 140Hz fundamental body resonance)
    low_thump: NDArray[np.float64] = (
        np.sin(2 * np.pi * 70 * t) * 0.6 + np.sin(2 * np.pi * 140 * t) * 0.3
    )

    # Blade slice / air noise (filtered white noise modulated by envelope)
    noise: NDArray[np.float64] = np.random.normal(0, 1, num_samples)
    slice_noise: NDArray[np.float64] = apply_bandpass(
        noise, 150, 1200, sample_rate
    ) * (rotor_envelope**1.5)

    # Tail rotor hum (~24 Hz 2-blade tail rotor)
    tail_rotor: NDArray[np.float64] = np.sin(2 * np.pi * 24.5 * t) * 0.25

    # Combined rotor sound
    rotor_raw: NDArray[np.float64] = (
        (low_thump * rotor_envelope) + (slice_noise * 1.8) + tail_rotor
    )
    rotor_cockpit: NDArray[np.float64] = apply_bandpass(
        rotor_raw, 40, 1800, sample_rate
    )

    # ==========================================
    # 2. 122.8 MHz AM RADIO STATIC (VHF Airband)
    # ==========================================
    raw_static: NDArray[np.float64] = np.random.normal(0, 1, num_samples)
    radio_static: NDArray[np.float64] = apply_bandpass(
        raw_static, 350, 2800, sample_rate, order=4
    )

    # 400Hz aircraft AC power supply hum + 1020Hz heterodyne whistle
    ac_hum: NDArray[np.float64] = np.sin(2 * np.pi * 400 * t) * 0.015
    heterodyne: NDArray[np.float64] = np.sin(2 * np.pi * 1020 * t) * 0.008

    radio_static += ac_hum + heterodyne

    # ==========================================
    # 3. INDISTINGUISHABLE RADIO CHATTER
    # ==========================================
    chatter_raw: NDArray[np.float64] = np.random.normal(0, 1, num_samples)
    chatter_filtered: NDArray[np.float64] = apply_bandpass(
        chatter_raw, 800, 2200, sample_rate, order=4
    )

    speech_envelope: NDArray[np.float64] = 0.5 * (
        1 + np.sin(2 * np.pi * 0.7 * t + np.sin(2 * np.pi * 0.15 * t))
    )
    speech_envelope = np.where(speech_envelope > 0.65, speech_envelope, 0.0)

    quiet_chatter: NDArray[np.float64] = chatter_filtered * speech_envelope

    # ==========================================
    # 4. FINAL MIX & NORMALIZATION
    # ==========================================
    mixed_signal: NDArray[np.float64] = (
        (rotor_cockpit * rotor_weight)
        + (radio_static * static_weight)
        + (quiet_chatter * chatter_weight)
    )

    # Master bandpass matching military aviation headset profile
    final_output: NDArray[np.float64] = apply_bandpass(
        mixed_signal, 100, 3400, sample_rate
    )

    max_val: float = float(np.max(np.abs(final_output)))
    if max_val > 0:
        final_output = (final_output / max_val) * 0.89

    audio_int16: NDArray[np.int16] = (final_output * 32767).astype(np.int16)

    wavfile.write(output_filename, sample_rate, audio_int16)
    print(f"Audio generated: {output_filename} ({duration_sec}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate simulated Bell UH-1 Huey cockpit audio ambience."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="woodstock_huey_cockpit.wav",
        help="Output WAV file path (default: woodstock_huey_cockpit.wav)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=15.0,
        help="Duration in seconds (default: 15.0)",
    )
    parser.add_argument(
        "--rotor-weight",
        type=float,
        default=0.55,
        help="Weight/gain of rotor thump (default: 0.55)",
    )
    parser.add_argument(
        "--static-weight",
        type=float,
        default=0.25,
        help="Weight/gain of radio static (default: 0.25)",
    )
    parser.add_argument(
        "--chatter-weight",
        type=float,
        default=0.12,
        help="Weight/gain of radio chatter (default: 0.12)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)",
    )

    args = parser.parse_args()

    generate_huey_ambience(
        duration_sec=args.duration,
        sample_rate=args.sample_rate,
        output_filename=args.output,
        rotor_weight=args.rotor_weight,
        static_weight=args.static_weight,
        chatter_weight=args.chatter_weight,
    )


if __name__ == "__main__":
    main()
