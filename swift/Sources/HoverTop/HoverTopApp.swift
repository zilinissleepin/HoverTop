import SwiftUI
import AppKit

@main
struct HoverTopApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // 不使用默认窗口，由 AppDelegate 管理
        Settings { EmptyView() }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private let windowManager = FloatingWindowManager()
    private var webSocketClient: WebSocketClient?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let port = parsePort()
        let offsetY = parseOffsetY()
        // 隐藏 dock 图标
        NSApp.setActivationPolicy(.accessory)
        // 显示悬浮窗
        windowManager.show(offsetY: offsetY)
        // 连接 WebSocket
        webSocketClient = WebSocketClient(port: port)
        webSocketClient?.connect()
    }

    func applicationWillTerminate(_ notification: Notification) {
        webSocketClient?.disconnect()
        windowManager.close()
    }

    private func parsePort() -> Int {
        let args = CommandLine.arguments
        if let idx = args.firstIndex(of: "--port"), idx + 1 < args.count {
            return Int(args[idx + 1]) ?? 9527
        }
        return 9527
    }

    private func parseOffsetY() -> CGFloat {
        let args = CommandLine.arguments
        if let idx = args.firstIndex(of: "--offset-y"), idx + 1 < args.count {
            return CGFloat(Double(args[idx + 1]) ?? 0)
        }
        return 0
    }
}
