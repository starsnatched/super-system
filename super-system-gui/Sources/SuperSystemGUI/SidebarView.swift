import SwiftUI

struct SidebarView: View {
    @Bindable var vm: AppViewModel
    @State private var selection: String?

    var body: some View {
        List(selection: $selection) {
            ForEach(vm.sessions) { session in
                SessionRowLabel(
                    session: session,
                    isActive: vm.currentSessionId == session.sessionId
                )
                .tag(session.sessionId)
            }
        }
        .listStyle(.sidebar)
        .safeAreaInset(edge: .top, spacing: 0) {
            sidebarHeader
        }
        .overlay {
            if vm.sessions.isEmpty {
                emptyState
            }
        }
        .onChange(of: selection) { _, newValue in
            guard let sessionId = newValue,
                  !vm.isSessionRunning,
                  sessionId != vm.currentSessionId
            else { return }
            vm.resumeSession(sessionId: sessionId, prompt: "")
        }
        .onChange(of: vm.currentSessionId) { _, newValue in
            selection = newValue
        }
    }

    private var sidebarHeader: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(vm.ws.isConnected ? Color.green : Color.red.opacity(0.7))
                .frame(width: 7, height: 7)

            Text("Super System")
                .font(.headline)

            Spacer()

            Button("New Session", systemImage: "square.and.pencil") {
                vm.resetForNewSession()
            }
            .labelStyle(.iconOnly)
            .buttonStyle(.borderless)
            .help("New Session")
            .disabled(vm.isSessionRunning)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.bar)
    }

    private var emptyState: some View {
        VStack(spacing: 6) {
            Text("No sessions yet")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
            Text("Enter a prompt to start")
                .font(.caption)
                .foregroundStyle(.quaternary)
        }
    }
}

private struct SessionRowLabel: View {
    let session: SessionInfo
    let isActive: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(session.promptPreview.isEmpty ? "Untitled" : String(session.promptPreview.prefix(50)))
                .font(.subheadline.weight(isActive ? .medium : .regular))
                .lineLimit(2)

            HStack(spacing: 0) {
                Circle()
                    .fill(statusColor)
                    .frame(width: 5, height: 5)

                Text(statusLabel)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .padding(.leading, 4)

                Text(session.startedDate, style: .relative)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .padding(.leading, 8)

                Spacer(minLength: 4)

                if session.costUsd > 0 {
                    Text(String(format: "$%.2f", session.costUsd))
                        .font(.caption2.monospaced())
                        .foregroundStyle(.quaternary)
                }
            }
        }
    }

    private var statusLabel: String {
        switch session.status {
        case "completed": return "Done"
        case "running": return "Running"
        case "failed": return "Failed"
        case "interrupted": return "Stopped"
        default: return session.status.capitalized
        }
    }

    private var statusColor: Color {
        switch session.status {
        case "completed": return .green
        case "running": return .blue
        case "failed": return .red
        case "interrupted": return .orange
        default: return .secondary
        }
    }
}
