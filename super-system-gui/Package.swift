// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "SuperSystemGUI",
    platforms: [.macOS(.v26)],
    targets: [
        .executableTarget(
            name: "SuperSystemGUI",
            path: "Sources/SuperSystemGUI",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
