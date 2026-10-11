import Foundation

@main struct BillingRecoveryTests {
    static func main() throws {
        var checks = 0
        func verify(_ value: Bool) { precondition(value); checks += 1 }
        let a = NativeBillingAttempt(product: "art.lazying.westicker.pocket")
        verify(a.canResume)
        for phase in ["presented", "pending", "cancelled", "unknown"] {
            var journal = NativeBillingJournal(attempt: a)
            journal.attempt?.phase = phase
            let restored = try JSONDecoder().decode(NativeBillingJournal.self, from: JSONEncoder().encode(journal))
            verify(restored.attempt?.id == a.id)
            verify(restored.attempt?.canResume == false)
            verify(!NativeBillingRecovery.mayPurchase(enabled: true, ready: true, paidThrough: false, storeOwned: false, attempt: restored.attempt))
        }
        for enabled in [false, true] { for ready in [false, true] {
            for paid in [false, true] { for owned in [false, true] {
                verify(NativeBillingRecovery.mayPurchase(enabled: enabled, ready: ready, paidThrough: paid, storeOwned: owned, attempt: nil) == (enabled && ready && !paid && !owned))
            } }
        } }
        verify(NativeBillingRecovery.afterVerification(a, product: a.product, verified: false, active: true) == a)
        verify(NativeBillingRecovery.afterVerification(a, product: a.product, verified: true, active: false) == a)
        verify(NativeBillingRecovery.afterVerification(a, product: "different-product", verified: true, active: true) == a)
        verify(NativeBillingRecovery.afterVerification(a, product: a.product, verified: true, active: true) == nil)
        let session = NativeBillingSession(origin: "https://service.test", token: "session-a", csrf: "csrf-a")
        verify(!session.sameAccountSession(as: nil))
        verify(!session.sameAccountSession(as: NativeBillingSession(origin: session.origin, token: "session-b", csrf: session.csrf)))
        verify(!session.sameAccountSession(as: NativeBillingSession(origin: "https://other.test", token: session.token, csrf: session.csrf)))
        verify(session.sameAccountSession(as: NativeBillingSession(origin: session.origin, token: session.token, csrf: "refreshed-csrf")))
        print("Apple billing recovery: \(checks) checks passed (no store or network access)")
    }
}
