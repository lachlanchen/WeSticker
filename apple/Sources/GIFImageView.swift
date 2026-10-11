#if os(macOS)
import AppKit
import ImageIO

final class GIFImageView: NSImageView {
    private var source: CGImageSource?
    private var timer: Timer?
    private var frameIndex = 0
    private var delays: [TimeInterval] = []
    private var playing = true

    func setPlaying(_ value: Bool) {
        playing = value
        if value { schedule() } else { stop() }
    }

    func load(_ data: Data) {
        stop()
        source = CGImageSourceCreateWithData(data as CFData, nil)
        frameIndex = 0
        image = nil
        guard let source else { return }
        delays = (0..<CGImageSourceGetCount(source)).map { index in
            let properties = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [String: Any]
            let gif = properties?[kCGImagePropertyGIFDictionary as String] as? [String: Any]
            return max(0.02, gif?[kCGImagePropertyGIFUnclampedDelayTime as String] as? Double
                ?? gif?[kCGImagePropertyGIFDelayTime as String] as? Double ?? 0.08)
        }
        showFrame()
        schedule()
    }

    private func showFrame() {
        guard let source, let pixels = CGImageSourceCreateImageAtIndex(source, frameIndex, nil) else { return }
        image = NSImage(cgImage: pixels, size: .zero)
    }

    private func schedule() {
        guard playing, window != nil, delays.count > 1, timer == nil else { return }
        let next = Timer(timeInterval: delays[frameIndex], repeats: false) { [weak self] _ in
            guard let self else { return }
            self.timer = nil
            self.frameIndex = (self.frameIndex + 1) % self.delays.count
            self.showFrame()
            self.schedule()
        }
        timer = next
        // Continue while the user scrolls or opens a menu, without retaining the view.
        RunLoop.main.add(next, forMode: .common)
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        if window == nil { stop() } else { schedule() }
    }

    deinit { timer?.invalidate() }
}
#endif
