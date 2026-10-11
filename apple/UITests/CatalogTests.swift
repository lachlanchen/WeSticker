import XCTest

final class CatalogTests: XCTestCase {
    func testGIFPlaybackPauseAndResume() throws {
        let app = XCUIApplication()
        app.launch()
        defer { app.terminate() }
        let sticker = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Preview ")).firstMatch
        XCTAssertTrue(sticker.waitForExistence(timeout: 20))
        if app.buttons["Play animations"].exists { app.buttons["Play animations"].tap() }
        func samples(_ name: String, attempts: Int) -> Int {
            var frames = Set<Data>()
            for index in 0..<attempts {
                Thread.sleep(forTimeInterval: 0.37)
                let shot = sticker.screenshot()
                frames.insert(shot.pngRepresentation)
                if index < 3 {
                    let attachment = XCTAttachment(screenshot: shot)
                    attachment.name = "\(name)-\(index)"
                    attachment.lifetime = .keepAlways
                    add(attachment)
                }
            }
            return frames.count
        }
        // Allow a slow first network fetch, but require changed sticker pixels.
        var moving = false
        for _ in 0..<6 {
            if samples("Playing", attempts: 4) > 1 { moving = true; break }
            Thread.sleep(forTimeInterval: 4)
        }
        XCTAssertTrue(moving, "GIF pixels never changed in the catalog")
        app.buttons["Pause animations"].tap()
        Thread.sleep(forTimeInterval: 1)
        XCTAssertEqual(samples("Paused", attempts: 4), 1)
        app.buttons["Play animations"].tap()
        Thread.sleep(forTimeInterval: 1)
        XCTAssertGreaterThan(samples("Resumed", attempts: 5), 1)
        capture("Animated catalog")
    }
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
    func testUnifiedCreatorAndLocalDraftPersistence() throws {
        let app = XCUIApplication()
        app.launch()
        defer { app.terminate() }
        XCTAssertTrue(app.buttons["Create"].waitForExistence(timeout: 20))
        app.buttons["Create"].tap()
        XCTAssertTrue(app.textFields["HTTPS creator service"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.webViews.count, 0)
        XCTAssertFalse(app.buttons["Agent"].exists)
        XCTAssertTrue(app.buttons["Library"].exists)
        XCTAssertTrue(app.buttons["Characters"].exists)
        capture("Native unified creator")
        app.buttons["Open saved local photo draft"].tap()
        XCTAssertTrue(app.textFields["Character name"].waitForExistence(timeout: 10))
        let character = app.textFields["Character name"]
        character.tap()
        let old = character.value as? String ?? ""
        character.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: old.count) + "QA character")
        XCTAssertTrue(app.textFields["Caption 1"].waitForExistence(timeout: 10))
        let caption = app.textFields["Caption 1"].value as? String
        capture("Native preserved local draft")
        app.terminate()
        app.launch()
        app.buttons["Create"].tap()
        app.buttons["Open saved local photo draft"].tap()
        XCTAssertTrue(app.textFields["Caption 1"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.textFields["Character name"].value as? String, "QA character")
        XCTAssertEqual(app.textFields["Caption 1"].value as? String, caption)
        capture("Native restored draft")
    }
}
