import XCTest

// Release-only XCTest fixture. Never signs in, presents a purchase or changes sales.
final class NativeAccountReleaseTests: XCTestCase {
    func testGuestAccountAndChatNavigation() throws {
        let app = XCUIApplication()
        app.launch()
        defer { app.terminate() }
        let input = app.descendants(matching: .any)["chat-message-input"].firstMatch
        XCTAssertTrue(input.waitForExistence(timeout: 20))
        XCTAssertTrue(input.isHittable)
        XCTAssertGreaterThan(input.frame.height, 20)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(input.frame))
        XCTAssertLessThanOrEqual(input.frame.maxY, app.buttons["Create"].frame.minY)
        let initial = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        initial.name = "Initial guest chat visible composer"
        initial.lifetime = .keepAlways
        add(initial)
        input.tap()
        input.typeText("A friendly sticker idea")
        XCTAssertTrue(app.buttons["Send message"].isEnabled)
        XCTAssertTrue(app.buttons["Send message"].isHittable)
        XCTAssertTrue(input.isHittable)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(input.frame))
        #if os(iOS)
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5))
        XCTAssertLessThanOrEqual(input.frame.maxY, app.keyboards.firstMatch.frame.minY)
        #endif
        let keyboard = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        keyboard.name = "Guest composer with keyboard - unsent"
        keyboard.lifetime = .keepAlways
        add(keyboard)
        // Discard the draft, never submit a live chat request.
        app.buttons["New chat"].tap()
        XCTAssertTrue(app.buttons["Account"].waitForExistence(timeout: 20))
        app.buttons["Account"].tap()
        XCTAssertTrue(app.buttons["Sign in"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["Manage App Store subscriptions"].exists)
        XCTAssertFalse(app.buttons["Subscribe"].exists)
        XCTAssertEqual(app.webViews.count, 0)
        let account = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        account.name = "Native Account guest"
        account.lifetime = .keepAlways
        add(account)
        // Sign in now opens the provider directly; never initiate authentication in this smoke.
        app.buttons["Create"].tap()
        XCTAssertTrue(app.buttons["Send message"].waitForExistence(timeout: 15))
        XCTAssertTrue(input.isHittable)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(input.frame))
        XCTAssertFalse(app.buttons["Sign in"].exists)
        XCTAssertFalse(app.buttons["Continue with LazyingArt"].exists)
        XCTAssertFalse(app.buttons["Characters"].exists)
        let signIn = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        signIn.name = "Guest chat without login"
        signIn.lifetime = .keepAlways
        add(signIn)
        input.tap()
        input.typeText("Another unsent idea")
        XCTAssertTrue(app.buttons["Send message"].isEnabled)
        XCTAssertTrue(app.buttons["Send message"].isHittable)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(input.frame))
        let returned = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        returned.name = "Guest composer after Account return - unsent"
        returned.lifetime = .keepAlways
        add(returned)
    }
}
