package art.lazying.westicker

import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.*
import com.android.billingclient.api.*
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class BillingPlan(val details: ProductDetails, val offer: ProductDetails.SubscriptionOfferDetails) {
    val id: String get() = details.productId
    val price: String get() = offer.pricingPhases.pricingPhaseList.single().formattedPrice
}
private class BillingProblem(message: String) : IllegalStateException(message)

// One connection belongs to the native root, not to the Account tab or a WebView.
class NativeBillingStore(private val cloud: CloudStudioStore) {
    var plans by mutableStateOf<List<BillingPlan>>(emptyList()); private set
    var configuredCount by mutableStateOf(0); private set
    var salesEnabled by mutableStateOf(false); private set
    var ready by mutableStateOf(false); private set
    var busy by mutableStateOf(false); private set
    var blocked by mutableStateOf(true); private set
    var message by mutableStateOf<String?>(null); private set
    var account by mutableStateOf(""); private set
    var plan by mutableStateOf("free"); private set
    var credits by mutableStateOf(0); private set
    var attempt by mutableStateOf<BillingAttempt?>(null); private set
    private var session: BillingSession? = null
    private var generation = 0L
    private var owner = ""
    private var products = emptySet<String>()
    private var basePlan = "monthly"
    private var receipts = linkedMapOf<String, String>()
    private var storeOwned = true
    private var paidThrough = false
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val mutex = Mutex()
    private val connectionMutex = Mutex()
    private data class Sheet(val session: BillingSession, val generation: Long, val attempt: String)
    private var sheet: Sheet? = null
    private val client = BillingClient.newBuilder(cloud.context.applicationContext)
        .setListener { result, purchases ->
            val presented = sheet
            if (result.responseCode == BillingClient.BillingResponseCode.USER_CANCELED && presented != null) {
                sheet = null
                run(presented.session, presented.generation) {
                    if (attempt?.id == presented.attempt) {
                        attempt = attempt?.copy(phase = "cancelled"); persist(presented.session, presented.generation)
                        reportOutcome(presented.session, presented.generation)
                        sheet = null; blocked = false; message = "Purchase cancelled."
                    }
                }
            } else if (result.responseCode == BillingClient.BillingResponseCode.OK && !purchases.isNullOrEmpty()) {
                sheet = null
                val s = session; val g = generation
                if (s != null) run(s, g) {
                    loadCatalog(s, g)
                    for (purchase in purchases) deliver(purchase, s, g)
                    sheet = null
                    restoreLocked(s, g)
                }
            } else {
                if (presented?.session?.sameAccountSession(cloud.billingSession()) == true) {
                    blocked = true; message = "Purchase status is uncertain. Restore before paying again."
                }
                restore()
            }
        }
        .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
        .enableAutoServiceReconnection()
        .build()

    fun attach() {
        val next = cloud.billingSession()
        if (session?.sameAccountSession(next) == true || session == null && next == null) return
        generation++; session = next
        plans = emptyList(); products = emptySet(); configuredCount = 0
        ready = false; salesEnabled = false; blocked = true; busy = false; message = null
        account = ""; plan = "free"; credits = 0; owner = ""; attempt = null; receipts.clear()
        restore()
    }
    fun close() { generation++; scope.cancel(); client.endConnection() }
    private fun checkSession(s: BillingSession, g: Long) {
        check(g == generation && s.sameAccountSession(session) && s.sameAccountSession(cloud.billingSession())) {
            "Your account changed. Restore from the original purchase account."
        }
    }
    private fun run(s: BillingSession, g: Long, action: suspend () -> Unit) {
        scope.launch {
            mutex.withLock {
                try {
                    checkSession(s, g); busy = true; message = null
                    action()
                } catch (e: CancellationException) { throw e }
                catch (e: Exception) {
                    if (g == generation && s.sameAccountSession(cloud.billingSession())) {
                        blocked = true; message = (e as? BillingProblem)?.message ?: "Purchase recovery is incomplete. Check the original account and use Restore; do not pay again."
                    }
                } finally { if (g == generation) busy = false }
            }
        }
    }
    private suspend fun api(path: String, body: JSONObject?, s: BillingSession, g: Long): JSONObject {
        checkSession(s, g)
        val result = withContext(Dispatchers.IO) {
            val c = URL(s.origin + path).openConnection() as HttpURLConnection
            try {
                c.requestMethod = if (body == null) "GET" else "POST"
                c.connectTimeout = 15000; c.readTimeout = 45000; c.instanceFollowRedirects = false
                c.setRequestProperty("Origin", s.origin); c.setRequestProperty("Authorization", "Bearer ${s.token}")
                c.setRequestProperty("X-CSRF-Token", s.csrf)
                if (body != null) {
                    c.doOutput = true; c.setRequestProperty("Content-Type", "application/json")
                    c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
                check(c.responseCode in 200..299) { "Verification unavailable" }
                JSONObject(c.inputStream.bufferedReader().use { it.readText() })
            } finally { c.disconnect() }
        }
        checkSession(s, g)
        return result
    }
    private suspend fun connect() = connectionMutex.withLock {
        if (!client.isReady) withTimeout(20000) {
            suspendCancellableCoroutine<Unit> { continuation ->
                client.startConnection(object : BillingClientStateListener {
                    override fun onBillingSetupFinished(result: BillingResult) {
                        if (!continuation.isActive) return
                        if (result.responseCode == BillingClient.BillingResponseCode.OK) continuation.resume(Unit)
                        else continuation.resumeWithException(IllegalStateException("Play Store unavailable"))
                    }
                    override fun onBillingServiceDisconnected() = Unit
                })
            }
        }
    }
    private suspend fun queryPurchases(): List<Purchase> {
        connect()
        return withTimeout(20000) { suspendCancellableCoroutine { continuation ->
            client.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.SUBS).build()) { result, purchases ->
                if (continuation.isActive) {
                    if (result.responseCode == BillingClient.BillingResponseCode.OK) continuation.resume(purchases)
                    else continuation.resumeWithException(IllegalStateException("Play purchases unavailable"))
                }
            }
        } }
    }
    private suspend fun queryPlans(ids: Set<String>): List<BillingPlan> {
        if (ids.isEmpty()) return emptyList()
        connect()
        val details = withTimeout(20000) { suspendCancellableCoroutine<List<ProductDetails>> { continuation ->
            val params = QueryProductDetailsParams.newBuilder().setProductList(ids.map {
                QueryProductDetailsParams.Product.newBuilder().setProductId(it).setProductType(BillingClient.ProductType.SUBS).build()
            }).build()
            client.queryProductDetailsAsync(params) { result, response ->
                if (continuation.isActive) {
                    if (result.responseCode == BillingClient.BillingResponseCode.OK) continuation.resume(response.productDetailsList)
                    else continuation.resumeWithException(IllegalStateException("Play plans unavailable"))
                }
            }
        } }
        // Only the backend-supported monthly base plan; no trial/offer/replacement inference.
        return details.mapNotNull { detail ->
            val offer = detail.subscriptionOfferDetails?.singleOrNull {
                it.basePlanId == basePlan && it.offerId == null && it.pricingPhases.pricingPhaseList.size == 1 &&
                    it.pricingPhases.pricingPhaseList.single().let { phase ->
                        phase.recurrenceMode == ProductDetails.RecurrenceMode.INFINITE_RECURRING && phase.billingPeriod == "P1M"
                    }
            }
            offer?.let { BillingPlan(detail, it) }
        }.sortedBy { it.offer.pricingPhases.pricingPhaseList.single().priceAmountMicros }
    }
    private fun persist(s: BillingSession, g: Long) {
        checkSession(s, g)
        val value = JSONObject().put("receipts", JSONObject(receipts as Map<*, *>))
        attempt?.let { value.put("attempt", JSONObject().put("id", it.id).put("product", it.product).put("phase", it.phase)) }
        cloud.billingWrite(s, owner, value.toString())
    }
    private suspend fun loadCatalog(s: BillingSession, g: Long) {
        val catalog = api("/api/billing/native/catalog", null, s, g).getJSONObject("providers").getJSONObject("google")
        val binding = catalog.getString("binding")
        check(binding.matches(Regex("[a-f0-9]{64}")))
        owner = binding; products = catalog.getJSONObject("products").keys().asSequence().toSet()
        configuredCount = products.size; salesEnabled = catalog.optBoolean("purchase_enabled", false)
        basePlan = catalog.optString("base_plan", "monthly")
        val saved = cloud.billingRead(s, owner)
        val journal = if (saved.isEmpty()) JSONObject() else JSONObject(saved)
        attempt = journal.optJSONObject("attempt")?.let { BillingAttempt(it.getString("id"), it.getString("product"), it.getString("phase")) }
        val known = journal.optJSONObject("receipts") ?: JSONObject()
        receipts = known.keys().asSequence().associateWith { known.getString(it) }.toMap(LinkedHashMap())
    }
    private suspend fun loadAccount(s: BillingSession, g: Long) {
        val user = api("/api/bootstrap", null, s, g).getJSONObject("user")
        account = user.optString("name", "WeSticker account"); plan = user.optString("plan", "free"); credits = user.optInt("credits")
        paidThrough = user.optDouble("expires", 0.0) > System.currentTimeMillis() / 1000.0
    }
    private suspend fun reportOutcome(s: BillingSession, g: Long) {
        val a = attempt ?: return
        if (!a.reportable) return
        api("/api/billing/native/outcome", JSONObject().put("attempt", a.id).put("state", a.phase), s, g)
        if (a.phase == "cancelled") { attempt = null; persist(s, g) }
    }
    private suspend fun verify(token: String, product: String, s: BillingSession, g: Long) {
        val result = api("/api/billing/native/verify", JSONObject().put("provider", "google").put("token", token), s, g)
        check(result.optBoolean("verified", false))
        // The server acknowledges only after durable delivery. Never acknowledge/consume here.
        attempt = BillingRecovery.afterVerification(attempt, product, true, result.optBoolean("active", false))
        persist(s, g)
    }
    private suspend fun deliver(purchase: Purchase, s: BillingSession, g: Long) {
        checkSession(s, g)
        check(purchase.products.size == 1)
        if (purchase.accountIdentifiers?.obfuscatedAccountId != owner) {
            throw BillingProblem("This Play purchase belongs to another WeSticker account. Sign in to its original account.")
        }
        if (purchase.purchaseState == Purchase.PurchaseState.PENDING) {
            if (attempt?.product == purchase.products.single()) { attempt = attempt?.copy(phase = "pending"); persist(s, g); reportOutcome(s, g) }
            blocked = true; message = "Payment is pending. Restore after approval; do not pay again."
            return
        }
        check(BillingRecovery.mayDeliver(owner, purchase.accountIdentifiers?.obfuscatedAccountId, purchase.purchaseState == Purchase.PurchaseState.PURCHASED))
        receipts[purchase.purchaseToken] = purchase.products.single(); persist(s, g)
        verify(purchase.purchaseToken, purchase.products.single(), s, g)
    }
    private suspend fun restoreLocked(s: BillingSession, g: Long) {
        ready = false; blocked = true
        loadCatalog(s, g); loadAccount(s, g)
        val metadata = try { queryPlans(products) } catch (e: CancellationException) { throw e } catch (_: Exception) { emptyList() }
        checkSession(s, g); plans = metadata
        reportOutcome(s, g)
        val found = queryPurchases(); checkSession(s, g)
        storeOwned = found.isNotEmpty()
        for (purchase in found) deliver(purchase, s, g)
        val handled = found.map { it.purchaseToken }.toSet()
        for ((token, product) in receipts.toMap()) if (token !in handled) verify(token, product, s, g)
        loadAccount(s, g)
        ready = true
        blocked = sheet != null || !BillingRecovery.mayPurchase(true, true, paidThrough, storeOwned, attempt)
        if (attempt != null) message = "A purchase is awaiting recovery. No additional payment will be started automatically."
        else if (plans.size < configuredCount) message = "Some Play Store plans are unavailable. Restore and Manage remain available."
    }
    fun restore() {
        val s = session ?: return; val g = generation
        if (busy) return
        run(s, g) { restoreLocked(s, g) }
    }
    fun purchase(activity: Activity, plan: BillingPlan, resume: Boolean = false) {
        if (busy || sheet != null || !ready || !salesEnabled || !resume && blocked || resume && attempt?.canResume != true) return
        val s = session ?: return; val g = generation
        run(s, g) {
            val found = queryPurchases(); checkSession(s, g)
            loadAccount(s, g); check(found.isEmpty() && !paidThrough)
            loadCatalog(s, g); check(salesEnabled && plan.id in products)
            val fresh = queryPlans(setOf(plan.id)).single(); checkSession(s, g)
            check(fresh.price == plan.price && fresh.offer.offerToken == plan.offer.offerToken) { "Store price changed. Refresh plans." }
            if (resume) check(attempt?.canResume == true && attempt?.product == plan.id)
            else { check(attempt == null); attempt = BillingAttempt(UUID.randomUUID().toString(), plan.id) }
            persist(s, g); blocked = true
            val prepared = api("/api/billing/native/prepare", JSONObject().put("provider", "google").put("product", plan.id).put("attempt", attempt!!.id), s, g)
            check(prepared.getString("binding") == owner && prepared.getString("attempt") == attempt!!.id)
            check(!activity.isFinishing && !activity.isDestroyed && activity.hasWindowFocus())
            val details = BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(fresh.details).setOfferToken(fresh.offer.offerToken).build()
            val params = BillingFlowParams.newBuilder().setObfuscatedAccountId(owner).setProductDetailsParamsList(listOf(details)).build()
            attempt = attempt?.copy(phase = "presented"); persist(s, g)
            sheet = Sheet(s, g, attempt!!.id)
            val result = client.launchBillingFlow(activity, params)
            if (result.responseCode == BillingClient.BillingResponseCode.USER_CANCELED) {
                attempt = attempt?.copy(phase = "cancelled"); persist(s, g); reportOutcome(s, g); sheet = null; blocked = false
            } else if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                // Any non-cancel failure retains the exact attempt until reconciliation.
                message = "Play could not confirm purchase status. Restore before paying again."
            }
        }
    }
    fun manage(activity: Activity) {
        try { activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/account/subscriptions?package=art.lazying.westicker"))) }
        catch (_: Exception) { message = "Play subscription management could not be opened." }
    }
}
