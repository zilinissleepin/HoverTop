import Foundation

final class WebSocketClient {
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private let port: Int
    private var reconnectDelay: TimeInterval = 1.0
    private var isConnected = false

    init(port: Int) {
        self.port = port
    }

    func connect() {
        let url = URL(string: "ws://localhost:\(port)")!
        session = URLSession(configuration: .default)
        task = session?.webSocketTask(with: url)
        task?.resume()
        listen()
        isConnected = true
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        isConnected = false
    }

    private func listen() {
        task?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.handleMessage(text)
                default:
                    break
                }
                self.reconnectDelay = 1.0
                self.listen()
            case .failure:
                self.isConnected = false
                self.scheduleReconnect()
            }
        }
    }

    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        do {
            let decoded = try JSONDecoder().decode(DisplayData.self, from: data)
            DispatchQueue.main.async {
                DisplayState.shared.data = decoded
            }
        } catch {
            print("Decode error: \(error)")
        }
    }

    private func scheduleReconnect() {
        DispatchQueue.global().asyncAfter(deadline: .now() + reconnectDelay) { [weak self] in
            self?.connect()
        }
        reconnectDelay = min(reconnectDelay * 2, 30.0)
    }
}
