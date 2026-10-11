import Foundation

@main struct GuestChatTest {
    static func main() throws {
        let complete = (0..<8).map { GuestChatExchange(id: UUID(), text: "message \($0)", reply: "reply \($0)") }
        let pending = GuestChatExchange(id: UUID(), text: "pending")
        let failed = GuestChatExchange(id: UUID(), text: "failed", failure: "offline")
        let history = GuestChatProtocol.history(complete + [pending, failed])
        precondition(history.count == 12 && history.first?.content == "message 2")
        precondition(history.last?.content == "reply 7")
        precondition(history.enumerated().allSatisfy { $0.element.role == ($0.offset % 2 == 0 ? "user" : "assistant") })
        let large = (0..<6).map { _ in GuestChatExchange(id: UUID(), text: String(repeating: "a", count: 2000), reply: String(repeating: "b", count: 6000)) }
        precondition(GuestChatProtocol.history(large).count == 4)
        let request = try GuestChatProtocol.request(origin: "https://westicker.lazying.art", message: " hello ", exchanges: complete, locale: "en")
        precondition(request.url?.path == "/api/guest/chat" && request.httpMethod == "POST")
        precondition(request.value(forHTTPHeaderField: "Authorization") == nil)
        precondition(request.value(forHTTPHeaderField: "Cookie") == nil)
        precondition(request.value(forHTTPHeaderField: "X-CSRF-Token") == nil)
        precondition(!request.httpShouldHandleCookies)
        let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
        precondition(Set(body.keys) == ["message", "history", "locale"])
        precondition(body["message"] as? String == "hello")
        precondition((body["history"] as? [[String: String]])?.count == 12)
        let reply = try GuestChatProtocol.reply(Data(#"{"reply":"Hello"}"#.utf8), status: 200)
        precondition(reply == "Hello")
        for (value, status) in [(#"{"reply":""}"#, 200), (#"{"reply":123}"#, 200), ("not JSON", 200), (#"{"detail":"Slow down"}"#, 429), (#"{"reply":"not followed"}"#, 302)] {
            do { _ = try GuestChatProtocol.reply(Data(value.utf8), status: status); preconditionFailure("Accepted invalid reply") }
            catch { if status == 429 { precondition(error.localizedDescription == "Slow down") } }
        }
        for message in [" ", String(repeating: "x", count: 2001)] {
            do { _ = try GuestChatProtocol.request(origin: "https://westicker.lazying.art", message: message, exchanges: [], locale: "en"); preconditionFailure("Accepted invalid message") }
            catch { }
        }
        print("Guest chat request, history bounds, credential omission and response tests passed; no network requests.")
    }
}
