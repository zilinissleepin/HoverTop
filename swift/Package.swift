// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "HoverTop",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "HoverTop",
            path: "Sources/HoverTop"
        ),
        .testTarget(
            name: "HoverTopTests",
            dependencies: ["HoverTop"],
            path: "Tests/HoverTopTests"
        ),
    ]
)
