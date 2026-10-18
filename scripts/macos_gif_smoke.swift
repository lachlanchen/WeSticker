import AppKit

@main
struct GIFSmoke {
    static func main() throws {
        let app = NSApplication.shared
        let offscreen = CommandLine.arguments.contains("--offscreen")
        app.setActivationPolicy(offscreen ? .prohibited : .accessory)
        let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let window = NSWindow(contentRect: NSRect(x: 80, y: 80, width: 260, height: 260), styleMask: [.titled], backing: .buffered, defer: false)
        window.title = "WeSticker playback test"
        let view = GIFImageView(frame: NSRect(x: 0, y: 0, width: 260, height: 260))
        view.imageScaling = .scaleProportionallyUpOrDown
        window.contentView = view
        if !offscreen { window.orderFrontRegardless() }
        defer { view.stop(); window.orderOut(nil) }
        view.load(data)
        func samples(_ phase: String) throws -> Int {
            var unique = Set<Data>()
            for index in 0..<8 {
                RunLoop.current.run(until: Date().addingTimeInterval(0.27))
                let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds)!
                view.cacheDisplay(in: view.bounds, to: rep)
                let png = rep.representation(using: .png, properties: [:])!
                unique.insert(png)
                try png.write(to: output.appendingPathComponent("\(phase)-\(index).png"))
            }
            return unique.count
        }
        let playing = try samples("playing")
        // The app switches to a static poster when paused.
        let poster = NSBitmapImageRep(data: data)!.representation(using: .png, properties: [:])!
        view.load(poster)
        let paused = try samples("paused")
        view.load(data)
        let resumed = try samples("resumed")
        precondition(playing > 1 && paused == 1 && resumed > 1, "GIF pixels must play, pause and resume")
        let result: [String: Any] = ["playing_frames": playing, "paused_frames": paused, "resumed_frames": resumed, "native_appkit": true, "offscreen": offscreen]
        let json = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        try json.write(to: output.appendingPathComponent("result.json"))
        print(String(decoding: json, as: UTF8.self))
    }
}
