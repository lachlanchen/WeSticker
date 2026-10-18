import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct StudioNavigation<Content: View>: View {
    @ViewBuilder let content: () -> Content
    var body: some View {
        if #available(macOS 13.0, *) {
            NavigationStack { content() }
        } else {
            NavigationView { content() }
        }
    }
}

struct StudioMultilineField: View {
    let title: String
    @Binding var text: String
    var lines: ClosedRange<Int> = 1...5

    var body: some View {
        if #available(macOS 13.0, *) {
            TextField(title, text: $text, axis: .vertical)
                .lineLimit(lines).textFieldStyle(.roundedBorder)
        } else {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.caption).foregroundStyle(.secondary)
                TextEditor(text: $text)
                    .frame(minHeight: CGFloat(max(2, lines.lowerBound)) * 20,
                           maxHeight: CGFloat(lines.upperBound) * 24)
                    .accessibilityLabel(title)
                    .overlay(RoundedRectangle(cornerRadius: 5).stroke(Color.secondary.opacity(0.25)))
            }
        }
    }
}

struct StudioPhotoPicker: View {
    let title: String
    let load: @MainActor (Data) async throws -> Void
    let failed: @MainActor () -> Void
    @State private var importing = false
    @State private var loading = false

    var body: some View {
        Group {
            if #available(macOS 13.0, *) {
                ModernStudioPhotoPicker(title: title, load: load, failed: failed)
            } else {
                Button { importing = true } label: {
                    Label(title, systemImage: "photo.badge.plus")
                }.disabled(loading)
                    .fileImporter(isPresented: $importing, allowedContentTypes: [.image]) { result in
                        guard case let .success(url) = result else { return }
                        loading = true
                        Task { @MainActor in
                            defer { loading = false }
                            let scoped = url.startAccessingSecurityScopedResource()
                            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                            do {
                                let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
                                guard size <= 20_000_000 else { throw CocoaError(.fileReadTooLarge) }
                                try await load(Data(contentsOf: url))
                            } catch { failed() }
                        }
                    }
            }
        }
    }
}

@available(macOS 13.0, *)
private struct ModernStudioPhotoPicker: View {
    let title: String
    let load: @MainActor (Data) async throws -> Void
    let failed: @MainActor () -> Void
    @State private var picked: PhotosPickerItem?
    @State private var loading = false

    var body: some View {
        PhotosPicker(selection: $picked, matching: .images) {
            Label(title, systemImage: "photo.badge.plus")
        }.disabled(loading)
            .onChange(of: picked) { item in
                guard let item else { return }
                loading = true
                Task { @MainActor in
                    defer { loading = false; picked = nil }
                    do {
                        guard let data = try await item.loadTransferable(type: Data.self),
                              data.count <= 20_000_000 else { throw CocoaError(.fileReadTooLarge) }
                        try await load(data)
                    } catch { failed() }
                }
            }
    }
}

private struct ZIPDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.zip] }
    let data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws {
        data = configuration.file.regularFileContents ?? Data()
    }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}

struct StudioShareZIP: View {
    let url: URL
    @State private var document: ZIPDocument?
    @State private var exporting = false
    @State private var failed = false

    var body: some View {
        if #available(macOS 13.0, *) {
            ShareLink(item: url) { Label("Save or share ZIP", systemImage: "square.and.arrow.up") }
        } else {
            Button {
                do { document = ZIPDocument(data: try Data(contentsOf: url)); exporting = true }
                catch { failed = true }
            } label: { Label("Save ZIP", systemImage: "square.and.arrow.up") }
                .fileExporter(isPresented: $exporting, document: document, contentType: .zip,
                              defaultFilename: url.lastPathComponent) { result in
                    if case .failure = result { failed = true }
                }
                .alert("Could not save ZIP", isPresented: $failed) {
                    Button("OK", role: .cancel) {}
                }
        }
    }
}

// AnyLayout keeps the sticker grid and its presentation state alive while a
// window changes shape. The Monterey fallback has a conventional split layout.
struct StudioCatalogLayout<Navigation: View, Content: View>: View {
    let sidebar: Bool
    let navigationHeight: CGFloat
    @ViewBuilder let navigation: () -> Navigation
    @ViewBuilder let content: () -> Content

    var body: some View {
        if #available(macOS 13.0, *) {
            let layout = sidebar ? AnyLayout(HStackLayout(alignment: .top, spacing: 16))
                                 : AnyLayout(VStackLayout(spacing: 12))
            layout {
                navigation().frame(width: sidebar ? 210 : nil, height: sidebar ? nil : navigationHeight)
                content().frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        } else {
            HStack(alignment: .top, spacing: 16) {
                navigation().frame(width: 210)
                content().frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}
