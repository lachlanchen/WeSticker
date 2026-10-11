"""Native source-contract regressions, not device, provider or image tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "apple/Sources"
ANDROID = ROOT / "android/app/src/main/java/art/lazying/westicker"


def test_four_primary_tabs_and_create_default():
    swift = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CreatorStudio.kt").read_text()
    assert '["Stickers", "Create", "Library", "Account"]' in swift
    assert 'listOf("Stickers","Create","Library","Account")' in kotlin
    assert "private var selected = 1" in swift
    assert "var tab by rememberSaveable { mutableStateOf(1) }" in kotlin


def test_characters_are_in_library_and_guest_create_has_no_login_gate():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert 'Picker("Library view", selection: $libraryPane)' in swift
    assert 'Text("Characters").tag(1)' in swift
    assert 'else if store.usesGuestChat {\n                        guestConversation' in swift
    assert 'if section == 1 && (store.usesGuestChat || pane == 0)' in swift
    assert 'listOf("Creations","Characters")' in kotlin
    assert 'if(section==1&&store.usesGuestChat)' in kotlin
    assert 'if(section==1&&(store.usesGuestChat||!store.creating&&pane==0))' in kotlin
    assert 'Continue with LazyingArt' not in swift + kotlin


def test_guest_transport_is_separate_and_credential_free():
    swift = (APPLE / "GuestChat.swift").read_text()
    kotlin = (ANDROID / "GuestChat.kt").read_text()
    for source in (swift, kotlin):
        assert "/api/guest/chat" in source
        assert "Authorization" not in source and "X-CSRF-Token" not in source
        assert "/api/packs" not in source
    assert "configuration.httpCookieStorage = nil" in swift
    assert "configuration.urlCredentialStorage = nil" in swift
    assert "completionHandler(nil)" in swift
    assert "CookieJar.NO_COOKIES" in kotlin
    assert ".followRedirects(false)" in kotlin and ".retryOnConnectionFailure(false)" in kotlin
    assert "continuation.invokeOnCancellation { call.cancel() }" in kotlin


def test_guest_completion_is_guarded_and_refresh_does_not_erase_guest_history():
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert "generation == guestGeneration, usesGuestChat" in swift
    assert "base == (try? validatedOrigin())" in swift
    assert "guestTask?.cancel()" in swift
    assert "generation == guestGeneration && usesGuestChat" in kotlin
    assert "base() == origin" in kotlin
    assert "guestJob?.cancel()" in kotlin
    assert "if (e is CancellationException) throw e" in kotlin
    for source, marker in ((swift, "func refresh()"), (kotlin, "suspend fun refresh()")):
        refresh = source.split(marker, 1)[1].split("acceptTerms()", 1)[0]
        assert "guestMessages =" not in refresh


def test_cloud_generation_keeps_existing_authenticated_path():
    for source in ((APPLE / "CloudStudio.swift").read_text(), (ANDROID / "CloudStudio.kt").read_text()):
        assert "/api/packs/" in source and "/generate" in source
        assert "usesGuestChat" in source and "needsConsent" in source
        assert "Confirm generation" in source
    assert "GuestChatClient.send" in (APPLE / "CloudStudio.swift").read_text()
    assert "GuestChatClient.send" in (ANDROID / "CloudStudio.kt").read_text()
