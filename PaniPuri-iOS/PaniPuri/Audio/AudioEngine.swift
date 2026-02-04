import Foundation
import AVFoundation
import Combine

enum AudioMode: String, CaseIterable {
    case samples = "Samples"
    case synth = "Synth"
}

class AudioEngine: ObservableObject {
    let engine = AVAudioEngine()

    @Published var audioMode: AudioMode = .samples
    @Published var volume: Float = 0.35
    @Published var activeNotes: Set<String> = []
    @Published var lastPlayedNote: String = ""

    private var samplePlayer: SamplePlayer!
    private var synthPlayer: SynthPlayer!

    init() {
        samplePlayer = SamplePlayer(engine: engine)
        synthPlayer = SynthPlayer(engine: engine)

        engine.mainMixerNode.outputVolume = volume
        try? engine.start()
    }

    func playNote(_ note: NoteShape) {
        let noteId = note.idx
        lastPlayedNote = "\(note.name)\(note.octave)"
        activeNotes.insert(noteId)

        switch audioMode {
        case .samples:
            samplePlayer.play(note: note)
        case .synth:
            synthPlayer.play(note: note)
        }

        // Remove highlight after 300ms
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
            self?.activeNotes.remove(noteId)
        }
    }

    func updateVolume() {
        engine.mainMixerNode.outputVolume = volume
    }
}
