import SwiftUI

final class DisplayState: ObservableObject {
    static let shared = DisplayState()
    @Published var data: DisplayData = .empty
}
