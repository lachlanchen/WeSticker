import SwiftUI
import PhotosUI
import CryptoKit
import Security
import ImageIO
import UniformTypeIdentifiers

struct StudioRow: Codable, Identifiable {
    var id: String; var label: String; var action: String?; var asset: String?; var approved: Bool
}
struct StudioPack: Codable, Identifiable {
    var id: String; var title: String; var items: [StudioRow]; var revision: Int; var character_id: String
}
struct StudioCharacter: Codable, Identifiable {
    var id: String; var name: String; var refs: [String]; var locked: Bool
}
struct StudioJob: Codable, Identifiable {
    var id: String; var pack_id: String; var kind: String; var state: String; var progress: Int; var error: String?
}
struct StudioLimits: Codable {
    var plan: String; var pack_size: Int; var packs: Int; var characters: Int; var credits: Int; var trial_images: Int; var animation: Bool
}
struct StudioWorkspace: Codable {
    var packs: [StudioPack]; var characters: [StudioCharacter]; var jobs: [StudioJob]; var limits: StudioLimits
}
struct StudioProposal: Codable { var reply: String; var items: [StudioRow]?; var revision: Int? }
struct StudioMessage: Codable, Identifiable { var id: String; var text: String; var state: String; var result: StudioProposal? }
struct StudioQuote: Codable { var credits: Int; var revision: Int; var kind: String; var items: [String]; var can_generate: Bool; var reason: String? }

private enum StudioSecret {
    static func query(_ origin: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "art.lazying.westicker.studio", kSecAttrAccount as String: origin]
    }
    static func read(_ origin: String) -> String {
        var q = query(origin); q[kSecReturnData as String] = true
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess, let data = item as? Data else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }
    static func write(_ token: String, _ origin: String) {
        let q = query(origin); SecItemDelete(q as CFDictionary)
        guard !token.isEmpty else { return }
        var value = q; value[kSecValueData as String] = Data(token.utf8)
        value[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(value as CFDictionary, nil)
    }
}

@MainActor final class CloudStudioStore: ObservableObject {
    @Published var origin = UserDefaults.standard.string(forKey: "studio-origin") ?? "https://westicker.lazying.art"
    @Published var workspace: StudioWorkspace?
    @Published var current: StudioPack?
    @Published var rows: [StudioRow] = [] { didSet { quote = nil } }
    @Published var selected: Set<String> = [] { didSet { quote = nil } }
    @Published var messages: [StudioMessage] = []
    @Published var quote: StudioQuote?
    @Published var error: String?
    @Published var busy = false
    @Published var dirty = false
    @Published var signedIn = false
    @Published var needsConsent = false
    @Published var capabilities: [String: Bool] = [:]
    @Published var refs: [String] = [] { didSet { pendingCharacter = "" } }
    @Published var pendingCharacter = ""
    private var csrf = ""
    private var linkedOrigin = ""
    private var link: (String, String)?
    private let network = URLSession(configuration: .ephemeral)

    func validatedOrigin() throws -> String {
        let value = origin.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let url = URL(string: value), url.host != nil, url.user == nil, url.password == nil,
              url.path.isEmpty, url.query == nil, url.fragment == nil,
              url.scheme == "https" || (url.scheme == "http" && ["localhost", "127.0.0.1"].contains(url.host ?? "")) else {
            throw NSError(domain: "Studio", code: 1, userInfo: [NSLocalizedDescriptionKey: "Enter your HTTPS creator-service origin."])
        }
        return value
    }
    func request(_ path: String, _ body: [String: Any]? = nil, method: String? = nil) async throws -> Data {
        let base = try validatedOrigin()
        var req = URLRequest(url: URL(string: base + path)!)
        req.httpMethod = method ?? (body == nil ? "GET" : "POST"); req.timeoutInterval = 100
        req.setValue(base, forHTTPHeaderField: "Origin")
        let token = StudioSecret.read(base)
        if !token.isEmpty { req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        if !csrf.isEmpty { req.setValue(csrf, forHTTPHeaderField: "X-CSRF-Token") }
        if let body { req.httpBody = try JSONSerialization.data(withJSONObject: body); req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await network.data(for: req)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            throw NSError(domain: "Studio", code: (response as? HTTPURLResponse)?.statusCode ?? 0, userInfo: [NSLocalizedDescriptionKey: value?["error"] as? String ?? "The creator service could not complete this request."])
        }
        return data
    }
    func json(_ data: Data) throws -> [String: Any] { try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:] }
    func payload(_ rows: [StudioRow]) throws -> [[String: Any]] { try JSONSerialization.jsonObject(with: JSONEncoder().encode(rows)) as? [[String: Any]] ?? [] }
    func perform(_ operation: @escaping () async throws -> Void) {
        guard !busy else { return }; busy = true; error = nil
        Task { do { try await operation() } catch { self.error = error.localizedDescription }; busy = false }
    }
    func refresh() async throws {
        let base = try validatedOrigin()
        if linkedOrigin != base { workspace = nil; current = nil; rows = []; messages = []; refs = []; dirty = false; csrf = ""; linkedOrigin = base }
        let boot = try json(await request("/api/bootstrap")); csrf = boot["csrf"] as? String ?? ""
        capabilities = boot["capabilities"] as? [String: Bool] ?? [:]
        let user = boot["user"] as? [String: Any]
        signedIn = user != nil
        needsConsent = signedIn && (user?["consented"] as? NSNumber)?.boolValue != true
        guard signedIn else { workspace = nil; current = nil; rows = []; selected = []; messages = []; refs = []; dirty = false; return }
        guard !needsConsent else { workspace = nil; return }
        let next = try JSONDecoder().decode(StudioWorkspace.self, from: await request("/api/workspace"))
        workspace = next
        if !dirty, let id = current?.id, let p = next.packs.first(where: { $0.id == id }) { current = p; rows = p.items }
        UserDefaults.standard.set(base, forKey: "studio-origin")
    }
    func acceptTerms() async throws {
        _ = try await request("/api/account/consent", ["adult": true, "terms": true])
        try await refresh()
    }
    func startLogin() async throws -> URL {
        _ = try validatedOrigin(); try await refresh()
        let verifier = UUID().uuidString.replacingOccurrences(of: "-", with: "") + UUID().uuidString.replacingOccurrences(of: "-", with: "")
        let digest = Data(SHA256.hash(data: Data(verifier.utf8))).base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
        let result = try json(await request("/api/native/link", ["challenge": digest]))
        guard let id = result["id"] as? String, let address = result["url"] as? String, let url = URL(string: address) else { throw URLError(.badServerResponse) }
        link = (id, verifier); return url
    }
    func finishLogin() async throws {
        guard let (id, verifier) = link else { try await refresh(); return }
        let result = try json(await request("/api/native/link/\(id)/exchange", ["verifier": verifier]))
        guard let token = result["token"] as? String else { error = "Approve Connect device in your browser, then check again."; return }
        StudioSecret.write(token, try validatedOrigin()); link = nil; try await refresh()
    }
    func signOut() async throws {
        _ = try await request("/api/auth/logout", [:])
        StudioSecret.write("", try validatedOrigin()); csrf = ""; signedIn = false; workspace = nil; current = nil; rows = []; selected = []; messages = []; refs = []; dirty = false; link = nil
    }
    func open(_ p: StudioPack) async throws {
        current = p; rows = p.items; selected = Set(p.items.prefix(1).map(\.id)); dirty = false; quote = nil
        try await loadMessages(p.id)
    }
    private func loadMessages(_ id: String) async throws {
        struct Result: Decodable { var messages: [StudioMessage] }
        messages = try JSONDecoder().decode(Result.self, from: await request("/api/packs/\(id)/conversation")).messages
    }
    func save(_ proposed: [StudioRow]? = nil, revision: Int? = nil) async throws {
        guard let p = current else { return }
        _ = try await request("/api/packs/\(p.id)", ["items": payload(proposed ?? rows), "revision": revision ?? p.revision], method: "PATCH")
        dirty = false; try await refresh(); quote = nil
    }
    func chat(_ text: String) async throws {
        guard let p = current else { return }
        _ = try await request("/api/packs/\(p.id)/chat", ["text": text, "attempt": UUID().uuidString])
        try await loadMessages(p.id)
    }
    func getQuote(_ kind: String) async throws {
        guard let p = current else { return }
        quote = try JSONDecoder().decode(StudioQuote.self, from: await request("/api/packs/\(p.id)/quote", ["kind": kind, "items": selected.sorted()]))
    }
    func generate() async throws {
        guard let p = current, let quote else { return }
        let key = "studio-attempt-\(linkedOrigin)-\(p.id)-\(quote.kind)-\(quote.revision)-\(quote.items.joined())"
        let attempt = UserDefaults.standard.string(forKey: key) ?? UUID().uuidString
        UserDefaults.standard.set(attempt, forKey: key)
        _ = try await request("/api/packs/\(p.id)/generate", ["kind": quote.kind, "items": quote.items, "revision": quote.revision, "attempt": attempt, "consent": true])
        self.quote = nil; try await refresh()
    }
    func upload(_ input: Data) async throws {
        guard input.count <= 20_000_000,
              let source = CGImageSourceCreateWithData(input as CFData, nil),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceThumbnailMaxPixelSize: 1600, kCGImageSourceCreateThumbnailWithTransform: true] as CFDictionary) else { throw URLError(.cannotDecodeContentData) }
        let buffer = NSMutableData()
        guard let target = CGImageDestinationCreateWithData(buffer, UTType.png.identifier as CFString, 1, nil) else { throw URLError(.cannotDecodeContentData) }
        CGImageDestinationAddImage(target, image, nil)
        guard CGImageDestinationFinalize(target) else { throw URLError(.cannotDecodeContentData) }
        let data = buffer as Data
        guard data.count <= 20_000_000, refs.count < 5 else { throw URLError(.dataLengthExceedsMaximum) }
        let base = try validatedOrigin(), boundary = UUID().uuidString
        var body = Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"rights\"\r\n\r\nyes\r\n--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"reference.png\"\r\nContent-Type: image/png\r\n\r\n".utf8)
        body.append(data); body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        var req = URLRequest(url: URL(string: base + "/api/assets")!)
        req.httpMethod = "POST"; req.httpBody = body; req.timeoutInterval = 100
        req.setValue(base, forHTTPHeaderField: "Origin"); req.setValue(csrf, forHTTPHeaderField: "X-CSRF-Token")
        req.setValue("Bearer " + StudioSecret.read(base), forHTTPHeaderField: "Authorization")
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        let (result, response) = try await network.data(for: req); let value = try json(result)
        guard (response as? HTTPURLResponse)?.statusCode == 201, let id = value["id"] as? String else {
            throw NSError(domain: "Studio", code: 1, userInfo: [NSLocalizedDescriptionKey: value["error"] as? String ?? "Reference upload failed."])
        }
        refs.append(id)
    }
    func create(name: String, title: String, language: String, character: String) async throws {
        var id = character.isEmpty ? pendingCharacter : character
        if id.isEmpty { let result = try json(await request("/api/characters", ["name": name, "style": "figurine", "refs": refs])); id = result["id"] as? String ?? "" }
        pendingCharacter = id
        _ = try await request("/api/characters/\(id)/lock", ["approved": true])
        let result = try json(await request("/api/packs", ["character": id, "title": title, "language": language, "theme": "daily"]))
        try await refresh()
        if let p = workspace?.packs.first(where: { $0.id == result["id"] as? String }) { try await open(p) }
        pendingCharacter = ""
    }
    var blocked: Bool { workspace?.jobs.contains(where: { $0.pack_id == current?.id && ["queued", "running", "uncertain"].contains($0.state) }) ?? false }
}

struct StudioAsset: View {
    @ObservedObject var store: CloudStudioStore
    let id: String
    @State private var data: Data?
    @Environment(\.accessibilityReduceMotion) private var reduced
    var body: some View {
        Group { if let data { NativeImage(data: data, playing: !reduced) } else { Image(systemName: "photo").foregroundStyle(.secondary) } }
            .task(id: id) { data = try? await store.request("/api/assets/" + id + "?preview=1") }
    }
}

struct CloudStudioView: View {
    @ObservedObject var store: CloudStudioStore
    @ObservedObject var local: CreatorStore
    var section: Int = 1
    var onCreate: () -> Void
    @Environment(\.openURL) private var openURL
    @State private var text = ""
    @State private var name = "My character"
    @State private var title = "Everyday moments"
    @State private var language = "en"
    @State private var character = ""
    @State private var rights = false
    @State private var creating = false
    @State private var picked: PhotosPickerItem?
    @State private var showLocal = false
    @State private var exportURL: URL?
    @State private var showHistory = false
    @State private var history: [StudioRow] = []
    @State private var termsAccepted = false
    @State private var showServiceSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let error = store.error { Text(error).foregroundStyle(.red).accessibilityIdentifier("studio-error") }
                    if !store.signedIn { signInView }
                    else if store.needsConsent {
                        Text("Before your first creation").font(.title2.bold())
                        Link("Creator terms", destination: URL(string: store.origin + "/terms.html")!)
                        Link("Privacy policy", destination: URL(string: store.origin + "/privacy.html")!)
                        Toggle("I am 18 or older and accept the creator terms", isOn: $termsAccepted)
                        Button("Continue") { store.perform { try await store.acceptTerms() } }.disabled(!termsAccepted)
                    }
                    else if let w = store.workspace {
                        Text("\(w.limits.plan.capitalized) · \(w.limits.credits) credits · \(w.limits.pack_size) per creation").font(.caption).foregroundStyle(.secondary)
                        if section == 2 { libraryView(w) }
                        else if section == 3 { charactersView(w) }
                        else if creating || store.current == nil { creationForm(w) }
                        else if let p = store.current { editor(p, w) }
                    }
                    if store.busy { ProgressView() }
                }.padding().frame(maxWidth: 850, alignment: .leading).frame(maxWidth: .infinity)
            }.navigationTitle(section == 2 ? "Library" : section == 3 ? "Characters" : "Create")
            .toolbar { ToolbarItemGroup {
                Button { store.perform { try await store.refresh() } } label: { Image(systemName: "arrow.clockwise") }
                if store.signedIn {
                    Button { creating = true; onCreate() } label: { Image(systemName: "plus") }
                    Button("Sign out") { store.perform { try await store.signOut() } }
                }
            } }.disabled(store.busy)
            .sheet(isPresented: $showLocal) { NavigationStack {
                CreatorView(store: local, openAgent: { showLocal = false })
                    .toolbar { Button("Close local draft") { showLocal = false } }
            } }
            .sheet(isPresented: $showHistory) { ScrollView { VStack {
                Text("Preserved versions").font(.headline)
                ForEach(Array(history.enumerated()), id: \.offset) { _, row in if let id = row.asset { StudioAsset(store: store, id: id).frame(width: 150, height: 150); Text(row.label) } }
                Button("Close") { showHistory = false }
            }.padding() }.frame(minWidth: 280, minHeight: 300) }
            .onChange(of: picked) { value in if let value { store.perform {
                if let data = try await value.loadTransferable(type: Data.self) { try await store.upload(data) }
            } } }
            .task {
                if !store.origin.isEmpty { store.perform { try await store.refresh() } }
                while !Task.isCancelled {
                    try? await Task.sleep(nanoseconds: 4_000_000_000)
                    if !store.busy && store.workspace?.jobs.contains(where: { ["queued", "running"].contains($0.state) }) == true { try? await store.refresh() }
                }
            }
        }
    }
    private var signInView: some View { Group {
        Text("Your own little cast").font(.title2.bold())
        DisclosureGroup("Service settings", isExpanded: $showServiceSettings) {
            TextField("HTTPS creator service", text: $store.origin).textFieldStyle(.roundedBorder).autocorrectionDisabled()
        }
        Button("Sign in with browser") { store.perform { openURL(try await store.startLogin()) } }
        Button("I connected my account") { store.perform { try await store.finishLogin() } }
        Button("Open saved local photo draft") { showLocal = true }
    } }
    @ViewBuilder private func libraryView(_ w: StudioWorkspace) -> some View {
        ForEach(w.packs) { p in
            Button { store.perform { try await store.open(p); creating = false; onCreate() } } label: {
                VStack(alignment: .leading) { Text(p.title).font(.headline); HStack {
                    ForEach(p.items.filter { $0.asset != nil }.prefix(4)) { row in StudioAsset(store: store, id: row.asset!).frame(width: 64, height: 64) }
                }; Text("\(p.items.count) stickers").font(.caption) }
            }.buttonStyle(.plain); Divider()
        }
        Button("Open saved local photo draft") { showLocal = true }
    }
    @ViewBuilder private func charactersView(_ w: StudioWorkspace) -> some View {
        ForEach(w.characters) { c in
            Text(c.name).font(.headline)
            ScrollView(.horizontal) { HStack { ForEach(c.refs, id: \.self) { id in StudioAsset(store: store, id: id).frame(width: 70, height: 70) } } }
            Button("Create with \(c.name)") { character = c.id; creating = true; onCreate() }; Divider()
        }
    }
    @ViewBuilder private func creationForm(_ w: StudioWorkspace) -> some View {
        Text("Who are we creating?").font(.title2.bold())
        Picker("Character", selection: $character) { Text("New character").tag(""); ForEach(w.characters) { Text($0.name).tag($0.id) } }
        if character.isEmpty {
            TextField("Character name", text: $name).textFieldStyle(.roundedBorder)
            Toggle("I have permission to use these references", isOn: $rights)
            PhotosPicker(selection: $picked, matching: .images) { Label("Upload reference (\(store.refs.count)/5)", systemImage: "photo.badge.plus") }.disabled(!rights || store.refs.count >= 5)
            ScrollView(.horizontal) { HStack { ForEach(store.refs, id: \.self) { id in VStack { StudioAsset(store: store, id: id).frame(width: 65, height: 65); Button { store.refs.removeAll { $0 == id } } label: { Image(systemName: "xmark.circle") } } } } }
        }
        TextField("Collection name", text: $title).textFieldStyle(.roundedBorder)
        Picker("Lettering", selection: $language) { Text("English").tag("en"); Text("中文").tag("zh"); Text("日本語").tag("ja") }
        Button("Approve references & start") { store.perform { try await store.create(name: name, title: title, language: language, character: character); creating = false } }.disabled(character.isEmpty && (!rights || store.refs.isEmpty))
    }
    @ViewBuilder private func editor(_ p: StudioPack, _ w: StudioWorkspace) -> some View {
        Text(p.title).font(.title2.bold())
        ForEach(store.messages) { m in
            Text(m.text).padding(10).frame(maxWidth: .infinity, alignment: .trailing).background(Color.cyan.opacity(0.1)).clipShape(RoundedRectangle(cornerRadius: 8))
            if let result = m.result {
                Text(result.reply)
                if let proposed = result.items {
                    ForEach(proposed) { row in VStack(alignment: .leading) { Text(row.label).bold(); Text(row.action ?? "").font(.caption).foregroundStyle(.secondary) }; Divider() }
                    Button("Apply table") { store.perform { try await store.save(proposed, revision: result.revision) } }.disabled(store.dirty || store.blocked || result.revision != p.revision)
                }
            }
        }
        HStack(alignment: .bottom) {
            TextField("Message your sticker assistant", text: $text, axis: .vertical).lineLimit(2...5).textFieldStyle(.roundedBorder)
            Button { let message = text; store.perform { try await store.chat(message); text = "" } } label: { Image(systemName: "arrow.up.circle.fill").font(.title) }.accessibilityLabel("Send message").disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.dirty || store.blocked)
        }
        Divider(); Text("Sticker plan").font(.headline)
        ForEach(store.rows.indices, id: \.self) { index in rowEditor(index) }
        HStack {
            Button { store.rows.append(StudioRow(id: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(), label: "Hello", approved: false)); store.dirty = true } label: { Label("Add word", systemImage: "plus") }.disabled(store.rows.count >= w.limits.pack_size || store.blocked)
            Button("Save table") { store.perform { try await store.save() } }.disabled(!store.dirty || store.blocked)
        }
        ForEach(w.jobs.filter { $0.pack_id == p.id }.prefix(3)) { job in
            Text("\(job.kind) · \(job.state)").font(.caption); ProgressView(value: Double(job.progress), total: 100)
            if let error = job.error { Text(error).font(.caption).foregroundStyle(.red) }
        }
        VStack(alignment: .leading) {
            Button("Use uploaded photo") { store.perform { try await store.getQuote("photo") } }
            Button("Generate references") { store.perform { try await store.getQuote("ai") } }.disabled(store.capabilities["ai_images"] != true)
            Button("Animate approved") { store.perform { try await store.getQuote("animate") } }.disabled(store.capabilities["animation"] != true)
        }.disabled(store.dirty || store.blocked || store.selected.isEmpty)
        if store.capabilities["ai_images"] != true { Text("AI image generation is unavailable on this service. Photo creations and saved drafts remain available.").font(.caption).foregroundStyle(.secondary) }
        if let quote = store.quote {
            Text("\(quote.items.count) sticker(s) · \(quote.credits) credits").bold()
            if let reason = quote.reason { Text(reason).font(.caption) }
            Button("Confirm generation") { store.perform { try await store.generate() } }.disabled(!quote.can_generate)
            Button("Cancel") { store.quote = nil }
        }
        Button("Export reviewed ZIP") { store.perform {
            let data = try await store.request("/api/packs/\(p.id)/export")
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("WeSticker-\(UUID().uuidString).zip")
            try data.write(to: url, options: .atomic); exportURL = url
        } }.disabled(store.dirty || store.rows.contains { !$0.approved })
        if let exportURL { ShareLink(item: exportURL) { Label("Save or share ZIP", systemImage: "square.and.arrow.up") } }
        Button("Version history") { store.perform {
            let result = try store.json(await store.request("/api/packs/\(p.id)/versions"))
            history = try (result["versions"] as? [[String: Any]] ?? []).flatMap { version in try JSONDecoder().decode([StudioRow].self, from: JSONSerialization.data(withJSONObject: version["items"] ?? [])) }
            showHistory = true
        } }
    }
    @ViewBuilder private func rowEditor(_ index: Int) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Toggle("Select \(index + 1)", isOn: Binding(get: { store.selected.contains(store.rows[index].id) }, set: { if $0 { store.selected.insert(store.rows[index].id) } else { store.selected.remove(store.rows[index].id) } })).labelsHidden().toggleStyle(.switch).frame(width: 45)
            VStack(alignment: .leading) {
                TextField("Caption \(index + 1)", text: Binding(get: { store.rows[index].label }, set: { store.rows[index].label = String($0.prefix(32)); store.rows[index].approved = false; store.dirty = true })).textFieldStyle(.roundedBorder)
                TextField("Action \(index + 1)", text: Binding(get: { store.rows[index].action ?? "" }, set: { store.rows[index].action = String($0.prefix(500)); store.rows[index].approved = false; store.dirty = true }), axis: .vertical).lineLimit(2...4).textFieldStyle(.roundedBorder)
                if let id = store.rows[index].asset { StudioAsset(store: store, id: id).frame(width: 110, height: 110); Toggle("Approve reference", isOn: Binding(get: { store.rows[index].approved }, set: { store.rows[index].approved = $0; store.dirty = true })) }
            }
            Button { store.selected.remove(store.rows[index].id); store.rows.remove(at: index); store.dirty = true } label: { Image(systemName: "trash") }.disabled(store.rows.count <= 1)
        }.disabled(store.blocked); Divider()
    }
}
