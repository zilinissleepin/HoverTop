import XCTest
@testable import HoverTop

final class ModelTests: XCTestCase {
    func testDecodeFullData() throws {
        let json = """
        {
            "title": "系统状态",
            "subtitle": "实时",
            "items": [
                {"label": "CPU", "value": "23%", "color": "#4CAF50"},
                {"label": "内存", "value": "6GB"}
            ],
            "footer": "每5秒"
        }
        """.data(using: .utf8)!

        let data = try JSONDecoder().decode(DisplayData.self, from: json)
        XCTAssertEqual(data.title, "系统状态")
        XCTAssertEqual(data.items.count, 2)
        XCTAssertEqual(data.items[0].color, "#4CAF50")
        XCTAssertNil(data.items[1].color)
    }

    func testDecodeEmptyData() throws {
        let json = "{}".data(using: .utf8)!
        let data = try JSONDecoder().decode(DisplayData.self, from: json)
        XCTAssertNil(data.title)
        XCTAssertTrue(data.items.isEmpty)
    }
}
