import Foundation

struct GuestChatExchange: Identifiable {
    let id: UUID
    let text: String
    var reply: String?
    var failure: String?
}

struct GuestChatTurn: Codable, Equatable {
    let role: String
    let content: String
}

enum GuestChatProtocol {
    static let messageLimit = 2000

    static func history(_ exchanges: [GuestChatExchange]) -> [GuestChatTurn] {
        var turns: [GuestChatTurn] = [], size = 0
        for exchange in exchanges.filter({ $0.reply != nil }).suffix(6).reversed() {
            let length = exchange.text.utf16.count + exchange.reply!.utf16.count
            guard size + length <= 16_000 else { break }
            turns.insert(contentsOf: [GuestChatTurn(role: "user", content: exchange.text),
                                      GuestChatTurn(role: "assistant", content: exchange.reply!)], at: 0)
            size += length
        }
        return turns
    }

    static func request(origin: String, message: String, exchanges: [GuestChatExchange], locale: String) throws -> URLRequest {
        let text = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, text.count <= messageLimit else { throw URLError(.badURL) }
        var request = URLRequest(url: URL(string: origin + "/api/guest/chat")!)
        request.httpMethod = "POST"
        request.timeoutInterval = 60
        request.httpShouldHandleCookies = false
        request.setValue(origin, forHTTPHeaderField: "Origin")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        struct Body: Encodable { let message: String; let history: [GuestChatTurn]; let locale: String }
        request.httpBody = try JSONEncoder().encode(Body(message: text, history: history(exchanges), locale: locale))
        return request
    }

    static func reply(_ data: Data, status: Int) throws -> String {
        guard data.count <= 65_536 else { throw URLError(.dataLengthExceedsMaximum) }
        let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        guard (200..<300).contains(status) else {
            let detail = value?["detail"] as? String ?? value?["error"] as? String ?? "Chat is unavailable. Please try again."
            throw NSError(domain: "GuestChat", code: status, userInfo: [NSLocalizedDescriptionKey: String(detail.prefix(500))])
        }
        guard let reply = value?["reply"] as? String, !reply.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw URLError(.cannotParseResponse)
        }
        return reply
    }
}

private final class GuestChatRedirectBlocker: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

enum GuestChatClient {
    // Separate from account networking: no credentials, cookies, redirects or retries.
    private static let session: URLSession = {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpCookieStorage = nil
        configuration.httpShouldSetCookies = false
        configuration.urlCredentialStorage = nil
        configuration.urlCache = nil
        return URLSession(configuration: configuration, delegate: GuestChatRedirectBlocker(), delegateQueue: nil)
    }()

    static func send(_ request: URLRequest) async throws -> String {
        let (data, response) = try await session.data(for: request)
        return try GuestChatProtocol.reply(data, status: (response as? HTTPURLResponse)?.statusCode ?? 0)
    }
}
