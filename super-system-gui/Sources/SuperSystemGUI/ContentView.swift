import SwiftUI

struct ContentView: View {
    @Bindable var vm: AppViewModel
    @State private var showPreview = true
    @State private var columnVisibility: NavigationSplitViewVisibility = .automatic

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView(vm: vm)
                .navigationSplitViewColumnWidth(min: 220, ideal: 260, max: 300)
        } detail: {
            HSplitView {
                ChatView(vm: vm)
                    .frame(minWidth: 420)

                if showPreview {
                    PreviewPanel(urlString: $vm.previewURL)
                        .frame(minWidth: 340)
                }
            }
            .overlay(alignment: .bottom) {
                StatusBarView(vm: vm)
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("Preview", systemImage: showPreview
                       ? "rectangle.righthalf.inset.filled"
                       : "rectangle.righthalf.inset.filled.arrow.right") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        showPreview.toggle()
                    }
                }
                .help(showPreview ? "Hide Preview" : "Show Preview")
            }
        }
        .frame(minWidth: 960, minHeight: 640)
    }
}
