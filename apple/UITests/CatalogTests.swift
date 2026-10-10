import XCTest

final class CatalogTests: XCTestCase {
    func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
    func testNativeCatalogAndSharing() throws {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 20))
        XCTAssertEqual(app.webViews.count, 0, "The mobile/desktop catalog must be native")
        let preview = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Preview ")).firstMatch
        XCTAssertTrue(preview.waitForExistence(timeout: 20))
        capture("Native catalog")
        preview.tap()
        let save = app.buttons["Save GIF"]
        XCTAssertTrue(save.waitForExistence(timeout: 10))
        capture("Native preview")
        save.tap()
        #if os(macOS)
        XCTAssertTrue(app.dialogs.firstMatch.waitForExistence(timeout: 35))
        capture("Native save panel")
        app.buttons["Cancel"].firstMatch.tap()
        #else
        let share = app.otherElements["ActivityListView"]
        XCTAssertTrue(share.waitForExistence(timeout: 60), app.debugDescription)
        capture("Native share sheet")
        #endif
        app.terminate()
    }
}
