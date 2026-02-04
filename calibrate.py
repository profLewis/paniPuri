#!/usr/bin/env python3
"""
Calibration tool for PaniPuri synthesizer.

Analyzes urbanPan WAV samples to extract per-note synthesis parameters,
producing a calibration.json file that the synth engine uses to generate
steel pan tones matching the real recordings.

Usage:
    python calibrate.py                    # Analyze samples, write calibration.json
    python calibrate.py --verbose          # Show per-note analysis details
    python calibrate.py --output out.json  # Write to custom path

Algorithms adapted from deepPan's analyze_audio.py.
"""

import os
import json
import argparse
import numpy as np
from scipy.io import wavfile
from scipy.fft import fft, fftfreq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")

NOTE_NAMES_SHARP = ["C", "CS", "D", "DS", "E", "F", "FS", "G", "GS", "A", "AS", "B"]
NOTE_NAMES_DISPLAY = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MIDI_LOW = 53   # F3
MIDI_HIGH = 84  # C6

# Use layer 2 (forte) as the primary calibration source - full chromatic coverage
CALIBRATION_LAYER = 2


def midi_to_freq(midi_note):
    """Convert MIDI note number to frequency (A4=440Hz)."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def midi_to_note_name(midi_note):
    """Convert MIDI note to urbanPan filename format."""
    octave = (midi_note // 12) - 1
    note_idx = midi_note % 12
    return f"{NOTE_NAMES_SHARP[note_idx]}{octave}"


def midi_to_display(midi_note):
    """Convert MIDI note to readable name."""
    octave = (midi_note // 12) - 1
    note_idx = midi_note % 12
    return f"{NOTE_NAMES_DISPLAY[note_idx]}{octave}"


# ---------------------------------------------------------------------------
# Pitch detection
# ---------------------------------------------------------------------------

def detect_pitch_autocorr(audio, sample_rate, min_freq=50, max_freq=2000):
    """Detect fundamental frequency using autocorrelation."""
    segment_start = int(0.05 * sample_rate)
    segment_length = int(0.2 * sample_rate)
    segment_end = min(segment_start + segment_length, len(audio))

    if segment_end <= segment_start:
        segment = audio
    else:
        segment = audio[segment_start:segment_end]

    segment = segment - np.mean(segment)
    peak = np.max(np.abs(segment))
    if peak > 0:
        segment = segment / peak

    corr = np.correlate(segment, segment, mode='full')
    corr = corr[len(corr) // 2:]

    min_lag = int(sample_rate / max_freq)
    max_lag = min(int(sample_rate / min_freq), len(corr) - 1)

    corr_segment = corr[min_lag:max_lag]
    if len(corr_segment) == 0:
        return 0

    peak_idx = np.argmax(corr_segment) + min_lag
    return sample_rate / peak_idx if peak_idx > 0 else 0


def detect_pitch_hps(audio, sample_rate, min_freq=50, max_freq=2000):
    """Detect fundamental using FFT with Harmonic Product Spectrum."""
    segment_start = int(0.05 * sample_rate)
    segment_length = int(0.3 * sample_rate)
    segment_end = min(segment_start + segment_length, len(audio))

    if segment_end <= segment_start:
        segment = audio
    else:
        segment = audio[segment_start:segment_end]

    window = np.hanning(len(segment))
    segment = segment * window

    n = len(segment)
    spectrum = np.abs(fft(segment))[:n // 2]
    freqs = fftfreq(n, 1 / sample_rate)[:n // 2]

    hps = spectrum.copy()
    for h in range(2, 6):
        decimated = spectrum[::h]
        hps[:len(decimated)] *= decimated

    freq_mask = (freqs >= min_freq) & (freqs <= max_freq)
    valid_hps = hps.copy()
    valid_hps[~freq_mask] = 0

    peak_idx = np.argmax(valid_hps)
    if peak_idx > 0 and freqs[peak_idx] >= min_freq:
        return freqs[peak_idx]
    return 0


def detect_pitch(audio, sample_rate, expected_freq=None):
    """Detect fundamental using both methods, cross-validate with expected."""
    freq_ac = detect_pitch_autocorr(audio, sample_rate)
    freq_hps = detect_pitch_hps(audio, sample_rate)

    # If we have an expected frequency, prefer the method closest to it
    if expected_freq and expected_freq > 0:
        err_ac = abs(freq_ac - expected_freq) / expected_freq if freq_ac > 0 else 1.0
        err_hps = abs(freq_hps - expected_freq) / expected_freq if freq_hps > 0 else 1.0

        if err_ac < 0.1 and err_hps < 0.1:
            return (freq_ac + freq_hps) / 2
        elif err_ac < err_hps:
            return freq_ac
        else:
            return freq_hps

    # No expected freq - average if they agree, prefer HPS otherwise
    if freq_ac > 0 and freq_hps > 0:
        if abs(freq_hps - freq_ac) < freq_ac * 0.1:
            return (freq_ac + freq_hps) / 2
        return freq_hps

    return freq_hps if freq_hps > 0 else freq_ac


# ---------------------------------------------------------------------------
# Harmonic analysis
# ---------------------------------------------------------------------------

def analyze_harmonics(audio, sample_rate, fundamental_freq):
    """Analyze harmonic content relative to the fundamental."""
    segment_start = int(0.1 * sample_rate)
    segment_length = int(0.3 * sample_rate)
    segment_end = min(segment_start + segment_length, len(audio))

    if segment_end <= segment_start:
        segment = audio
    else:
        segment = audio[segment_start:segment_end]

    n = len(segment)
    window = np.hanning(n)
    spectrum = np.abs(fft(segment * window))[:n // 2]
    freqs = fftfreq(n, 1 / sample_rate)[:n // 2]

    harmonic_ratios = [0.5, 1.0, 2.0, 3.0, 4.0]
    harmonic_names = ['sub_bass', 'fundamental', 'harmonic2', 'harmonic3', 'harmonic4']

    harmonics = {}
    fund_amp = 0

    for ratio, name in zip(harmonic_ratios, harmonic_names):
        target_freq = fundamental_freq * ratio
        tolerance = fundamental_freq * 0.05
        freq_mask = (freqs >= target_freq - tolerance) & (freqs <= target_freq + tolerance)

        if np.any(freq_mask):
            amp = np.max(spectrum[freq_mask])
            harmonics[name] = amp
            if name == 'fundamental':
                fund_amp = amp
        else:
            harmonics[name] = 0

    if fund_amp > 0:
        for name in harmonic_names:
            harmonics[name] = min(100, int((harmonics[name] / fund_amp) * 100))

    return harmonics


# ---------------------------------------------------------------------------
# Envelope analysis
# ---------------------------------------------------------------------------

def analyze_envelope(audio, sample_rate):
    """Estimate ADSR envelope parameters from audio."""
    envelope = np.abs(audio)

    window_size = int(0.01 * sample_rate)
    if window_size > 1:
        kernel = np.ones(window_size) / window_size
        envelope = np.convolve(envelope, kernel, mode='same')

    max_amp = np.max(envelope)
    if max_amp > 0:
        envelope = envelope / max_amp

    # Attack: time to reach 90% of peak
    peak_idx = np.argmax(envelope)
    attack_idx = 0
    for i in range(peak_idx):
        if envelope[i] >= 0.9:
            attack_idx = i
            break
    attack_ms = (attack_idx / sample_rate) * 1000

    # Sustain level: average in middle portion
    sustain_start = int(0.3 * len(envelope))
    sustain_end = int(0.6 * len(envelope))
    if sustain_end > sustain_start:
        sustain_level = np.mean(envelope[sustain_start:sustain_end])
    else:
        sustain_level = 0.2

    # Decay: time from peak to sustain level
    decay_idx = peak_idx
    for i in range(peak_idx, len(envelope)):
        if envelope[i] <= sustain_level * 1.1:
            decay_idx = i
            break
    decay_ms = ((decay_idx - peak_idx) / sample_rate) * 1000

    # Release: time for final portion to drop to 10%
    release_start = int(0.7 * len(envelope))
    if release_start < len(envelope):
        release_segment = envelope[release_start:]
        if len(release_segment) > 0 and release_segment[0] > 0:
            threshold = release_segment[0] * 0.1
            release_idx = len(release_segment)
            for i, val in enumerate(release_segment):
                if val <= threshold:
                    release_idx = i
                    break
            release_ms = (release_idx / sample_rate) * 1000
        else:
            release_ms = 300
    else:
        release_ms = 300

    return {
        'attack': max(1, min(200, int(attack_ms))),
        'decay': max(50, min(2000, int(decay_ms))),
        'sustain': max(0, min(100, int(sustain_level * 100))),
        'release': max(50, min(2000, int(release_ms))),
    }


# ---------------------------------------------------------------------------
# Spectral brightness / filter estimation
# ---------------------------------------------------------------------------

def analyze_brightness(audio, sample_rate, fundamental_freq):
    """Estimate filter cutoff and brightness from spectral shape."""
    n = len(audio)
    window = np.hanning(n)
    spectrum = np.abs(fft(audio * window))[:n // 2]
    freqs = fftfreq(n, 1 / sample_rate)[:n // 2]

    # Spectral centroid
    total = np.sum(spectrum)
    if total > 0:
        centroid = np.sum(freqs * spectrum) / total
    else:
        centroid = 1000

    # Rolloff (85% of energy)
    cumsum = np.cumsum(spectrum)
    if cumsum[-1] > 0:
        rolloff_idx = np.where(cumsum >= 0.85 * cumsum[-1])[0]
        rolloff_freq = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 6000
    else:
        rolloff_freq = 6000

    filter_cutoff = max(500, min(10000, int(rolloff_freq)))

    brightness_ratio = centroid / fundamental_freq if fundamental_freq > 0 else 2
    brightness = max(0, min(100, int((brightness_ratio - 1) * 25 + 50)))

    return {
        'filter': filter_cutoff,
        'brightness': brightness,
    }


# ---------------------------------------------------------------------------
# Single sample analysis
# ---------------------------------------------------------------------------

def analyze_sample(filepath, expected_freq=None):
    """Analyze a single WAV sample and return synthesis parameters."""
    sample_rate, audio = wavfile.read(filepath)

    # Convert to mono float
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float32) / 2147483648.0

    freq = detect_pitch(audio, sample_rate, expected_freq)
    harmonics = analyze_harmonics(audio, sample_rate, freq if freq > 0 else (expected_freq or 440))
    envelope = analyze_envelope(audio, sample_rate)
    brightness = analyze_brightness(audio, sample_rate, freq if freq > 0 else (expected_freq or 440))

    return {
        'freq': round(freq, 1),
        'attack': envelope['attack'],
        'decay': envelope['decay'],
        'sustain': envelope['sustain'],
        'release': envelope['release'],
        'sub_bass': harmonics.get('sub_bass', 20),
        'fundamental': harmonics.get('fundamental', 100),
        'harmonic2': harmonics.get('harmonic2', 30),
        'harmonic3': harmonics.get('harmonic3', 10),
        'harmonic4': harmonics.get('harmonic4', 5),
        'filter': brightness['filter'],
        'brightness': brightness['brightness'],
    }


# ---------------------------------------------------------------------------
# Batch calibration
# ---------------------------------------------------------------------------

def calibrate(sample_dir=SAMPLE_DIR, output_path=DEFAULT_OUTPUT, verbose=False):
    """Analyze all layer-2 samples and produce calibration.json."""
    notes = {}
    analyzed = 0
    missing = 0

    print(f"Calibrating from samples in {sample_dir}/")
    print(f"Using velocity layer {CALIBRATION_LAYER} (forte)\n")

    for midi_note in range(MIDI_LOW, MIDI_HIGH + 1):
        note_name = midi_to_note_name(midi_note)
        display = midi_to_display(midi_note)
        filename = f"{CALIBRATION_LAYER}-{note_name}.wav"
        filepath = os.path.join(sample_dir, filename)

        if not os.path.exists(filepath):
            if verbose:
                print(f"  {display:5s} (MIDI {midi_note}): MISSING {filename}")
            missing += 1
            continue

        expected_freq = midi_to_freq(midi_note)
        params = analyze_sample(filepath, expected_freq)
        notes[str(midi_note)] = params
        analyzed += 1

        freq_err = abs(params['freq'] - expected_freq) / expected_freq * 100
        if verbose:
            print(f"  {display:5s} (MIDI {midi_note}): "
                  f"freq={params['freq']:7.1f} Hz (exp {expected_freq:.1f}, err {freq_err:.1f}%), "
                  f"A={params['attack']}ms D={params['decay']}ms S={params['sustain']}% "
                  f"sub={params['sub_bass']} h2={params['harmonic2']} h3={params['harmonic3']} h4={params['harmonic4']} "
                  f"filt={params['filter']} bright={params['brightness']}")
        else:
            print(f"  {display:5s} (MIDI {midi_note}): {params['freq']:.1f} Hz, "
                  f"A={params['attack']} D={params['decay']} S={params['sustain']}", flush=True)

    # Compute defaults (averaged parameters for interpolation/fallback)
    if notes:
        param_keys = ['attack', 'decay', 'sustain', 'release',
                      'sub_bass', 'fundamental', 'harmonic2', 'harmonic3', 'harmonic4',
                      'filter', 'brightness']
        defaults = {}
        for key in param_keys:
            values = [n[key] for n in notes.values()]
            defaults[key] = int(np.mean(values))
        defaults['detune'] = 2
    else:
        defaults = {
            'attack': 15, 'decay': 500, 'sustain': 20, 'release': 300,
            'sub_bass': 20, 'fundamental': 100, 'harmonic2': 30,
            'harmonic3': 10, 'harmonic4': 5,
            'filter': 6000, 'brightness': 50, 'detune': 2,
        }

    calibration = {
        'notes': notes,
        'defaults': defaults,
    }

    with open(output_path, 'w') as f:
        json.dump(calibration, f, indent=2)

    print(f"\nCalibration complete:")
    print(f"  Analyzed: {analyzed} notes")
    print(f"  Missing:  {missing} notes")
    print(f"  Output:   {output_path}")
    print(f"\nDefault parameters (averaged):")
    for k, v in defaults.items():
        print(f"  {k}: {v}")

    return calibration


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calibrate PaniPuri synthesizer from urbanPan samples"
    )
    parser.add_argument(
        '--output', '-o', default=DEFAULT_OUTPUT,
        help=f"Output calibration JSON file (default: calibration.json)"
    )
    parser.add_argument(
        '--samples', default=SAMPLE_DIR,
        help=f"Sample directory (default: samples/)"
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help="Show detailed per-note analysis"
    )

    args = parser.parse_args()
    calibrate(args.samples, args.output, args.verbose)


if __name__ == '__main__':
    main()
