package art.lazying.westicker

import okio.Buffer
import org.json.JSONObject

fun main() {
    val complete = (0 until 8).map { GuestChatExchange("$it", "message $it", "reply $it") }
    val history = GuestChatHistory.turns(complete + GuestChatExchange("pending", "pending") + GuestChatExchange("failed", "failed", failure = "offline"))
    check(history.size == 12 && history.first().content == "message 2" && history.last().content == "reply 7")
    check(history.withIndex().all { it.value.role == if (it.index % 2 == 0) "user" else "assistant" })
    val large = (0 until 6).map { GuestChatExchange("$it", "a".repeat(2000), "b".repeat(6000)) }
    check(GuestChatHistory.turns(large).size == 4)
    val request = GuestChatClient.request("https://westicker.lazying.art", " hello ", complete, "en")
    check(request.url.encodedPath == "/api/guest/chat" && request.method == "POST")
    check(listOf("Authorization", "Cookie", "X-CSRF-Token").all { request.header(it) == null })
    val buffer = Buffer()
    request.body!!.writeTo(buffer)
    val body = JSONObject(buffer.readUtf8())
    check(body.keySet() == setOf("message", "history", "locale"))
    check(body.getString("message") == "hello" && body.getJSONArray("history").length() == 12)
    check(GuestChatClient.reply("""{"reply":"Hello"}""", 200) == "Hello")
    listOf("""{"reply":""}""" to 200, """{"reply":123}""" to 200, "not JSON" to 200,
        """{"detail":"Slow down"}""" to 429, """{"reply":"not followed"}""" to 302).forEach { (value, status) ->
        val result = runCatching { GuestChatClient.reply(value, status) }
        check(result.isFailure)
        if (status == 429) check(result.exceptionOrNull()!!.message == "Slow down")
    }
    listOf(" ", "x".repeat(2001)).forEach {
        check(runCatching { GuestChatClient.request("https://westicker.lazying.art", it, emptyList(), "en") }.isFailure)
    }
    println("Guest chat request, history bounds, credential omission and response tests passed; no network requests.")
}
