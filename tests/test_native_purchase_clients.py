"""Native source-contract checks; these are not device or store purchase tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "apple/Sources/NativeBilling.swift"
ANDROID = ROOT / "android/app/src/main/java/art/lazying/westicker"


def test_account_uses_native_hosts():
    assert "NativeBillingAccountView" in (ROOT / "apple/Sources/CreatorStudio.swift").read_text()
    assert "BillingAccountScreen" in (ANDROID / "CreatorStudio.kt").read_text()
    assert "BillingClient.newBuilder" in (ANDROID / "NativeBilling.kt").read_text()
    assert "import StoreKit" in SWIFT.read_text()


def test_no_native_stripe_or_bridge_checkout():
    for path in (SWIFT, ANDROID / "NativeBilling.kt", ANDROID / "BillingAccountScreen.kt"):
        source = path.read_text().lower()
        for forbidden in ("stripe", "/api/billing/checkout", "capacitor", "webview"):
            # Comments can identify that the native root is not a web shell.
            assert forbidden not in "\n".join(line for line in source.splitlines() if not line.strip().startswith("//"))


def test_apple_server_verifies_before_finish():
    source = SWIFT.read_text()
    delivery = source.split("private func deliver(", 1)[1].split("private func verify(", 1)[0]
    assert delivery.index("tx.appAccountToken") < delivery.index("try persist(s, g)")
    assert delivery.index("try await verify(receipt, s, g)") < delivery.index("await tx.finish()")
    assert "try check(s, g)\n        await tx.finish()\n        try check(s, g)" in delivery
    assert source.count("await tx.finish()") == 1
    assert 'result["verified"] as? Bool == true' in source


def test_restore_does_not_initiate_purchase_or_automatic_sync():
    source = SWIFT.read_text()
    restore = source.split("func restore(sync:", 1)[1].split("func purchase(", 1)[0]
    assert "if sync { try await AppStore.sync()" in restore
    assert ".purchase(" not in restore
    source = (ANDROID / "NativeBilling.kt").read_text()
    restore = source.split("private suspend fun restoreLocked", 1)[1].split("fun purchase(", 1)[0]
    assert "launchBillingFlow" not in restore
    assert "attempt = null" not in restore


def test_play_never_acknowledges_or_consumes_in_client():
    source = (ANDROID / "NativeBilling.kt").read_text()
    assert "acknowledgePurchase(" not in source
    assert "consumeAsync(" not in source
    assert 'getJSONObject("google")' in source
    assert 'setObfuscatedAccountId(owner)' in source
    assert 'check(result.optBoolean("verified", false))' in source


def test_attempt_persisted_before_presenting_either_store():
    swift = SWIFT.read_text()
    assert 'journal.attempt?.phase = "presented"; try persist(s, g)' in swift
    assert swift.index('journal.attempt?.phase = "presented"') < swift.index("product.purchase(confirmIn:")
    kotlin = (ANDROID / "NativeBilling.kt").read_text()
    assert 'attempt = attempt?.copy(phase = "presented"); persist(s, g)' in kotlin
    assert kotlin.index('attempt = attempt?.copy(phase = "presented")') < kotlin.index("client.launchBillingFlow")


def test_fixed_session_requests_and_fail_closed_recovery_storage():
    swift = SWIFT.read_text()
    assert '"Bearer " + s.token' in swift
    assert 's.sameAccountSession(as: cloud?.billingSession)' in swift
    assert 'kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly' in swift
    kotlin = (ANDROID / "NativeBilling.kt").read_text()
    assert '"Bearer ${s.token}"' in kotlin
    assert 's.sameAccountSession(cloud.billingSession())' in kotlin
    cloud = (ANDROID / "CloudStudio.kt").read_text()
    assert 'readSecret("billing:$owner:", strict = true)' in cloud


def test_product_ids_come_from_catalog_not_bundle_prefix_on_play():
    kotlin = (ANDROID / "NativeBilling.kt").read_text()
    assert 'catalog.getJSONObject("products")' in kotlin
    assert 'purchase.products.single().startsWith' not in kotlin


def test_catalog_metadata_is_independent_of_receipt_verification():
    swift = SWIFT.read_text().split("func restore(sync:", 1)[1].split("func purchase(", 1)[0]
    assert swift.index("Product.products") < swift.index("try await deliver(")
    kotlin = (ANDROID / "NativeBilling.kt").read_text().split("private suspend fun restoreLocked", 1)[1].split("fun restore()", 1)[0]
    assert kotlin.index("queryPlans(products)") < kotlin.index("deliver(purchase")
