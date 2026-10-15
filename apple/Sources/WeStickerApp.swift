import SwiftUI
import UniformTypeIdentifiers
import ImageIO
#if os(iOS)
import UIKit
#else
import AppKit
#endif

struct Sticker: Decodable, Identifiable {
    let id, label, gif, poster: String
}
struct Pack: Decodable, Identifiable {
    let id, english, name, banner: String
    let stickers: [String: [Sticker]]
}
struct Catalog: Decodable { let packs: [Pack] }

actor DownloadSlots {
    static let shared = DownloadSlots()
    private var available = 3
    private var waiting: [CheckedContinuation<Void, Never>] = []
    func acquire() async {
        if available > 0 { available -= 1; return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func release() {
        if waiting.isEmpty { available += 1 } else { waiting.removeFirst().resume() }
    }
}

func bundled(_ path: String) -> URL? {
    guard !path.contains("..") else { return nil }
    return Bundle.main.resourceURL?.appendingPathComponent("CatalogAssets").appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
}

actor ImageStore {
    static let shared = ImageStore()
    private let cache = NSCache<NSURL, NSData>()
    private var pending: [URL: Task<Data, Error>] = [:]
    private let session: URLSession
    init() {
        cache.totalCostLimit = 20_000_000
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 20
        config.timeoutIntervalForResource = 45
        config.httpMaximumConnectionsPerHost = 4
        config.urlCache = URLCache(memoryCapacity: 8_000_000, diskCapacity: 40_000_000)
        session = URLSession(configuration: config)
    }
    func load(_ path: String) async throws -> Data {
        guard let url = path.hasPrefix("/") ? bundled(path) : URL(string: path) else { throw URLError(.badURL) }
        if let value = cache.object(forKey: url as NSURL) { return value as Data }
        if let task = pending[url] { return try await task.value }
        let data: Data
        if url.isFileURL {
            data = try Data(contentsOf: url)
        } else {
            guard url.scheme == "https", url.host == "aya.lazying.art", url.user == nil,
                  url.port == nil, url.path.hasPrefix("/media/") else { throw URLError(.badURL) }
            let task = Task<Data, Error> {
                await DownloadSlots.shared.acquire()
                do {
                    let (bytes, response) = try await session.data(for: URLRequest(url: url))
                    guard let http = response as? HTTPURLResponse, http.statusCode == 200,
                          http.url?.host == "aya.lazying.art", http.url?.scheme == "https",
                          bytes.count <= 3_000_000 else { throw URLError(.badServerResponse) }
                    await DownloadSlots.shared.release()
                    return bytes
                } catch {
                    await DownloadSlots.shared.release()
                    throw error
                }
            }
            pending[url] = task
            defer { pending[url] = nil }
            data = try await task.value
        }
        cache.setObject(data as NSData, forKey: url as NSURL, cost: data.count)
        return data
    }
}

struct AnimatedArtwork: View {
    let sticker: Sticker
    var playing = true
    @State private var bytes: Data?
    var body: some View {
        Group {
            if let bytes { NativeImage(data: bytes).allowsHitTesting(false) }
            else { RoundedRectangle(cornerRadius: 8).fill(Color.gray.opacity(0.06)) }
        }
        .accessibilityLabel(sticker.label)
        .task(id: sticker.gif + String(playing)) {
            bytes = try? await ImageStore.shared.load(sticker.poster)
            if playing, let data = try? await ImageStore.shared.load(sticker.gif), !Task.isCancelled { bytes = data }
        }
    }
}

#if os(iOS)
struct NativeImage: UIViewRepresentable {
    let data: Data
    var playing: Bool = true
    class Coordinator { var last: Data? }
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeUIView(context: Context) -> UIImageView {
        let view = UIImageView()
        view.contentMode = .scaleAspectFit
        view.setContentHuggingPriority(.defaultLow, for: .horizontal)
        view.setContentHuggingPriority(.defaultLow, for: .vertical)
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        view.setContentCompressionResistancePriority(.defaultLow, for: .vertical)
        return view
    }
    func updateUIView(_ view: UIImageView, context: Context) {
        guard context.coordinator.last != data else {
            if playing && (view.animationImages?.count ?? 0) > 1 { view.startAnimating() } else { view.stopAnimating() }
            return
        }
        context.coordinator.last = data
        view.stopAnimating(); view.animationImages = nil
        guard let source = CGImageSourceCreateWithData(data as CFData, nil) else { return }
        let count = min(CGImageSourceGetCount(source), 180)
        var frames: [UIImage] = [], duration = 0.0
        for index in 0..<count {
            guard let image = CGImageSourceCreateImageAtIndex(source, index, nil) else { continue }
            frames.append(UIImage(cgImage: image))
            let props = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [String: Any]
            let gif = props?[kCGImagePropertyGIFDictionary as String] as? [String: Any]
            duration += max(0.02, gif?[kCGImagePropertyGIFUnclampedDelayTime as String] as? Double
                ?? gif?[kCGImagePropertyGIFDelayTime as String] as? Double ?? 0.08)
        }
        view.image = frames.first
        if frames.count > 1 { view.animationImages = frames; view.animationDuration = duration; if playing { view.startAnimating() } }
    }
    static func dismantleUIView(_ view: UIImageView, coordinator: Coordinator) {
        view.stopAnimating(); view.animationImages = nil; coordinator.last = nil
    }
}
struct ShareSheet: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: [url], applicationActivities: nil)
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}
#else
struct NativeImage: NSViewRepresentable {
    let data: Data
    var playing: Bool = true
    class Coordinator { var last: Data? }
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> GIFImageView {
        let view = GIFImageView()
        view.imageScaling = .scaleProportionallyUpOrDown
        view.animates = false
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        view.setContentCompressionResistancePriority(.defaultLow, for: .vertical)
        return view
    }
    func updateNSView(_ view: GIFImageView, context: Context) {
        view.setPlaying(playing)
        guard context.coordinator.last != data else { return }
        context.coordinator.last = data
        view.load(data)
    }
    static func dismantleNSView(_ view: GIFImageView, coordinator: Coordinator) {
        view.stop()
        coordinator.last = nil
    }
}
#endif

struct GIFDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.gif] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}
struct Preview: Identifiable {
    let pack: Pack
    let sticker: Sticker
    var id: String { pack.id + sticker.id }
}
struct SharedFile: Identifiable { let url: URL; var id: String { url.path } }

@main
struct WeStickerApp: App {
    var body: some Scene {
        WindowGroup { StudioRootView().tint(Color(red: 0.79, green: 0.19, blue: 0.37)) }
        #if os(macOS)
        .defaultSize(width: 1120, height: 800)
        #endif
    }
}

struct CatalogView: View {
    init(showSaved: Bool = false) { _onlySaved = State(initialValue: showSaved) }
    @State private var packs: [Pack] = {
        guard let url = bundled("catalog.json"), let data = try? Data(contentsOf: url),
              let value = try? JSONDecoder().decode(Catalog.self, from: data) else { return [] }
        return value.packs
    }()
    @AppStorage("catalog-language") private var language = "en"
    @AppStorage("catalog-favorites") private var saved = ""
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var selected = "vol-01"
    @State private var query = ""
    @State private var onlySaved = false
    @State private var playbackOverride: Bool?
    private var playing: Bool { playbackOverride ?? !reduceMotion }
    @State private var preview: Preview?
    @State private var info = false
    @State private var busy = false
    @State private var failure: String?
    @State private var shared: SharedFile?
    @State private var document: GIFDocument?
    @State private var exporting = false
    @State private var filename = "sticker.gif"
    private var favorites: Set<String> { Set(saved.split(separator: "|").map(String.init)) }
    private var filtered: [Pack] {
        packs.filter { (!onlySaved || favorites.contains($0.id)) &&
            (query.isEmpty || ($0.english + $0.name).localizedCaseInsensitiveContains(query)) }
    }
    private var active: Pack? { filtered.first { $0.id == selected } ?? filtered.first }
    private func toggle(_ pack: Pack) {
        var values = favorites
        if values.contains(pack.id) { values.remove(pack.id) } else { values.insert(pack.id) }
        saved = values.sorted().joined(separator: "|")
    }
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                    TextField("Search collections", text: $query).textFieldStyle(.plain)
                    if !query.isEmpty { Button { query = "" } label: { Image(systemName: "xmark.circle.fill") }.accessibilityLabel("Clear search") }
                }.padding(12).background(Color.gray.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
                GeometryReader { geometry in
                    if geometry.size.width >= 700 {
                        HStack(alignment: .top, spacing: 16) {
                            ScrollView { LazyVStack(spacing: 6) { ForEach(filtered) { packButton($0) } } }.frame(width: 210)
                            content.frame(maxWidth: .infinity)
                        }
                    } else {
                        VStack(spacing: 12) {
                            ScrollView(.horizontal, showsIndicators: false) {
                                LazyHStack(spacing: 6) { ForEach(filtered) { packButton($0).frame(width: 188) } }
                            }.frame(height: 68)
                            content
                        }
                    }
                }
            }
            .padding(16)
            .compactStudioHeader("WeSticker")
            .toolbar {
                ToolbarItemGroup(placement: .primaryAction) {
                    Button { onlySaved.toggle() } label: { Image(systemName: onlySaved ? "heart.fill" : "heart") }.accessibilityLabel("Saved collections")
                    Button { info = true } label: { Image(systemName: "info.circle") }.accessibilityLabel("About WeSticker")
                }
            }
            .sheet(item: $preview) { value in
                VStack(spacing: 16) {
                    HStack {
                        Text(value.sticker.label).font(.title2.bold())
                        Spacer()
                        Button { preview = nil } label: { Image(systemName: "xmark") }.accessibilityLabel("Close preview")
                    }
                    AnimatedArtwork(sticker: value.sticker, playing: playing).aspectRatio(1, contentMode: .fit)
                    Button { download(value.pack, value.sticker) } label: { Label("Save GIF", systemImage: "square.and.arrow.up") }
                        .buttonStyle(.borderedProminent).disabled(busy)
                }.padding(24).frame(idealWidth: 420, idealHeight: 520)
                #if os(iOS)
                .sheet(item: $shared) { ShareSheet(url: $0.url) }
                #endif
                .fileExporter(isPresented: $exporting, document: document, contentType: .gif, defaultFilename: filename) { result in
                    if case let .failure(error) = result { failure = error.localizedDescription }
                }
            }
            #if os(iOS)
            .sheet(item: Binding(get: { preview == nil ? shared : nil }, set: { shared = $0 })) { ShareSheet(url: $0.url) }
            #endif
            .fileExporter(isPresented: Binding(get: { preview == nil && exporting }, set: { exporting = $0 }),
                document: document, contentType: .gif, defaultFilename: filename) { result in
                    if case let .failure(error) = result { failure = error.localizedDescription }
                }
            .alert("WeSticker", isPresented: $info) {
                Button("Done", role: .cancel) {}
            } message: {
                Text("Aya, Lala, Sasa and Zhuangzi the robot.\n\nWeSticker by LazyingArt.\n\nFavorites and local photo drafts stay on this device. Cloud creations belong to your signed-in account.")
            }
            .alert("Could not save sticker", isPresented: Binding(get: { failure != nil }, set: { if !$0 { failure = nil } })) {
                Button("OK", role: .cancel) { failure = nil }
            } message: { Text(failure ?? "") }
        }
        .task { if let latest = await PublicCatalogStore.shared.load(), !Task.isCancelled { packs = latest } }
        #if os(macOS)
        .frame(minWidth: 640, minHeight: 500)
        #endif
    }
    private func packButton(_ pack: Pack) -> some View {
        Button { selected = pack.id } label: {
            HStack(spacing: 8) {
                if let first = pack.stickers[language]?.first {
                    AnimatedArtwork(sticker: first, playing: false).frame(width: 44, height: 44)
                }
                Text(pack.english).font(.subheadline.weight(.semibold)).lineLimit(2).frame(maxWidth: .infinity, alignment: .leading)
            }.padding(10).background(active?.id == pack.id ? Color.pink.opacity(0.10) : Color.gray.opacity(0.04), in: RoundedRectangle(cornerRadius: 8))
        }.buttonStyle(.plain)
            .animation(reduceMotion ? nil : .easeOut(duration: 0.16), value: active?.id == pack.id)
    }
    @ViewBuilder private var content: some View {
        if let pack = active {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(pack.english).font(.title3.bold())
                        Text("\(pack.stickers[language]?.count ?? 0) GIFs").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button { toggle(pack) } label: { Image(systemName: favorites.contains(pack.id) ? "heart.fill" : "heart") }
                        .accessibilityLabel("Save collection")
                }
                HStack {
                    Picker("Sticker language", selection: $language) {
                        Text("English").tag("en"); Text("日本語").tag("ja"); Text("中文").tag("zh")
                    }.pickerStyle(.segmented)
                    Button { playbackOverride = !playing } label: { Image(systemName: playing ? "pause.fill" : "play.fill") }
                        .accessibilityLabel(playing ? "Pause animations" : "Play animations")
                }
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 106, maximum: 180), spacing: 8)], spacing: 8) {
                        ForEach(pack.stickers[language] ?? []) { sticker in
                            VStack(spacing: 0) {
                                Button { preview = Preview(pack: pack, sticker: sticker) } label: {
                                    AnimatedArtwork(sticker: sticker, playing: playing).aspectRatio(1, contentMode: .fit).contentShape(Rectangle())
                                }.buttonStyle(.plain).accessibilityLabel("Preview " + sticker.label)
                                HStack {
                                    Text(sticker.label).font(.caption).lineLimit(2)
                                    Spacer(minLength: 0)
                                    Button { download(pack, sticker) } label: { Image(systemName: "square.and.arrow.up").frame(width: 32, height: 36) }
                                        .accessibilityLabel("Save GIF " + sticker.label).disabled(busy)
                                }.padding(.horizontal, 8)
                            }.background(Color.gray.opacity(0.035), in: RoundedRectangle(cornerRadius: 8))
                        }
                    }
                }.id(pack.id + language)
            }
        } else {
            VStack(spacing: 12) {
                Image(systemName: "magnifyingglass").font(.largeTitle)
                Text("No collections found")
                Button("Show all collections") { onlySaved = false; query = "" }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
    private func download(_ pack: Pack, _ sticker: Sticker) {
        guard !busy else { return }
        busy = true
        Task { @MainActor in
            defer { busy = false }
            do {
                let data = try await ImageStore.shared.load(sticker.gif)
                guard [Data("GIF87a".utf8), Data("GIF89a".utf8)].contains(Data(data.prefix(6))) else { throw URLError(.cannotDecodeContentData) }
                filename = "\(pack.id)-\(language)-\(sticker.id).gif"
                guard filename.range(of: #"^[A-Za-z0-9_-]+\.gif$"#, options: .regularExpression) != nil else { throw URLError(.badURL) }
                #if os(iOS)
                let url = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
                try data.write(to: url, options: .atomic)
                shared = SharedFile(url: url)
                #else
                document = GIFDocument(data: data)
                exporting = true
                #endif
            } catch {
                let code = (error as NSError).code
                NSLog("WeSticker GIF save failed (%ld)", code)
                failure = "Check your connection and try again. (\(code))"
            }
        }
    }
}
