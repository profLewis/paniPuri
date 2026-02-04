import SwiftUI

struct ControlsView: View {
    @ObservedObject var audioEngine: AudioEngine

    var body: some View {
        VStack(spacing: 14) {
            // Synth / Samples mode picker
            Picker("Audio Mode", selection: $audioEngine.audioMode) {
                Text("Samples").tag(AudioMode.samples)
                Text("Synth").tag(AudioMode.synth)
            }
            .pickerStyle(.segmented)

            // Volume slider
            HStack(spacing: 10) {
                Image(systemName: "speaker.fill")
                    .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6))
                    .font(.system(size: 14))

                Slider(
                    value: Binding<Double>(
                        get: { Double(audioEngine.volume) },
                        set: { audioEngine.volume = Float($0) }
                    ),
                    in: 0...1
                )
                .tint(Color(red: 0.6, green: 0.6, blue: 0.6))

                Image(systemName: "speaker.wave.3.fill")
                    .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6))
                    .font(.system(size: 14))
            }

            // Ring legend
            HStack(spacing: 16) {
                legendItem(
                    color: Color(red: 0.753, green: 0.224, blue: 0.169),
                    label: "Outer (Oct 4)"
                )
                legendItem(
                    color: Color(red: 0.141, green: 0.443, blue: 0.639),
                    label: "Central (Oct 5)"
                )
                legendItem(
                    color: Color(red: 0.118, green: 0.518, blue: 0.286),
                    label: "Inner (Oct 6)"
                )
            }
            .font(.system(size: 12))

            // Now playing indicator
            if !audioEngine.lastPlayedNote.isEmpty {
                HStack(spacing: 6) {
                    Text("Now playing:")
                        .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6))
                        .font(.system(size: 14))

                    Text(audioEngine.lastPlayedNote)
                        .foregroundColor(Color(red: 1.0, green: 0.843, blue: 0.0)) // #FFD700
                        .font(.system(size: 16, weight: .bold))
                }
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(red: 0.13, green: 0.13, blue: 0.13).opacity(0.9))
        )
    }

    // MARK: - Legend Item

    private func legendItem(color: Color, label: String) -> some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 10, height: 10)
            Text(label)
                .foregroundColor(Color(red: 0.7, green: 0.7, blue: 0.7))
        }
    }
}

#Preview {
    ControlsView(audioEngine: AudioEngine())
        .padding()
        .background(Color.black)
}
