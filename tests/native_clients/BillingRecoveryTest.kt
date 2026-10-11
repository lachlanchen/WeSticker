package art.lazying.westicker

fun main() {
    var cases = 0
    fun verify(value: Boolean) { check(value); cases++ }
    val a = BillingAttempt("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "art.lazying.westicker.pocket")
    verify(a.canResume)
    for (phase in listOf("presented", "pending", "cancelled", "unknown")) {
        val restarted = a.copy(phase = phase)
        verify(!restarted.canResume)
        verify(!BillingRecovery.mayPurchase(true, true, false, false, restarted))
    }
    verify(!a.reportable)
    verify(a.copy(phase = "cancelled").reportable)
    verify(a.copy(phase = "pending").reportable)
    verify(!a.copy(phase = "presented").reportable)
    for (enabled in listOf(false, true)) for (ready in listOf(false, true)) {
        for (paid in listOf(false, true)) for (owned in listOf(false, true)) {
            verify(BillingRecovery.mayPurchase(enabled, ready, paid, owned, null) == (enabled && ready && !paid && !owned))
        }
    }
    verify(!BillingRecovery.mayDeliver("owner-a", "owner-b", true))
    verify(!BillingRecovery.mayDeliver("owner-a", null, true))
    verify(!BillingRecovery.mayDeliver("owner-a", "owner-a", false))
    verify(!BillingRecovery.mayDeliver("", "", true))
    verify(BillingRecovery.mayDeliver("owner-a", "owner-a", true))
    verify(BillingRecovery.afterVerification(a, a.product, false, true) == a)
    verify(BillingRecovery.afterVerification(a, a.product, true, false) == a)
    verify(BillingRecovery.afterVerification(a, "different-product", true, true) == a)
    verify(BillingRecovery.afterVerification(a, a.product, true, true) == null)
    val session = BillingSession("https://service.test", "session-a", "csrf-a")
    verify(!session.sameAccountSession(null))
    verify(!session.sameAccountSession(BillingSession(session.origin, "session-b", "csrf-a")))
    verify(!session.sameAccountSession(BillingSession("https://other.test", session.token, "csrf-a")))
    verify(session.sameAccountSession(BillingSession(session.origin, session.token, "csrf-refreshed")))
    println("Billing recovery: $cases checks passed (no store or network access)")
}
