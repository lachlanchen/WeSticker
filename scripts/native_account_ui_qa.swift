import XCTest

// Release-only tests. Local fixture responses are layout evidence, not OAuth proof.
final class NativeAccountReleaseTests: XCTestCase {
    private let publicOrigin = "https://westicker.lazying.art"
    private let fixtureOrigin = "http://127.0.0.1:18649"

    private func capture(_ name: String) {
        let shot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        shot.name = name; shot.lifetime = .keepAlways; add(shot)
    }
    private func fixtureState(_ value: String) {
        let completed = expectation(description: "Local fixture state")
        URLSession.shared.dataTask(with: URL(string: fixtureOrigin + "/__qa/" + value)!) { _, response, error in
            XCTAssertNil(error)
            XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
            completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 5)
    }
    private func refreshFromLogin(_ app: XCUIApplication) {
        let settings = app.buttons["Service settings"]
        let enabled = NSPredicate(format: "exists == true AND hittable == true AND enabled == true")
        expectation(for: enabled, evaluatedWith: settings)
        waitForExpectations(timeout: 10)
        settings.tap()
        app.buttons["Done"].tap()
    }
    private func publicProviders() -> [String] {
        let completed = expectation(description: "Public configured providers")
        var providers: [String] = []
        URLSession.shared.dataTask(with: URL(string: publicOrigin + "/api/bootstrap")!) { data, response, error in
            XCTAssertNil(error)
            XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
            if let data, let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                providers = body["providers"] as? [String] ?? []
            }
            completed.fulfill()
        }.resume()
        wait(for: [completed], timeout: 20)
        return providers
    }
    private func assertComposer(_ app: XCUIApplication) -> XCUIElement {
        let input = app.descendants(matching: .any)["chat-message-input"].firstMatch
        XCTAssertTrue(input.waitForExistence(timeout: 15))
        XCTAssertTrue(input.isHittable)
        XCTAssertGreaterThan(input.frame.height, 20)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(input.frame))
        XCTAssertLessThanOrEqual(input.frame.maxY, app.buttons["Create"].frame.minY)
        XCTAssertFalse(app.buttons["Continue with LazyingArt"].exists)
        XCTAssertFalse(app.buttons["Manage App Store subscriptions"].exists)
        app.assertCompactHeader("Create", action: "Service settings")
        return input
    }

    func testAuthenticatedFixtureComposerKeyboardTabReturnAndExpiry() throws {
        fixtureState("authenticated")
        let app = XCUIApplication()
        app.launchArguments += ["-studio-origin", fixtureOrigin]
        app.launch()
        defer { app.terminate() }
        app.buttons["Create"].tap()
        let input = assertComposer(app)
        let welcome = app.staticTexts["What shall we make?"]
        XCTAssertTrue(welcome.waitForExistence(timeout: 10))
        XCTAssertTrue(welcome.isHittable)
        XCTAssertTrue(app.windows.firstMatch.frame.contains(welcome.frame))
        XCTAssertLessThan(welcome.frame.height, 44)
        XCTAssertLessThan(welcome.frame.maxY, input.frame.minY)
        capture("Authenticated fixture clean chat visible composer")
        input.tap(); input.typeText("A friendly sticker idea")
        XCTAssertTrue(app.buttons["Send message"].isEnabled)
        XCTAssertTrue(app.buttons["Send message"].isHittable)
        #if os(iOS)
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5))
        XCTAssertLessThanOrEqual(input.frame.maxY, app.keyboards.firstMatch.frame.minY)
        #endif
        capture("Authenticated fixture composer keyboard unsent")
        app.buttons["Library"].tap()
        XCTAssertTrue(app.buttons["Characters"].waitForExistence(timeout: 10))
        app.assertCompactHeader("Library", action: "Refresh library")
        app.buttons["Characters"].tap()
        capture("Authenticated fixture Characters inside Library")
        app.buttons["Create"].tap()
        let returned = assertComposer(app)
        returned.tap(); returned.typeText("Another unsent idea")
        XCTAssertTrue(app.buttons["Send message"].isEnabled)
        XCTAssertTrue(app.buttons["Send message"].isHittable)
        capture("Authenticated fixture composer tab return unsent")
        fixtureState("expired")
        app.buttons["Library"].tap()
        let refresh = app.buttons["Refresh library"]
        expectation(for: NSPredicate(format: "enabled == true"), evaluatedWith: refresh)
        waitForExpectations(timeout: 10)
        refresh.tap()
        XCTAssertTrue(app.buttons["Continue with LazyingArt"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.descendants(matching: .any)["chat-message-input"].exists)
        XCTAssertFalse(app.buttons["Library"].isHittable)
        capture("Expired fixture opens shared authentication")
        fixtureState("unavailable")
        refreshFromLogin(app)
        XCTAssertTrue(app.staticTexts["Sign-in is unavailable."].waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["Continue with LazyingArt"].exists)
        XCTAssertTrue(app.buttons["Retry"].isHittable)
        capture("Unavailable provider is not offered")
    }

    func testSharedAuthenticationDestinationAndConfiguredProviders() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-studio-origin", fixtureOrigin]
        defer { app.terminate() }
        for destination in ["Create", "Library", "Account"] {
            fixtureState("expired")
            app.launch()
            XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 20))
            app.buttons[destination].tap()
            XCTAssertTrue(app.buttons["Continue with LazyingArt"].waitForExistence(timeout: 10))
            XCTAssertFalse(app.buttons[destination].isHittable)
            XCTAssertFalse(app.buttons["Sign in"].exists)
            XCTAssertFalse(app.buttons["Manage App Store subscriptions"].exists)
            app.buttons["Browse stickers"].tap()
            XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 10))
            app.buttons[destination].tap()
            XCTAssertTrue(app.staticTexts["Sign in to WeSticker"].waitForExistence(timeout: 10))
            // Layout-only session transition, not a browser/PKCE authentication receipt.
            fixtureState("authenticated")
            refreshFromLogin(app)
            switch destination {
            case "Create": _ = assertComposer(app)
            case "Library":
                XCTAssertTrue(app.buttons["Characters"].waitForExistence(timeout: 10))
                app.assertCompactHeader("Library", action: "Refresh library")
            default:
                XCTAssertTrue(app.buttons["Manage App Store subscriptions"].waitForExistence(timeout: 10))
                app.assertCompactHeader("Account")
            }
            XCTAssertFalse(app.staticTexts["Sign in to WeSticker"].exists)
            capture("Fixture restored intended " + destination)
            app.terminate()
        }
        fixtureState("providers")
        app.launch()
        XCTAssertTrue(app.buttons["Create"].waitForExistence(timeout: 20))
        app.buttons["Create"].tap()
        for name in ["Google", "Apple", "GitHub", "LazyingArt"] {
            let button = app.buttons["Continue with " + name]
            XCTAssertTrue(button.waitForExistence(timeout: 10))
            XCTAssertTrue(button.isHittable)
            XCTAssertTrue(app.windows.firstMatch.frame.contains(button.frame))
            XCTAssertEqual(app.buttons.matching(identifier: "Continue with " + name).count, 1)
        }
        XCTAssertFalse(app.buttons["Continue with unknown"].exists)
        capture("Configured provider buttons on one shared route fixture")
        // Each fixture link opens only a local inert page, never a real issuer/account.
        for name in ["Google", "Apple", "GitHub", "LazyingArt"] {
            let provider = app.buttons["Continue with " + name]
            XCTAssertTrue(provider.waitForExistence(timeout: 10))
            provider.tap()
            let systemCancel = XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.buttons["Cancel"]
            if systemCancel.waitForExistence(timeout: 5) { systemCancel.tap() }
            else {
                let browserCancel = app.buttons["Cancel"].firstMatch
                XCTAssertTrue(browserCancel.waitForExistence(timeout: 10))
                browserCancel.tap()
            }
            XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 10))
            XCTAssertTrue(app.buttons["About this beta"].isHittable)
            XCTAssertFalse(app.staticTexts["Sign in to WeSticker"].exists)
            capture("System authentication cancelled to catalog fixture " + name)
            app.buttons["Create"].tap()
        }
    }

    func testProtectedCreateAndAccountNavigation() throws {
        let configured = publicProviders()
        let app = XCUIApplication()
        app.launchArguments += ["-studio-origin", publicOrigin]
        app.launch()
        defer { app.terminate() }
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 20))
        capture("Public initial Stickers")
        app.buttons["Create"].tap()
        XCTAssertTrue(app.staticTexts["Sign in to WeSticker"].waitForExistence(timeout: 20))
        app.assertCompactHeader("Sign in", action: "Service settings")
        XCTAssertFalse(app.descendants(matching: .any)["chat-message-input"].exists)
        XCTAssertFalse(app.buttons["Send message"].exists)
        XCTAssertFalse(app.buttons["Manage App Store subscriptions"].exists)
        for (id, name) in [("google", "Google"), ("apple", "Apple"), ("github", "GitHub"), ("lazyingart", "LazyingArt")] {
            let button = app.buttons["Continue with " + name]
            if configured.contains(id) {
                XCTAssertTrue(button.waitForExistence(timeout: 20))
                XCTAssertTrue(button.isHittable)
                XCTAssertTrue(app.windows.firstMatch.frame.contains(button.frame))
            } else { XCTAssertFalse(button.exists) }
        }
        XCTAssertFalse(app.buttons["Characters"].exists)
        XCTAssertEqual(app.webViews.count, 0)
        XCTAssertFalse(app.buttons["Account"].isHittable)
        capture("Shared authentication live provider availability")
        app.buttons["Browse stickers"].tap()
        XCTAssertTrue(app.buttons["About this beta"].waitForExistence(timeout: 10))
        app.buttons["Account"].tap()
        XCTAssertTrue(app.staticTexts["Sign in to WeSticker"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["Sign in"].exists)
        XCTAssertFalse(app.buttons["Manage App Store subscriptions"].exists)
        XCTAssertFalse(app.buttons["Subscribe"].exists)
        capture("Account opens the same shared authentication")
    }
}
