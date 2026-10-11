import SwiftUI

private struct CompactStudioHeader: ViewModifier {
    let title: String
    private var leading: ToolbarItemPlacement {
        #if os(iOS)
        return .navigationBarLeading
        #else
        return .navigation
        #endif
    }
    func body(content: Content) -> some View {
        content.navigationTitle("")
            .toolbar {
                ToolbarItem(placement: leading) {
                    Text(title).font(.headline).lineLimit(1).truncationMode(.tail)
                        .fixedSize(horizontal: true, vertical: false)
                        .accessibilityAddTraits(.isHeader)
                        .accessibilityIdentifier("studio-toolbar-title")
                }
            }
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
    }
}

extension View {
    func compactStudioHeader(_ title: String) -> some View {
        modifier(CompactStudioHeader(title: title))
    }
}

struct StudioChatWelcome: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var appeared = false
    var body: some View {
        VStack(spacing: 12) {
            if let url = bundled("app-icon.png"), let data = try? Data(contentsOf: url) {
                NativeImage(data: data).frame(width: 44, height: 44)
                    .clipShape(RoundedRectangle(cornerRadius: 8)).accessibilityHidden(true)
            }
            Text("What shall we make?").font(.headline).multilineTextAlignment(.center)
        }
        .accessibilityIdentifier("chat-welcome")
        .opacity(appeared || reduceMotion ? 1 : 0)
        .offset(y: appeared || reduceMotion ? 0 : 6)
        .onAppear {
            withAnimation(reduceMotion ? nil : .easeOut(duration: 0.22)) { appeared = true }
        }
    }
}
