import SwiftUI
import AppKit

final class FloatingWindowManager {
    private var window: NSWindow?

    func show(offsetY: CGFloat = 0) {
        if window != nil { return }

        let contentView = ContentView()

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 280, height: 200),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )

        window.level = .floating
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.isMovableByWindowBackground = true
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.isReleasedWhenClosed = false

        // 居中显示在屏幕右上角; offsetY 向下偏移, 支持多个窗口错开
        if let screen = NSScreen.main {
            let screenFrame = screen.visibleFrame
            let x = screenFrame.maxX - 300
            let y = screenFrame.maxY - 250 - offsetY
            window.setFrameOrigin(NSPoint(x: x, y: y))
        }

        window.contentView = NSHostingView(rootView: contentView)
        window.makeKeyAndOrderFront(nil)

        self.window = window
    }

    func close() {
        window?.close()
        window = nil
    }
}
