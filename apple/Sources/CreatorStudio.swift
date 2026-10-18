import SwiftUI
import PhotosUI
import ImageIO
import UniformTypeIdentifiers
#if os(iOS)
import UIKit
#else
import AppKit
#endif

struct LocalDraft: Codable {
    var name = "My character"
    var title = "My first pack"
    var language = "en"
    var theme = "daily"
    var labels: [String] = []
    var photo: String?
    var rights = false
    var locked = false
}
struct CaptionPlans: Decodable {
    let themes: [String: [String: [String]]]
    let keywords: [String: [String]]
    func match(_ text: String, fallback: String) -> String {
        let lowered = text.lowercased()
        var best = fallback
        var bestCount = 0
        for key in keywords.keys.sorted() {
            let count = keywords[key, default: []].filter { lowered.contains($0.lowercased()) }.count
            if count > bestCount { best = key; bestCount = count }
        }
        return best
    }
}

@MainActor final class CreatorStore: ObservableObject {
    @Published var draft = LocalDraft() { didSet { persist() } }
    @Published var photo: Data?
    @Published var error: String?
    @Published var plan: [String] = []
    @Published var matchedTheme = "daily"
    @Published var brief = ""
    private let root: URL
    private var loaded = false
    let plans: CaptionPlans
    init() {
        root = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("WeStickerStudio", isDirectory: true)
        plans = (try? bundled("creator-plans.json").map { try JSONDecoder().decode(CaptionPlans.self, from: Data(contentsOf: $0)) }) ?? CaptionPlans(themes: [:], keywords: [:])
        do {
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
            let file = root.appendingPathComponent("draft.json")
            if FileManager.default.fileExists(atPath: file.path) {
                draft = try JSONDecoder().decode(LocalDraft.self, from: Data(contentsOf: file))
                if let name = draft.photo, name.range(of: #"^[A-Za-z0-9-]+\.png$"#, options: .regularExpression) != nil {
                    photo = try Data(contentsOf: root.appendingPathComponent(name))
                }
            }
            loaded = true
        } catch { self.error = "The saved draft could not be opened. Its files were preserved." }
        if draft.labels.isEmpty { draft.labels = plans.themes["daily"]?["en"] ?? [] }
    }
    private func persist() {
        guard loaded else { return }
        do {
            try JSONEncoder().encode(draft).write(to: root.appendingPathComponent("draft.json"), options: .atomic)
        } catch { self.error = "Draft could not be saved. Please keep this screen open and try again." }
    }
    func importPhoto(_ data: Data) throws {
        guard data.count <= 20_000_000,
              let source = CGImageSourceCreateWithData(data as CFData, nil),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true, kCGImageSourceThumbnailMaxPixelSize: 1200] as CFDictionary) else { throw CocoaError(.fileReadCorruptFile) }
        let bytes = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(bytes, UTType.png.identifier as CFString, 1, nil) else { throw CocoaError(.fileWriteUnknown) }
        CGImageDestinationAddImage(dest, image, nil)
        guard CGImageDestinationFinalize(dest) else { throw CocoaError(.fileWriteUnknown) }
        let name = UUID().uuidString + ".png"
        try (bytes as Data).write(to: root.appendingPathComponent(name), options: .atomic)
        photo = bytes as Data
        draft.photo = name
        draft.locked = false
        draft.rights = false
    }
    func prepare() {
        matchedTheme = plans.match(brief, fallback: draft.theme)
        plan = plans.themes[matchedTheme]?[draft.language] ?? []
    }
    func applyPlan() {
        guard !plan.isEmpty else { return }
        draft.theme = matchedTheme
        draft.labels = plan
    }
}

struct PNGDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.png] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}

struct StudioRootView: View {
    @StateObject private var store = CreatorStore()
    @StateObject private var cloud = CloudStudioStore()
    @StateObject private var billing = NativeBillingStore()
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var selected = 0
    @State private var authDestination = 1
    @State private var showAuthentication = false
    @State private var showLocalDraft = false
    @State private var openLocalAfterAuthentication = false
    @State private var authenticateAfterLocal = false
    private let labels = ["Stickers", "Create", "Library", "Account"]
    private let symbols = ["face.smiling", "bubble.left.and.bubble.right", "square.stack", "person.crop.circle"]
    var body: some View {
        VStack(spacing: 0) {
            Group {
            switch cloud.signedIn ? selected : 0 {
            case 3: NativeBillingAccountView(cloud: cloud, billing: billing)
            case 1, 2: CloudStudioView(store: cloud, local: store, section: selected, onCreate: { navigate(1) })
            default: CatalogView()
            }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
            VStack(spacing: 0) {
                Divider()
                HStack(spacing: 4) {
                    ForEach(0..<labels.count, id: \.self) { index in
                        Button { navigate(index) } label: {
                            VStack(spacing: 4) {
                                Image(systemName: symbols[index]).font(.system(size: 21))
                                Text(labels[index]).font(.caption)
                            }.frame(maxWidth: .infinity).frame(minHeight: 50)
                                .foregroundStyle(selected == index ? Color.accentColor : .secondary)
                                .background(selected == index ? Color.accentColor.opacity(0.09) : .clear, in: RoundedRectangle(cornerRadius: 8))
                                .animation(reduceMotion ? nil : .easeOut(duration: 0.16), value: selected == index)
                        }.buttonStyle(.plain).accessibilityLabel(labels[index])
                            .accessibilityAddTraits(selected == index ? .isSelected : [])
                    }
                }.padding(.horizontal, 8).padding(.vertical, 6)
            }.background(.background)
        }.task { billing.attach(cloud); cloud.perform { try await cloud.refresh() } }
        .task(id: cloud.billingSessionID) { billing.attach(cloud) }
        .onChange(of: scenePhase) { phase in if phase == .active { billing.attach(cloud); billing.restore() } }
        .onChange(of: cloud.signedIn) { signedIn in
            if signedIn && showAuthentication {
                selected = authDestination; showAuthentication = false
            } else if !signedIn && selected != 0 {
                authDestination = selected; selected = 0; showAuthentication = true
            }
        }
        .sheet(isPresented: $showAuthentication, onDismiss: {
            if openLocalAfterAuthentication { openLocalAfterAuthentication = false; showLocalDraft = true }
        }) {
            StudioLoginView(store: cloud, signIn: { provider in cloud.perform {
                let completed = try await cloud.signIn(provider: provider)
                if !completed { selected = 0; showAuthentication = false }
            } },
                dismiss: { showAuthentication = false }, openLocalDraft: authDestination == 2 ? {
                    openLocalAfterAuthentication = true; showAuthentication = false
                } : nil)
                .interactiveDismissDisabled(cloud.busy)
        }
        .sheet(isPresented: $showLocalDraft, onDismiss: {
            if authenticateAfterLocal { authenticateAfterLocal = false; navigate(1) }
        }) {
            CreatorView(store: store, openAgent: { authenticateAfterLocal = true; showLocalDraft = false },
                close: { showLocalDraft = false })
        }
    }
    private func navigate(_ destination: Int) {
        if destination != 0 && !cloud.signedIn {
            authDestination = destination; selected = 0; showAuthentication = true
        } else { selected = destination }
    }
}

struct PhotoSticker: View {
    let data: Data?
    let label: String
    var body: some View {
        ZStack(alignment: .bottom) {
            if let data { NativeImage(data: data).allowsHitTesting(false).padding(8) }
            else { Image(systemName: "photo").font(.largeTitle).foregroundStyle(.secondary).frame(maxWidth: .infinity, maxHeight: .infinity) }
            Text(label).font(.system(size: 25, weight: .heavy, design: .rounded)).multilineTextAlignment(.center)
                .foregroundStyle(.white).shadow(color: .black, radius: 1, x: 1, y: 1).shadow(color: .black, radius: 1, x: -1, y: -1)
                .padding(12).minimumScaleFactor(0.55).lineLimit(2)
        }.aspectRatio(1, contentMode: .fit).frame(maxWidth: 320)
    }
}

struct CreatorView: View {
    @ObservedObject var store: CreatorStore
    let openAgent: () -> Void
    var close: (() -> Void)? = nil
    @State private var selectedLabel = 0
    @State private var shared: SharedFile?
    @State private var document: PNGDocument?
    @State private var exporting = false
    var body: some View {
        StudioNavigation {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    HStack {
                        Text(store.draft.locked ? "Character locked" : "Private draft").font(.subheadline).foregroundStyle(.secondary)
                        Spacer()
                        Text("On this device").font(.caption).foregroundStyle(.secondary)
                    }
                    HStack(spacing: 16) {
                        if let photo = store.photo { NativeImage(data: photo).frame(width: 96, height: 112).allowsHitTesting(false) }
                        else if let url = bundled("app-icon.png"), let data = try? Data(contentsOf: url) { NativeImage(data: data).frame(width: 96, height: 96).allowsHitTesting(false) }
                        VStack(alignment: .leading, spacing: 10) {
                            TextField("Character name", text: $store.draft.name).textFieldStyle(.roundedBorder)
                            StudioPhotoPicker(title: store.photo == nil ? "Choose photo" : "Replace photo",
                                load: { try store.importPhoto($0) },
                                failed: { store.error = "Choose a supported photo smaller than 20 MB." })
                        }
                    }
                    Toggle("I have permission to use this photo", isOn: $store.draft.rights)
                    Toggle("Keep this character reference", isOn: $store.draft.locked).disabled(store.photo == nil || !store.draft.rights)
                    TextField("Pack title", text: $store.draft.title).textFieldStyle(.roundedBorder)
                    HStack {
                        Picker("Lettering", selection: $store.draft.language) { Text("English").tag("en"); Text("日本語").tag("ja"); Text("中文").tag("zh") }.pickerStyle(.segmented)
                        Button(action: openAgent) { Image(systemName: "bubble.left.and.bubble.right") }.accessibilityLabel("Ask Agent")
                    }
                    ForEach(store.draft.labels.indices, id: \.self) { index in
                        HStack {
                            Button { selectedLabel = index } label: { Image(systemName: selectedLabel == index ? "checkmark.circle.fill" : "circle") }.accessibilityLabel("Preview caption \(index + 1)")
                            TextField("Caption \(index + 1)", text: Binding(get: { store.draft.labels[index] }, set: { store.draft.labels[index] = String($0.prefix(48)) })).textFieldStyle(.roundedBorder)
                        }
                    }
                    if !store.draft.labels.isEmpty {
                        PhotoSticker(data: store.photo, label: store.draft.labels[min(selectedLabel, store.draft.labels.count - 1)])
                            .frame(maxWidth: .infinity).clipped()
                        Button { saveSticker() } label: { Label("Export photo sticker", systemImage: "square.and.arrow.up") }
                            .buttonStyle(.borderedProminent).disabled(store.photo == nil || !store.draft.rights || !store.draft.locked)
                    }
                    Text("Cloud AI: not connected").font(.caption).foregroundStyle(.secondary)
                    if let error = store.error { Text(error).foregroundStyle(.red) }
                }.padding(16).frame(maxWidth: 680)
            }.compactStudioHeader("Create")
                .toolbar {
                    if let close {
                        ToolbarItem(placement: .primaryAction) {
                            Button(action: close) { Image(systemName: "xmark") }.accessibilityLabel("Close local draft")
                        }
                    }
                }
        }
        .onChange(of: store.draft.rights) { if !$0 { store.draft.locked = false } }
        #if os(iOS)
        .sheet(item: $shared) { ShareSheet(url: $0.url) }
        #endif
        .fileExporter(isPresented: $exporting, document: document, contentType: .png, defaultFilename: "westicker-photo.png") { result in
            if case .failure = result { store.error = "Could not export the photo sticker." }
        }
    }
    @MainActor private func saveSticker() {
        guard let data = store.photo, store.draft.locked, store.draft.rights, !store.draft.labels.isEmpty else { return }
        let label = store.draft.labels[min(selectedLabel, store.draft.labels.count - 1)]
        #if os(iOS)
        // UIKit draws the same photo/caption composition without relying on hosted-view snapshots.
        guard let photo = UIImage(data: data) else { return }
        let format = UIGraphicsImageRendererFormat(); format.scale = 1; format.opaque = false
        let rendered = UIGraphicsImageRenderer(size: CGSize(width: 320, height: 320), format: format).image { _ in
            let ratio = min(304 / photo.size.width, 280 / photo.size.height)
            let size = CGSize(width: photo.size.width * ratio, height: photo.size.height * ratio)
            photo.draw(in: CGRect(x: (320-size.width)/2, y: (292-size.height)/2, width: size.width, height: size.height))
            let style = NSMutableParagraphStyle(); style.alignment = .center
            (label as NSString).draw(in: CGRect(x: 8, y: 265, width: 304, height: 54), withAttributes: [.font: UIFont.boldSystemFont(ofSize: label.count > 18 ? 19 : 25), .foregroundColor: UIColor.white, .strokeColor: UIColor.black, .strokeWidth: -5, .paragraphStyle: style])
        }
        guard let bytes = rendered.pngData() else { return }
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("westicker-photo-\(UUID().uuidString).png")
        do { try bytes.write(to: url, options: .atomic); shared = SharedFile(url: url) }
        catch { store.error = "Could not save photo sticker." }
        #else
        guard let source = NSImage(data: data) else { return }
        let image = NSImage(size: NSSize(width: 320, height: 320))
        image.lockFocus()
        let ratio = min(304/source.size.width, 280/source.size.height)
        let size = NSSize(width: source.size.width*ratio, height: source.size.height*ratio)
        source.draw(in: NSRect(x: (320-size.width)/2, y: 28+(280-size.height)/2, width: size.width, height: size.height))
        let style = NSMutableParagraphStyle(); style.alignment = .center
        (label as NSString).draw(in: NSRect(x: 8, y: 2, width: 304, height: 54), withAttributes: [.font: NSFont.boldSystemFont(ofSize: label.count > 18 ? 19 : 25), .foregroundColor: NSColor.white, .strokeColor: NSColor.black, .strokeWidth: -5, .paragraphStyle: style])
        image.unlockFocus()
        guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff), let bytes = bitmap.representation(using: .png, properties: [:]) else { return }
        document = PNGDocument(data: bytes); exporting = true
        #endif
    }
}

struct AgentView: View {
    @ObservedObject var store: CreatorStore
    let openCreate: () -> Void
    @State private var replacing = false
    var body: some View {
        StudioNavigation {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Label("On-device planner", systemImage: "iphone").font(.subheadline).foregroundStyle(.secondary)
                    Text(store.draft.title).font(.title3.bold())
                    StudioMultilineField(title: "Pack brief", text: $store.brief, lines: 3...6)
                    Picker("Theme", selection: $store.draft.theme) {
                        Text("Daily").tag("daily"); Text("Work").tag("office"); Text("Couple").tag("couple"); Text("Sports").tag("sports")
                    }.pickerStyle(.segmented)
                    Button { store.prepare() } label: { Label("Prepare captions", systemImage: "sparkles") }.buttonStyle(.borderedProminent)
                    if !store.plan.isEmpty {
                        Text("\(store.plan.count) captions · \(store.matchedTheme)").font(.headline)
                        ForEach(Array(store.plan.enumerated()), id: \.offset) { _, label in Text(label) }
                        Button { replacing = true } label: { Label("Apply to draft", systemImage: "checkmark") }
                    }
                    Divider()
                    HStack { Text("Cloud AI"); Spacer(); Text("Not connected").foregroundStyle(.secondary) }
                    HStack { Text("WeChat upload"); Spacer(); Text("Not connected").foregroundStyle(.secondary) }
                    if let error = store.error { Text(error).foregroundStyle(.red) }
                }.padding(16).frame(maxWidth: 680)
            }.compactStudioHeader("Agent")
        }
        .confirmationDialog("Replace this draft's captions?", isPresented: $replacing) {
            Button("Apply captions") { store.applyPlan(); openCreate() }
            Button("Cancel", role: .cancel) {}
        }
    }
}
