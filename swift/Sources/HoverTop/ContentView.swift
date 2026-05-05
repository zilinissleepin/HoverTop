import SwiftUI

struct ContentView: View {
    @StateObject private var state = DisplayState.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 标题区
            if let title = state.data.title {
                Text(title)
                    .font(.headline)
                    .foregroundColor(.primary)
            }
            if let subtitle = state.data.subtitle {
                Text(subtitle)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // 分隔线
            if state.data.title != nil && !state.data.items.isEmpty {
                Divider()
            }

            // 数据项
            ForEach(state.data.items) { item in
                HStack {
                    Text(item.label)
                        .font(.body)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(item.value)
                        .font(.body.monospaced())
                        .foregroundColor(colorFromHex(item.color))
                }
            }

            // 底部
            if let footer = state.data.footer {
                Divider()
                Text(footer)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(16)
        .frame(width: 260)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func colorFromHex(_ hex: String?) -> Color {
        guard let hex = hex else { return .primary }
        let cleaned = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        guard cleaned.count == 6,
              let val = UInt64(cleaned, radix: 16) else { return .primary }
        let r = Double((val >> 16) & 0xFF) / 255
        let g = Double((val >> 8) & 0xFF) / 255
        let b = Double(val & 0xFF) / 255
        return Color(red: r, green: g, blue: b)
    }
}
