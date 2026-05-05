import Foundation

struct DisplayItem: Codable, Identifiable {
    var id: String { label }
    let label: String
    let value: String
    let color: String?
}

struct DisplayData: Codable {
    let title: String?
    let subtitle: String?
    let items: [DisplayItem]
    let footer: String?

    enum CodingKeys: String, CodingKey {
        case title, subtitle, items, footer
    }

    init(title: String?, subtitle: String?, items: [DisplayItem], footer: String?) {
        self.title = title
        self.subtitle = subtitle
        self.items = items
        self.footer = footer
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        title = try container.decodeIfPresent(String.self, forKey: .title)
        subtitle = try container.decodeIfPresent(String.self, forKey: .subtitle)
        items = try container.decodeIfPresent([DisplayItem].self, forKey: .items) ?? []
        footer = try container.decodeIfPresent(String.self, forKey: .footer)
    }

    static let empty = DisplayData(title: nil, subtitle: nil, items: [], footer: nil)
}
