import SwiftUI
import AppKit

final class FloatingWindowManager {
    private var window: NSWindow?
    private var expandedFrameBeforeCollapse: NSRect?
    private let collapsedWindowHeight: CGFloat = 44

    func show(offsetY: CGFloat = 0) {
        if window != nil { return }

        let contentView = ContentView(
            onClose: { [weak self] in
                self?.close()
                NSApp.terminate(nil)
            },
            onCollapseChange: { [weak self] isCollapsed in
                self?.setCollapsed(isCollapsed)
            }
        )

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
        expandedFrameBeforeCollapse = nil
    }

    private func setCollapsed(_ isCollapsed: Bool) {
        guard let window = window else { return }

        if isCollapsed {
            let currentFrame = window.frame
            expandedFrameBeforeCollapse = currentFrame

            var collapsedFrame = currentFrame
            collapsedFrame.size.height = collapsedWindowHeight
            collapsedFrame.origin.y = currentFrame.maxY - collapsedWindowHeight
            window.setFrame(collapsedFrame, display: true, animate: true)
        } else if let expandedFrame = expandedFrameBeforeCollapse {
            window.setFrame(expandedFrame, display: true, animate: true)
            expandedFrameBeforeCollapse = nil
        }
    }
}
