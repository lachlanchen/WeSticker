package art.lazying.westicker

import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Authenticator
import okhttp3.Call
import okhttp3.Callback
import okhttp3.CookieJar
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class GuestChatExchange(val id: String, val text: String, val reply: String? = null, val failure: String? = null)
data class GuestChatTurn(val role: String, val content: String)

object GuestChatHistory {
    const val MESSAGE_LIMIT = 2000
    fun turns(exchanges: List<GuestChatExchange>): List<GuestChatTurn> {
        val turns = mutableListOf<GuestChatTurn>()
        var size = 0
        for (exchange in exchanges.filter { it.reply != null }.takeLast(6).asReversed()) {
            val length = exchange.text.length + exchange.reply!!.length
            if (size + length > 16_000) break
            turns.addAll(0, listOf(GuestChatTurn("user", exchange.text), GuestChatTurn("assistant", exchange.reply)))
            size += length
        }
        return turns
    }
}

object GuestChatClient {
    // Coil already provides OkHttp. This independent client never borrows account credentials.
    private val client = OkHttpClient.Builder().cookieJar(CookieJar.NO_COOKIES)
        .authenticator(Authenticator.NONE).proxyAuthenticator(Authenticator.NONE)
        .followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false)
        .callTimeout(60, TimeUnit.SECONDS).build()

    fun request(origin: String, message: String, exchanges: List<GuestChatExchange>, locale: String): Request {
        val text = message.trim()
        require(text.isNotEmpty() && text.length <= GuestChatHistory.MESSAGE_LIMIT)
        val history = JSONArray(GuestChatHistory.turns(exchanges).map { JSONObject().put("role", it.role).put("content", it.content) })
        val body = JSONObject().put("message", text).put("history", history).put("locale", locale)
        return Request.Builder().url("$origin/api/guest/chat").header("Origin", origin)
            .post(body.toString().toRequestBody("application/json".toMediaType())).build()
    }

    fun reply(text: String, status: Int): String {
        require(text.toByteArray(Charsets.UTF_8).size <= 65_536) { "Chat reply was too large." }
        val value = runCatching { JSONObject(text) }.getOrNull()
        if (status !in 200..299) {
            val detail = (value?.opt("detail") as? String) ?: (value?.opt("error") as? String)
            error(detail?.take(500) ?: "Chat is unavailable. Please try again.")
        }
        return (value?.opt("reply") as? String)?.takeIf { it.isNotBlank() } ?: error("Chat returned an empty reply.")
    }

    suspend fun send(request: Request): String = suspendCancellableCoroutine { continuation ->
        val call = client.newCall(request)
        continuation.invokeOnCancellation { call.cancel() }
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, error: IOException) {
                if (continuation.isActive) continuation.resumeWithException(error)
            }
            override fun onResponse(call: Call, response: Response) {
                val result = runCatching { response.use { reply(it.body?.string().orEmpty(), it.code) } }
                if (continuation.isActive) result.fold({ continuation.resume(it) }, { continuation.resumeWithException(it) })
            }
        })
    }
}
