import SwiftUI

@main
struct SuperSystemGUIApp: App {
    @State private var vm = AppViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView(vm: vm)
                .onAppear {
                    vm.startBackend()
                }
                .onDisappear {
                    vm.stopBackend()
                }
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified(showsTitle: false))
        .defaultSize(width: 1280, height: 800)
        .commands {
            CommandGroup(after: .newItem) {
                Button("New Session") {
                    vm.resetForNewSession()
                }
                .keyboardShortcut("n", modifiers: .command)

                Button("Change Working Directory\u{2026}") {
                    vm.chooseWorkingDirectory()
                }
                .keyboardShortcut("o", modifiers: [.command, .shift])

                Divider()

                Button("Interrupt Session") {
                    vm.interruptSession()
                }
                .keyboardShortcut(".", modifiers: .command)
                .disabled(!vm.isSessionRunning)
            }

            CommandGroup(replacing: .help) {
                Button("Refresh Sessions") {
                    vm.fetchSessions()
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])
            }
        }
    }
}
