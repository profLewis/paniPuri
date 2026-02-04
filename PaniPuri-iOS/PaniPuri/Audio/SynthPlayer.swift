import Foundation
import AVFoundation
import os

/// Additive synthesis engine that renders steel pan tones in real time using
/// an `AVAudioSourceNode`. Each voice produces seven sine partials with
/// per-partial ADSR envelopes and a 2nd-order Butterworth lowpass filter.
class SynthPlayer {

    // MARK: - Constants

    private let maxVoices = 16
    private let voiceDuration: Double = 2.0  // seconds before release

    // MARK: - Properties

    private let engine: AVAudioEngine
    private let calibration: CalibrationData
    private var sourceNode: AVAudioSourceNode!

    /// Active synthesis voices. Protected by `voiceLock`.
    private var voices: [SynthVoice] = []
    private var voiceLock = os_unfair_lock()

    // MARK: - Initialisation

    init(engine: AVAudioEngine) {
        self.engine = engine
        self.calibration = CalibrationData.load()
        setupSourceNode()
    }

    // MARK: - Source Node

    private func setupSourceNode() {
        let sampleRate = engine.outputNode.outputFormat(forBus: 0).sampleRate
        let sr = sampleRate > 0 ? sampleRate : 44100.0

        sourceNode = AVAudioSourceNode { [weak self] _, _, frameCount, audioBufferList -> OSStatus in
            guard let self = self else { return noErr }

            let ablPointer = UnsafeMutableAudioBufferListPointer(audioBufferList)
            let frames = Int(frameCount)

            // Acquire lock, render, release lock.
            os_unfair_lock_lock(&self.voiceLock)
            let voicesCopy = self.voices
            os_unfair_lock_unlock(&self.voiceLock)

            // Zero the output buffers first.
            for buf in ablPointer {
                guard let data = buf.mData else { continue }
                memset(data, 0, Int(buf.mDataByteSize))
            }

            // Render each voice into the output.
            for var voice in voicesCopy {
                for frame in 0..<frames {
                    let sample = voice.renderSample(sampleRate: sr)
                    for buf in ablPointer {
                        guard let data = buf.mData else { continue }
                        let ptr = data.assumingMemoryBound(to: Float.self)
                        ptr[frame] += Float(sample)
                    }
                }
            }

            // Write back updated voice states and prune finished voices.
            os_unfair_lock_lock(&self.voiceLock)
            // Rebuild voices array from the rendered copies.
            // voicesCopy indices correspond to self.voices indices only if
            // no concurrent mutation happened. Since we hold the lock
            // around both reads and writes, we update in-place based on
            // the copy we rendered.
            var updatedVoices: [SynthVoice] = []
            // We need to update from the copies we actually rendered.
            // Because the render loop mutated local copies, reconstruct.
            // Re-render is not feasible, so we track via sampleIndex in
            // the struct. We'll take a simpler approach: render into the
            // copies directly and write them back.
            os_unfair_lock_unlock(&self.voiceLock)

            // Use a second pass approach: we already rendered into `voicesCopy`
            // but Swift value semantics mean those are copies. We need to
            // render with mutable references. Let's use the direct approach
            // instead.
            // (The actual rendering is done inline below via the mutable
            // render method on the struct.)

            return noErr
        }

        // Replace the naive callback above with a correct mutable-voice version.
        sourceNode = AVAudioSourceNode { [weak self] _, _, frameCount, audioBufferList -> OSStatus in
            guard let self = self else { return noErr }

            let ablPointer = UnsafeMutableAudioBufferListPointer(audioBufferList)
            let frames = Int(frameCount)

            // Zero output buffers.
            for buf in ablPointer {
                guard let data = buf.mData else { continue }
                memset(data, 0, Int(buf.mDataByteSize))
            }

            os_unfair_lock_lock(&self.voiceLock)

            for i in (0..<self.voices.count).reversed() {
                for frame in 0..<frames {
                    let sample = self.voices[i].renderSample(sampleRate: sr)
                    for buf in ablPointer {
                        guard let data = buf.mData else { continue }
                        let ptr = data.assumingMemoryBound(to: Float.self)
                        ptr[frame] += Float(sample)
                    }
                }
            }

            // Prune finished voices.
            self.voices.removeAll { $0.isFinished }

            os_unfair_lock_unlock(&self.voiceLock)

            return noErr
        }

        let format = AVAudioFormat(standardFormatWithSampleRate: sr, channels: 2)!
        engine.attach(sourceNode)
        engine.connect(sourceNode, to: engine.mainMixerNode, format: format)
    }

    // MARK: - Playback

    /// Triggers a new synthesis voice for the given note.
    func play(note: NoteShape) {
        let params = calibration.params(forMidi: note.midiNote)
        let defaults = calibration.defaults
        let freq = NoteIdentity.midiToFreq(note.midiNote)

        let voice = SynthVoice(
            frequency: freq,
            params: params,
            defaults: defaults,
            duration: voiceDuration
        )

        os_unfair_lock_lock(&voiceLock)

        // Steal oldest voice if at capacity.
        if voices.count >= maxVoices {
            voices.removeFirst()
        }
        voices.append(voice)

        os_unfair_lock_unlock(&voiceLock)
    }
}

// MARK: - SynthVoice

/// A value-type synthesis voice that produces seven sine partials with
/// per-partial ADSR envelopes and a Butterworth lowpass filter.
struct SynthVoice {

    // MARK: - Partial Descriptor

    /// Describes a single sine partial with its own envelope timing.
    struct Partial {
        var phase: Double = 0.0
        let freqRatio: Double
        let amplitude: Double
        let decayMultiplier: Double
    }

    // MARK: - Properties

    let frequency: Double
    let attackTime: Double
    let decayTime: Double
    let sustainLevel: Double
    let releaseTime: Double
    let filterCutoff: Double
    let totalDuration: Double  // duration + releaseTime

    private(set) var sampleIndex: Int = 0
    private(set) var isFinished: Bool = false

    // Seven partials
    private var partials: [Partial]

    // Butterworth lowpass biquad state
    private var biquadB0: Double = 0
    private var biquadB1: Double = 0
    private var biquadB2: Double = 0
    private var biquadA1: Double = 0
    private var biquadA2: Double = 0
    private var filterX1: Double = 0
    private var filterX2: Double = 0
    private var filterY1: Double = 0
    private var filterY2: Double = 0
    private var filterInitialized: Bool = false

    // MARK: - Initialisation

    init(frequency: Double, params: CalibrationNote, defaults: CalibrationDefaults, duration: Double) {
        self.frequency = frequency
        self.attackTime = params.attack
        self.decayTime = params.decay
        self.sustainLevel = params.sustain
        self.releaseTime = params.release
        self.filterCutoff = params.filter
        self.totalDuration = duration + params.release

        // Detune: defaults.detune is in units, interpreted as detune * 0.001
        // frequency ratio offset. E.g. detune=2 means +/-0.002 freq ratio.
        let detuneRatio = defaults.detune * 0.001

        // Build the seven partials with their decay multipliers.
        // Amplitudes are normalised from the calibration percentages.
        let ampScale = 1.0 / 100.0

        partials = [
            // Sub-bass: 0.5x fundamental
            Partial(freqRatio: 0.5, amplitude: params.sub_bass * ampScale, decayMultiplier: 1.0),
            // Fundamental - detune
            Partial(freqRatio: 1.0 - detuneRatio, amplitude: params.fundamental * ampScale, decayMultiplier: 1.0),
            // Fundamental
            Partial(freqRatio: 1.0, amplitude: params.fundamental * ampScale, decayMultiplier: 1.0),
            // Fundamental + detune
            Partial(freqRatio: 1.0 + detuneRatio, amplitude: params.fundamental * ampScale, decayMultiplier: 1.0),
            // 2nd harmonic
            Partial(freqRatio: 2.0, amplitude: params.harmonic2 * ampScale, decayMultiplier: 1.3),
            // 3rd harmonic
            Partial(freqRatio: 3.0, amplitude: params.harmonic3 * ampScale, decayMultiplier: 1.8),
            // 4th harmonic
            Partial(freqRatio: 4.0, amplitude: params.harmonic4 * ampScale, decayMultiplier: 2.2),
        ]
    }

    // MARK: - Rendering

    /// Renders a single audio sample and advances internal state.
    /// This method is designed to be called from the audio render callback
    /// and performs no allocations.
    mutating func renderSample(sampleRate: Double) -> Double {
        guard !isFinished else { return 0.0 }

        let t = Double(sampleIndex) / sampleRate
        sampleIndex += 1

        // Check if voice has exceeded its total duration.
        if t >= totalDuration {
            isFinished = true
            return 0.0
        }

        // Compute master envelope (attack -> hold -> release).
        let masterEnv: Double
        let noteEndTime = totalDuration - releaseTime
        if t < attackTime {
            // Attack: ramp to 0.8
            masterEnv = 0.8 * (t / max(attackTime, 0.0001))
        } else if t < noteEndTime {
            // Hold
            masterEnv = 0.8
        } else {
            // Release: ramp to 0
            let releaseElapsed = t - noteEndTime
            let relProgress = releaseElapsed / max(releaseTime, 0.0001)
            masterEnv = 0.8 * max(0.0, 1.0 - relProgress)
        }

        // Sum partials with per-partial envelopes.
        var sum = 0.0
        let twoPi = 2.0 * Double.pi

        for i in 0..<partials.count {
            let partial = partials[i]
            let partialFreq = frequency * partial.freqRatio

            // Per-partial envelope
            let partialEnv: Double
            let effectiveDecay = decayTime / partial.decayMultiplier
            if t < attackTime {
                // Attack: linear ramp from 0 to amplitude
                partialEnv = partial.amplitude * (t / max(attackTime, 0.0001))
            } else if t < attackTime + effectiveDecay {
                // Decay: ramp from amplitude to amplitude * sustainLevel
                let decayElapsed = t - attackTime
                let decayProgress = decayElapsed / max(effectiveDecay, 0.0001)
                partialEnv = partial.amplitude * (1.0 - (1.0 - sustainLevel) * decayProgress)
            } else if t < noteEndTime {
                // Sustain: exponential decay
                let sustainElapsed = t - attackTime - effectiveDecay
                partialEnv = partial.amplitude * sustainLevel * exp(-sustainElapsed * 2.0)
            } else {
                // Release: linear ramp to 0
                let releaseElapsed = t - noteEndTime
                let relProgress = releaseElapsed / max(releaseTime, 0.0001)
                let sustainElapsed = noteEndTime - attackTime - effectiveDecay
                let sustainAmp = partial.amplitude * sustainLevel * exp(-max(sustainElapsed, 0.0) * 2.0)
                partialEnv = sustainAmp * max(0.0, 1.0 - relProgress)
            }

            // Sine oscillator
            let phaseDelta = twoPi * partialFreq / sampleRate
            partials[i].phase += phaseDelta
            // Wrap phase to prevent floating point accumulation
            if partials[i].phase > twoPi {
                partials[i].phase -= twoPi
            }
            sum += sin(partials[i].phase) * partialEnv
        }

        // Apply master envelope
        sum *= masterEnv

        // 2nd-order Butterworth lowpass filter
        if !filterInitialized {
            computeFilterCoefficients(sampleRate: sampleRate)
            filterInitialized = true
        }

        let filtered = biquadB0 * sum + biquadB1 * filterX1 + biquadB2 * filterX2
                      - biquadA1 * filterY1 - biquadA2 * filterY2
        filterX2 = filterX1
        filterX1 = sum
        filterY2 = filterY1
        filterY1 = filtered

        return filtered
    }

    // MARK: - Filter

    /// Computes 2nd-order Butterworth lowpass biquad coefficients.
    private mutating func computeFilterCoefficients(sampleRate: Double) {
        let cutoff = min(filterCutoff, sampleRate * 0.49)  // Nyquist guard
        let omega = 2.0 * Double.pi * cutoff / sampleRate
        let cosOmega = cos(omega)
        let sinOmega = sin(omega)
        let alpha = sinOmega / (2.0 * sqrt(2.0))  // Q = sqrt(2)/2 for Butterworth

        let a0 = 1.0 + alpha
        biquadB0 = ((1.0 - cosOmega) / 2.0) / a0
        biquadB1 = (1.0 - cosOmega) / a0
        biquadB2 = ((1.0 - cosOmega) / 2.0) / a0
        biquadA1 = (-2.0 * cosOmega) / a0
        biquadA2 = (1.0 - alpha) / a0
    }
}
