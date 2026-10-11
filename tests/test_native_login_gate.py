"""Native source contracts; runtime/provider qualification is recorded separately."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "apple/Sources"
ANDROID = ROOT / "android/app/src/main/java/art/lazying/westicker"


def test_public_home_initial_and_four_tabs():
    swift = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CreatorStudio.kt").read_text()
    assert '["Stickers", "Create", "Library", "Account"]' in swift
    assert 'listOf("Stickers","Create","Library","Account")' in kotlin
    assert "private var selected = 0" in swift
    assert "var tab by rememberSaveable { mutableStateOf(0) }" in kotlin


def test_one_root_login_remembers_destination_and_dismisses_to_browse():
    swift = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CreatorStudio.kt").read_text()
    assert swift.count("StudioLoginView(store: cloud,") == 1
    assert ".sheet(isPresented: $showAuthentication" in swift
    assert "selected = authDestination; showAuthentication = false" in swift
    assert "authDestination = destination; selected = 0; showAuthentication = true" in swift
    assert "switch cloud.signedIn ? selected : 0" in swift
    assert kotlin.count("StudioLoginScreen(cloud,loader,signIn,") == 1
    assert "if(authDestination!=null) Dialog(" in kotlin
    assert "authDestination?.let { tab=it;authDestination=null }" in kotlin
    assert "authDestination=destination;tab=0" in kotlin
    assert "when(if(cloud.signedIn) tab else 0)" in kotlin
    assert "cloud.finishLogin(uri);if(cloud.signedIn)tab=1" not in kotlin
    for source in (swift, kotlin):
        assert "onSignIn" not in source


def test_library_and_account_do_not_duplicate_auth_forms():
    for path in (APPLE / "NativeBilling.swift", ANDROID / "BillingAccountScreen.kt"):
        source = path.read_text()
        assert "signIn:" not in source
        assert 'Text("Sign in")' not in source
    for path in (APPLE / "CloudStudio.swift", ANDROID / "CloudStudio.kt"):
        source = path.read_text()
        assert "Sign in to cloud library" not in source
        assert "Browse stickers" in source


def test_characters_and_local_draft_remain_in_library():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert 'Picker("Library view", selection: $libraryPane)' in swift
    assert 'Text("Characters").tag(1)' in swift
    assert 'listOf("Creations","Characters")' in kotlin
    for source in (swift, kotlin):
        assert "Open saved local photo draft" in source


def test_retired_transport_absent_from_native_sources():
    for root in (APPLE, ANDROID):
        assert not list(root.glob("GuestChat.*"))
        for path in root.iterdir():
            if path.suffix in (".swift", ".kt"):
                source = path.read_text()
                assert "usesGuestChat" not in source
                assert "GuestChat" not in source
                assert "/api/guest/chat" not in source


def test_login_uses_live_availability_and_existing_pkce():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert 'boot["providers"]' in swift
    assert "StudioProvider.allCases.filter" in swift
    assert "guard providers.contains(provider) else" in swift
    assert '"provider": provider.rawValue' in swift
    assert 'boot.optJSONArray("providers")' in kotlin
    assert "StudioProvider.entries.filter" in kotlin
    assert "check(provider in providers)" in kotlin
    assert '.put("provider", provider.id)' in kotlin
    for source in (swift, kotlin):
        assert '"/api/native/link"' in source
        assert '"challenge"' in source and '"app_return"' in source
        assert "/exchange" in source
        for provider in ("Google", "Apple", "GitHub", "LazyingArt"):
            assert '"' + provider + '"' in source
        assert "signInAvailable" not in source
    assert "ForEach(store.providers)" in swift
    assert "store.providers.forEach" in kotlin


def test_offline_draft_is_available_from_shared_library_gate():
    swift = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CreatorStudio.kt").read_text()
    assert "openLocalDraft: authDestination == 2" in swift
    assert "openLocalDraft=if(authDestination==2)" in kotlin
    for source in (swift, kotlin):
        assert "showLocalDraft" in source
        assert "Close local draft" in source


def test_successful_signed_out_bootstrap_clears_bearer_without_cancelling_pkce():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    for source, refresh, branch, clear, tail in (
        (swift, "func refresh()", "guard signedIn else", 'StudioSecret.write("", base)', "guard !needsConsent"),
        (kotlin, "suspend fun refresh()", "if (!signedIn)", 'saveToken("")', "if (needsConsent)"),
    ):
        body = source.split(refresh, 1)[1].split(tail, 1)[0]
        signed_out = body.split(branch, 1)[1]
        assert clear in signed_out
        assert clear not in body.split(branch, 1)[0]
        assert "workspace = nil" in signed_out or "workspace = null" in signed_out
        assert "cancelLogin" not in signed_out and "link = nil" not in signed_out
        assert body.index('"/api/bootstrap"') < body.index(clear)


def test_selected_provider_response_url_goes_directly_to_system_browser():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    root = (ANDROID / "CreatorStudio.kt").read_text()
    activity = (ANDROID / "MainActivity.kt").read_text()
    assert 'let address = result["url"] as? String, let url = URL(string: address)' in swift
    assert "let url = try await startLogin(provider: provider)" in swift
    assert "let result = try await authentication.open(url)" in swift
    assert 'return result.getString("url")' in kotlin
    assert "beginAuthentication(cloud.startLogin(provider))" in root
    assert 'launch(authLauncher, Uri.parse(url), "art.lazying.westicker")' in activity
    for source in (swift, kotlin):
        assert "/?native_link=" not in source
        assert "\"/complete\"" in source
        assert "\"link\"" in source and "\"verifier\"" in source


def test_browser_cancellation_clears_root_gate_and_returns_to_catalog():
    swift = (APPLE / "CloudStudio.swift").read_text()
    root = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CreatorStudio.kt").read_text()
    assert "ASWebAuthenticationSessionError.canceledLogin.rawValue { return false }" in swift
    assert "if !completed { selected = 0; showAuthentication = false }" in root
    assert "activity.clearAuthenticationResult();cloud.cancelLogin();authDestination=null;tab=0" in kotlin


def test_authenticated_composer_keeps_explicit_layout_and_consent():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert "section == 1 && store.signedIn && !store.needsConsent && store.workspace != nil" in swift
    assert "VStack(spacing: 0)" in swift
    assert ".fixedSize(horizontal: false, vertical: true)" in swift
    assert ".safeAreaInset" not in swift
    assert "section==1&&store.signedIn&&!store.needsConsent&&store.workspace!=null" in kotlin
    assert ".imePadding()" in kotlin
    for source in (swift, kotlin):
        assert "/api/packs/" in source and "/generate" in source
        assert "Confirm generation" in source
