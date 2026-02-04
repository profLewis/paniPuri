import SwiftUI
import AVFoundation

@main
struct PaniPuriApp: App {
    init() {
        // Configure audio session for low-latency playback
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
        try? session.setPreferredIOBufferDuration(0.005) // 5ms for low latency
        try? session.setActive(true)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
