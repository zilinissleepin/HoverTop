import SwiftUI

struct ContentView: View {
    @StateObject private var state = DisplayState.shared

    /// 列宽配置 (与 Python 端约定)
    /// label | price | change | holding
    private let labelWidth: CGFloat = 78
    private let priceWidth: CGFloat = 92
    private let changeWidth: CGFloat = 68
    private let holdingWidth: CGFloat = 100

    private var totalRowWidth: CGFloat {
        labelWidth + priceWidth + changeWidth + holdingWidth
    }

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
                rowView(for: item)
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
        .frame(width: totalRowWidth + 32)  // 内容宽度 + 左右 padding
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func rowView(for item: DisplayItem) -> some View {
        let color = colorFromHex(item.color)
        if let cells = item.cells, cells.count >= 3 {
            // 多列模式: label | price | change | holding
            HStack(spacing: 0) {
                Text(item.label)
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(.secondary)
                    .frame(width: labelWidth, alignment: .leading)
                Text(cells[0])
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(color)
                    .frame(width: priceWidth, alignment: .trailing)
                Text(cells[1])
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(color)
                    .frame(width: changeWidth, alignment: .trailing)
                Text(cells[2])
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(color)
                    .frame(width: holdingWidth, alignment: .trailing)
            }
        } else {
            // 兼容: label + value 两列模式
            HStack(spacing: 0) {
                Text(item.label)
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(.secondary)
                    .frame(width: labelWidth, alignment: .leading)
                Text(item.value)
                    .font(.system(.body, design: .monospaced))
                    .foregroundColor(color)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
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
