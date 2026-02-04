import SwiftUI

struct ContentView: View {
    @StateObject var audioEngine = AudioEngine()

    /// Note shapes loaded from the bundled JSON at launch.
    @State private var noteShapes: [NoteShape] = NoteShape.loadAll()

    var body: some View {
        ZStack {
            // Dark gradient background
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(red: 0.102, green: 0.102, blue: 0.102), // #1a1a1a
                    Color(red: 0.176, green: 0.176, blue: 0.176)  // #2d2d2d
                ]),
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 12) {
                // Title with silver-white gradient text
                Text("PaniPuri")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [
                                Color(red: 0.85, green: 0.85, blue: 0.88),
                                Color.white,
                                Color(red: 0.78, green: 0.78, blue: 0.82)
                            ],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .padding(.top, 8)

                // Subtitle
                Text("Interactive Steel Pan")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6))

                // Steel pan view filling available space with 1:1 aspect ratio
                SteelPanView(
                    noteShapes: noteShapes,
                    activeNotes: audioEngine.activeNotes,
                    onNotePlayed: { noteShape in
                        audioEngine.playNote(noteShape)
                    }
                )
                .aspectRatio(1, contentMode: .fit)
                .padding(.horizontal, 8)

                // Controls below the pan
                ControlsView(audioEngine: audioEngine)
                    .padding(.horizontal, 16)
                    .padding(.bottom, 8)
            }
        }
        .preferredColorScheme(.dark)
    }
}

#Preview {
    ContentView()
}
