import SwiftUI

struct MessageBubble: View {
    let entry: ChatEntry

    var body: some View {
        Group {
            switch entry {
            case .text(_, let content, _):
                textBubble(content)

            case .agentDispatch(_, let agent, let desc, let ts):
                agentBubble(agent: agent, description: desc, timestamp: ts)

            case .result(_, let turns, let cost, let durationMs, let isError, let errorText):
                resultBubble(turns: turns, cost: cost, durationMs: durationMs, isError: isError, errorText: errorText)

            case .error(_, let message, _):
                errorBubble(message)

            case .status(_, let message, _):
                statusBubble(message)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func textBubble(_ content: String) -> some View {
        let parsed = parseMarkdown(content)
        HStack(alignment: .top, spacing: 0) {
            RoundedRectangle(cornerRadius: 1)
                .fill(.secondary.opacity(0.2))
                .frame(width: 2)
                .padding(.vertical, 2)

            Text(parsed)
                .textSelection(.enabled)
                .font(.body)
                .lineSpacing(4)
                .padding(.leading, 12)
                .padding(.vertical, 2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func agentBubble(agent: String, description: String, timestamp: Date) -> some View {
        let meta = AgentMeta.find(agent)
        let color = agentColor(meta)

        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)

            Text(agent)
                .font(.caption.weight(.medium))
                .foregroundStyle(color)

            if !description.isEmpty {
                Text(description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 4)

            Text(timestamp, style: .time)
                .font(.caption2.monospaced())
                .foregroundStyle(.quaternary)
        }
        .padding(.vertical, 3)
    }

    @ViewBuilder
    private func resultBubble(turns: Int, cost: Double, durationMs: Int, isError: Bool, errorText: String) -> some View {
        let accent: Color = isError ? .red : .green

        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: isError ? "xmark.circle.fill" : "checkmark.circle.fill")
                    .font(.system(size: 13))
                Text(isError ? "Session failed" : "Session complete")
                    .font(.callout.weight(.medium))
            }
            .foregroundStyle(accent)

            HStack(spacing: 20) {
                metricLabel("Turns", value: "\(turns)")
                metricLabel("Cost", value: String(format: "$%.4f", cost))
                metricLabel("Time", value: formatDuration(durationMs))
            }

            if isError && !errorText.isEmpty {
                Text(errorText)
                    .font(.caption.monospaced())
                    .foregroundStyle(.red.opacity(0.8))
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.red.opacity(0.06), in: RoundedRectangle(cornerRadius: 6))
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassEffect(.regular.tint(accent), in: .rect(cornerRadius: 10))
    }

    @ViewBuilder
    private func errorBubble(_ message: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 11))
                .foregroundStyle(.red.opacity(0.8))
                .padding(.top, 1)
            Text(message)
                .font(.caption)
                .foregroundStyle(.red.opacity(0.85))
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.red.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
    }

    @ViewBuilder
    private func statusBubble(_ message: String) -> some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.tertiary)
            .padding(.vertical, 3)
    }

    @ViewBuilder
    private func metricLabel(_ label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.caption.monospaced().weight(.medium))
        }
    }

    private func agentColor(_ meta: AgentMeta?) -> Color {
        guard let meta else { return .secondary }
        return Color(hue: meta.hue / 360, saturation: 0.55, brightness: 0.8)
    }

    private func formatDuration(_ ms: Int) -> String {
        let totalSec = ms / 1000
        let mins = totalSec / 60
        let secs = totalSec % 60
        return String(format: "%d:%02d", mins, secs)
    }

    private func parseMarkdown(_ text: String) -> AttributedString {
        (try? AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
            ?? AttributedString(text)
    }
}
