package art.lazying.westicker

import android.content.Context

// Compile-only boundary for the billing client. Not an app shell or runtime fake.
class CloudStudioStore(val context: Context) {
    val signedIn = false
    val busy = false
    val error: String? = null
    fun billingSession(): BillingSession? = null
    fun billingRead(session: BillingSession, owner: String): String = error("Compile-only fixture")
    fun billingWrite(session: BillingSession, owner: String, value: String): Unit = error("Compile-only fixture")
    fun base(): String = "https://service.test"
    suspend fun run(block: suspend () -> Unit) = block()
    suspend fun signOut() = Unit
}
