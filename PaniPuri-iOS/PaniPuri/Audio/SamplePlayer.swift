import Foundation
import AVFoundation

/// Sample-based playback engine with 16-voice polyphony.
/// Loads all steel pan WAV files from the app bundle into memory at
/// initialisation and plays them back using a round-robin pool of
/// `AVAudioPlayerNode` instances.
class SamplePlayer {

    // MARK: - Properties

    private let engine: AVAudioEngine
    private var buffers: [String: AVAudioPCMBuffer] = [:]
    private var playerNodes: [AVAudioPlayerNode] = []
    private let voiceCount = 16
    private var nextVoice = 0

    // MARK: - Initialisation

    init(engine: AVAudioEngine) {
        self.engine = engine
        loadSamples()
        createVoicePool()
    }

    // MARK: - Sample Loading

    /// Loads all WAV files from the bundle's Sounds directory into PCM buffers
    /// keyed by sample file name (e.g. "C4", "Fs5").
    private func loadSamples() {
        let sampleNames = [
            "C4", "Cs4", "D4", "Ds4", "E4", "F4", "Fs4", "G4", "Gs4",
            "A4", "As4", "B4",
            "C5", "Cs5", "D5", "Ds5", "E5", "F5", "Fs5", "G5", "Gs5",
            "A5", "As5", "B5",
            "C6", "Cs6", "D6", "Ds6", "E6"
        ]

        for name in sampleNames {
            guard let url = Bundle.main.url(forResource: name, withExtension: "wav") else {
                print("SamplePlayer: \(name).wav not found in bundle")
                continue
            }
            do {
                let audioFile = try AVAudioFile(forReading: url)
                let frameCount = AVAudioFrameCount(audioFile.length)
                guard let buffer = AVAudioPCMBuffer(
                    pcmFormat: audioFile.processingFormat,
                    frameCapacity: frameCount
                ) else {
                    print("SamplePlayer: could not create buffer for \(name)")
                    continue
                }
                try audioFile.read(into: buffer)
                buffers[name] = buffer
            } catch {
                print("SamplePlayer: failed to load \(name).wav — \(error)")
            }
        }
        print("SamplePlayer: loaded \(buffers.count) samples")
    }

    // MARK: - Voice Pool

    /// Creates a pool of player nodes and connects each to the engine's
    /// main mixer node.
    private func createVoicePool() {
        for _ in 0..<voiceCount {
            let node = AVAudioPlayerNode()
            engine.attach(node)
            // Use a common stereo format for connection; buffers will be
            // converted automatically if needed.
            engine.connect(node, to: engine.mainMixerNode,
                           format: nil)
            playerNodes.append(node)
        }
    }

    // MARK: - Playback

    /// Plays the sample corresponding to the given note using round-robin
    /// voice allocation.
    func play(note: NoteShape) {
        let fileName = note.sampleFileName
        guard let buffer = buffers[fileName] else {
            print("SamplePlayer: no buffer for \(fileName)")
            return
        }

        let node = playerNodes[nextVoice]
        nextVoice = (nextVoice + 1) % voiceCount

        node.stop()
        node.scheduleBuffer(buffer, at: nil, options: [], completionHandler: nil)
        node.play()
    }
}
