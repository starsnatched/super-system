import SwiftUI

struct ChatView: View {
    @Bindable var vm: AppViewModel
    @State private var promptText = ""
    @FocusState private var promptFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            if vm.entries.isEmpty && !vm.isSessionRunning {
                welcomeState
            } else {
                messageStream
            }

            inputArea
        }
        .onAppear {
            promptFocused = true
        }
    }

    private var welcomeState: some View {
        GeometryReader { geo in
            VStack(spacing: 0) {
                Spacer(minLength: geo.size.height * 0.15)

                VStack(spacing: 20) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 44, weight: .thin))
                        .foregroundStyle(
                            .linearGradient(
                                colors: [.blue.opacity(0.5), .purple.opacity(0.3)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )

                    VStack(spacing: 5) {
                        Text("Super System")
                            .font(.title2.weight(.semibold))
                        Text("Multi-agent engineering team")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                VStack(alignment: .leading, spacing: 12) {
                    HintRow(icon: "folder", text: "Set your project directory below")
                    HintRow(icon: "text.cursor", text: "Describe what you\u{2019}d like to build")
                    HintRow(icon: "eye", text: "Preview your frontend in realtime")
                }
                .fixedSize(horizontal: true, vertical: false)
                .padding(.top, 32)

                Spacer(minLength: 40)
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var messageStream: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(vm.entries) { entry in
                        MessageBubble(entry: entry)
                            .id(entry.id)
                    }

                    if vm.isSessionRunning {
                        HStack(spacing: 6) {
                            ProgressView()
                                .controlSize(.small)
                            Text("Working\u{2026}")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 20)
                        .padding(.vertical, 6)
                        .id("typing-indicator")
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 48)
            }
            .onChange(of: vm.entries.count) { _, _ in
                if let last = vm.entries.last {
                    withAnimation(.easeOut(duration: 0.15)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    private var inputArea: some View {
        VStack(spacing: 0) {
            HStack(spacing: 6) {
                Button {
                    vm.chooseWorkingDirectory()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "folder.fill")
                            .font(.system(size: 9))
                        Text(vm.workingDirectoryName)
                            .font(.caption2.monospaced())
                            .lineLimit(1)
                    }
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .glassEffect(in: .capsule)
                }
                .buttonStyle(.plain)
                .help(vm.workingDirectoryDisplay)

                Spacer()

                if vm.isSessionRunning {
                    Button("Stop", systemImage: "stop.fill") {
                        vm.interruptSession()
                    }
                    .labelStyle(.titleAndIcon)
                    .font(.caption2)
                    .foregroundStyle(.red)
                    .buttonStyle(.glass)
                    .help("Interrupt session")
                }
            }
            .padding(.horizontal, 18)
            .padding(.top, 8)
            .padding(.bottom, 6)

            HStack(alignment: .bottom, spacing: 0) {
                TextField("What would you like to build?", text: $promptText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(.body)
                    .lineLimit(1...6)
                    .focused($promptFocused)
                    .onSubmit {
                        if NSEvent.modifierFlags.contains(.shift) { return }
                        sendPrompt()
                    }
                    .padding(.leading, 14)
                    .padding(.trailing, 8)
                    .padding(.vertical, 10)

                Button {
                    sendPrompt()
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 24))
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(canSend ? Color.accentColor : Color.secondary.opacity(0.4))
                }
                .buttonStyle(.plain)
                .disabled(!canSend)
                .help("Send")
                .padding(.trailing, 10)
                .padding(.bottom, 8)
            }
            .glassEffect(in: .rect(cornerRadius: 14))
            .padding(.horizontal, 16)
            .padding(.bottom, 32)
        }
    }

    private var canSend: Bool {
        !promptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !vm.isSessionRunning
    }

    private func sendPrompt() {
        let text = promptText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !vm.isSessionRunning else { return }
        promptText = ""
        vm.startSession(prompt: text)
    }
}

private struct HintRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundStyle(.tertiary)
                .frame(width: 18, alignment: .center)
            Text(text)
                .font(.subheadline)
                .foregroundStyle(.tertiary)
        }
    }
}
