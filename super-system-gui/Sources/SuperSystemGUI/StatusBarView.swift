import SwiftUI

struct StatusBarView: View {
    @Bindable var vm: AppViewModel

    var body: some View {
        HStack(spacing: 0) {
            statusIndicator
                .padding(.leading, 14)

            separator

            metricItem(icon: "arrow.triangle.2.circlepath", value: "\(vm.totalTurns)")

            separator

            metricItem(icon: "dollarsign.circle", value: String(format: "$%.4f", vm.totalCost))

            separator

            metricItem(icon: "clock", value: vm.formattedDuration)

            Spacer()

            if let sid = vm.currentSessionId {
                Text(sid.prefix(12))
                    .font(.caption2.monospaced())
                    .foregroundStyle(.quaternary)
                    .padding(.trailing, 14)
            }
        }
        .font(.caption2.monospaced())
        .foregroundStyle(.tertiary)
        .frame(height: 24)
        .frame(maxWidth: .infinity)
        .background(.bar)
    }

    @ViewBuilder
    private func metricItem(icon: String, value: String) -> some View {
        HStack(spacing: 3) {
            Image(systemName: icon)
                .font(.system(size: 8))
            Text(value)
        }
        .padding(.horizontal, 10)
    }

    private var separator: some View {
        Rectangle()
            .fill(.quaternary.opacity(0.5))
            .frame(width: 1, height: 10)
    }

    @ViewBuilder
    private var statusIndicator: some View {
        HStack(spacing: 5) {
            switch vm.sessionStatus {
            case .idle:
                Circle().fill(.secondary.opacity(0.4)).frame(width: 5, height: 5)
                Text("Ready").foregroundStyle(.secondary)
            case .running:
                ProgressView().controlSize(.mini)
                Text("Running").foregroundStyle(.blue)
            case .completed:
                Circle().fill(.green).frame(width: 5, height: 5)
                Text("Done").foregroundStyle(.green)
            case .failed:
                Circle().fill(.red).frame(width: 5, height: 5)
                Text("Failed").foregroundStyle(.red)
            case .interrupted:
                Circle().fill(.orange).frame(width: 5, height: 5)
                Text("Stopped").foregroundStyle(.orange)
            }
        }
        .padding(.trailing, 10)
    }
}
