package art.lazying.westicker

class BillingSession(val origin: String, val token: String, val csrf: String) {
    fun sameAccountSession(other: BillingSession?): Boolean =
        other != null && origin == other.origin && token == other.token
}

data class BillingAttempt(val id: String, val product: String, val phase: String = "prepared") {
    val canResume: Boolean get() = phase == "prepared"
    val reportable: Boolean get() = phase == "cancelled" || phase == "pending"
}

object BillingRecovery {
    fun mayPurchase(enabled: Boolean, ready: Boolean, paidThrough: Boolean,
                    storeOwned: Boolean, attempt: BillingAttempt?): Boolean =
        enabled && ready && !paidThrough && !storeOwned && attempt == null

    fun mayDeliver(expectedOwner: String, actualOwner: String?, purchased: Boolean): Boolean =
        expectedOwner.isNotBlank() && expectedOwner == actualOwner && purchased

    fun afterVerification(attempt: BillingAttempt?, product: String, verified: Boolean, active: Boolean): BillingAttempt? =
        if (verified && active && attempt?.product == product) null else attempt
}
