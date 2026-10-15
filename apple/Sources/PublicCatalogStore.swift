import Foundation

actor PublicCatalogStore {
    static let shared = PublicCatalogStore()
    private var nextRefresh = Date.distantPast
    private var current: [Pack]?
    private let source = URL(string: "https://westicker.lazying.art/api/catalog")!
    private let cache = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("public-aya-catalog.json")

    private func decode(_ data: Data) throws -> [Pack] {
        guard data.count <= 2_000_000 else { throw URLError(.dataLengthExceedsMaximum) }
        let value = try JSONDecoder().decode(Catalog.self, from: data)
        guard (1...200).contains(value.packs.count), Set(value.packs.map(\.id)).count == value.packs.count else { throw URLError(.cannotParseResponse) }
        for pack in value.packs {
            for language in ["en", "ja", "zh"] {
                guard let stickers = pack.stickers[language], (1...64).contains(stickers.count), Set(stickers.map(\.id)).count == stickers.count else { throw URLError(.cannotParseResponse) }
                for path in [pack.banner] + stickers.flatMap({ [$0.gif, $0.poster] }) {
                    guard let url = URL(string: path), url.scheme == "https", url.host == "aya.lazying.art",
                          url.user == nil, url.port == nil, url.query == nil, url.fragment == nil,
                          url.path.hasPrefix("/media/"), !path.contains("..") else { throw URLError(.badURL) }
                }
            }
        }
        return value.packs
    }

    func load() async -> [Pack]? {
        if current == nil, let data = try? Data(contentsOf: cache) { current = try? decode(data) }
        guard Date() >= nextRefresh else { return current }
        nextRefresh = Date().addingTimeInterval(300)
        do {
            var request = URLRequest(url: source)
            request.timeoutInterval = 8
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200, http.url == source else { throw URLError(.badServerResponse) }
            let packs = try decode(data)
            try data.write(to: cache, options: .atomic)
            current = packs
        } catch { nextRefresh = Date().addingTimeInterval(60) }
        return current
    }
}
