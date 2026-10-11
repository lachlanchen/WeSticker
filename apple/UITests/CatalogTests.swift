import XCTest

final class CatalogTests: XCTestCase {
    func testGIFPlaybackPauseAndResume() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-studio-origin", "https://westicker.lazying.art"]
        app.launch()
        defer { app.terminate() }
        app.buttons["Stickers"].tap()
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
        app.launchArguments += ["-studio-origin", "https://westicker.lazying.art"]
        app.launch()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 20))
        app.assertCompactHeader("WeSticker", action: "About this beta")
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
        app.launchArguments += ["-studio-origin", "https://westicker.lazying.art"]
        app.launch()
        defer { app.terminate() }
        XCTAssertTrue(app.buttons["Create"].waitForExistence(timeout: 20))
        app.buttons["Create"].tap()
        XCTAssertTrue(app.buttons["Continue with LazyingArt"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.staticTexts["Sign in to WeSticker"].exists)
        app.assertCompactHeader("Sign in", action: "Service settings")
        XCTAssertFalse(app.descendants(matching: .any)["chat-message-input"].exists)
        XCTAssertFalse(app.buttons["Send message"].exists)
        XCTAssertFalse(app.buttons["Characters"].exists)
        app.buttons["Service settings"].tap()
        XCTAssertTrue(app.textFields["HTTPS creator service"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.webViews.count, 0)
        XCTAssertFalse(app.buttons["Agent"].exists)
        app.buttons["Done"].tap()
        XCTAssertFalse(app.buttons["Library"].isHittable)
        capture("Shared authentication from Create")
        XCTAssertTrue(app.buttons["Browse stickers"].isHittable)
        app.buttons["Browse stickers"].tap()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 10))
        app.buttons["Library"].tap()
        XCTAssertTrue(app.staticTexts["Sign in to WeSticker"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["Characters"].exists)
        XCTAssertTrue(app.buttons["Open saved local photo draft"].waitForExistence(timeout: 10))
        app.buttons["Open saved local photo draft"].tap()
        XCTAssertTrue(app.textFields["Character name"].waitForExistence(timeout: 10))
        app.assertCompactHeader("Create", action: "Close local draft")
        let character = app.textFields["Character name"]
        character.tap()
        let old = character.value as? String ?? ""
        character.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: old.count) + "QA character")
        XCTAssertTrue(app.textFields["Caption 1"].waitForExistence(timeout: 10))
        let caption = app.textFields["Caption 1"].value as? String
        capture("Native preserved local draft")
        app.terminate()
        app.launch()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 20))
        app.buttons["Library"].tap()
        XCTAssertTrue(app.buttons["Open saved local photo draft"].waitForExistence(timeout: 10))
        app.buttons["Open saved local photo draft"].tap()
        XCTAssertTrue(app.textFields["Caption 1"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.textFields["Character name"].value as? String, "QA character")
        XCTAssertEqual(app.textFields["Caption 1"].value as? String, caption)
        capture("Native restored draft")
        app.buttons["Close local draft"].tap()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 10))
    }
}

extension XCUIApplication {
    func assertCompactHeader(_ title: String, action: String? = nil,
                             file: StaticString = #filePath, line: UInt = #line) {
        let heading = staticTexts.matching(identifier: "studio-toolbar-title")
        XCTAssertTrue(heading.firstMatch.waitForExistence(timeout: 10), file: file, line: line)
        let visible = heading.allElementsBoundByIndex.filter { $0.isHittable }
        XCTAssertEqual(visible.count, 1, "One visible toolbar title", file: file, line: line)
        guard let label = visible.first else { return }
        let window = windows.firstMatch.frame
        XCTAssertEqual(label.label, title, file: file, line: line)
        XCTAssertGreaterThan(label.frame.width, 0, file: file, line: line)
        XCTAssertLessThanOrEqual(label.frame.height, 44, file: file, line: line)
        XCTAssertTrue(window.contains(label.frame), file: file, line: line)
        #if os(macOS)
        // The native window controls precede the leading toolbar item.
        XCTAssertLessThan(label.frame.minX - window.minX, 160, file: file, line: line)
        #else
        XCTAssertLessThan(label.frame.minX - window.minX, 80, file: file, line: line)
        #endif
        XCTAssertLessThan(label.frame.maxY - window.minY, 120, file: file, line: line)
        if let action {
            let button = buttons[action]
            XCTAssertTrue(button.isHittable, file: file, line: line)
            XCTAssertLessThan(abs(label.frame.midY - button.frame.midY), 14, file: file, line: line)
            XCTAssertLessThanOrEqual(label.frame.maxX, button.frame.minX, file: file, line: line)
        }
    }
}
