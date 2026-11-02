import Foundation

// Swift port of src/ipodfw/accent.py. The two versions use the same steps and the same rounding.
//
// Apple's firmware uses one blue for the selection bar of the Views and for some pictures. This
// code changes that blue to the accent colour of the owner. The accent #5898e8 is Apple's blue:
// with it nothing changes.

public enum Accent {
    public static let apple = "#5898e8"
    static let appleTop: [UInt8] = [0x58, 0x98, 0xE8, 0xFF]
    static let appleBottom: [UInt8] = [0x28, 0x64, 0xD0, 0xFF]
    /// The pictures of Apple's firmware 1.3 that hold the accent blue.
    static let pictures: Set<Int> = [13981, 13982, 24279, 24403, 24404, 24405, 24406, 24407, 24408, 24409,
                                     25043, 25045, 25046, 25560, 25562,
                                     24361, 24362, 24363, 24364, 24365, 24366,
                                     22206, 24394]
    static let satMin = 0.35, valMin = 0.15
    /// The largest channel of the top colour of the selection bar. Apple's blue has 232 (0xe8). The owner saw
    /// yellow pixels at the top of a red bar (255, 69, 58): the code that draws the bar needs room above the colour.
    static let maxChannel = 232

    /// Colours that the owner can select quickly. The first is Apple's blue.
    public static let presets: [(name: String, hex: String)] = [
        ("Blue", apple), ("Red", "#ff453a"), ("Orange", "#ff9f0a"), ("Green", "#30d158"),
        ("Teal", "#40c8e0"), ("Purple", "#bf5af2"), ("Pink", "#ff6482"),
    ]

    public static func parseHex(_ text: String) throws -> (r: Int, g: Int, b: Int) {
        var s = text.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6, let v = Int(s, radix: 16) else {
            throw ThemeError("The accent colour must have the form #RRGGBB, not \"\(text)\".")
        }
        return (v >> 16 & 255, v >> 8 & 255, v & 255)
    }

    public static func isApple(_ text: String) -> Bool {
        guard let a = try? parseHex(text), let b = try? parseHex(apple) else { return false }
        return a == b
    }

    /// The bottom and the top colour of the selection bar (RGBA bytes).
    static func words(_ text: String) throws -> (bottom: [UInt8], top: [UInt8]) {
        let (r, g, b) = try parseHex(text)
        if isApple(text) { return (appleBottom, appleTop) }
        var c = [r, g, b]
        let top = c.max()!
        if top > maxChannel { c = c.map { Int(Double($0) * Double(maxChannel) / Double(top) + 0.5) } }
        return (c.map { UInt8(Double($0) * 0.8) } + [255], c.map { UInt8($0) } + [255])
    }

    static func mod(_ x: Double, _ m: Double) -> Double {
        let r = fmod(x, m)
        return r < 0 ? r + m : r
    }

    static func rgbToHSV(_ r: Int, _ g: Int, _ b: Int) -> (h: Double, s: Double, v: Double) {
        let rf = Double(r) / 255.0, gf = Double(g) / 255.0, bf = Double(b) / 255.0
        let mx = max(rf, gf, bf), mn = min(rf, gf, bf)
        let df = mx - mn
        var h = 0.0
        if df > 1e-9 {
            if mx == rf { h = mod((gf - bf) / df, 6.0) / 6.0 }
            else if mx == gf { h = ((bf - rf) / df + 2.0) / 6.0 }
            else { h = ((rf - gf) / df + 4.0) / 6.0 }
            h = mod(h, 1.0)
        }
        return (h, mx > 0 ? df / mx : 0.0, mx)
    }

    static func hsvToRGB(_ h: Double, _ s: Double, _ v: Double) -> (Double, Double, Double) {
        let hh = floor(h * 6.0)
        let i = Int(hh) % 6
        let f = h * 6.0 - hh
        let p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s)
        let c: (Double, Double, Double)
        switch i {
        case 0: c = (v, t, p)
        case 1: c = (q, v, p)
        case 2: c = (p, v, t)
        case 3: c = (p, q, v)
        case 4: c = (t, p, v)
        default: c = (v, p, q)
        }
        return (c.0 * 255.0, c.1 * 255.0, c.2 * 255.0)
    }

    static func byte(_ x: Double) -> Int { min(255, max(0, Int(floor(x + 0.5)))) }

    /// The change from Apple's blue to the accent.
    struct Tint {
        var hue, sat, val: Double

        init(_ text: String) throws {
            let a = try parseHex(Accent.apple)
            let base = rgbToHSV(a.r, a.g, a.b)
            let c = try parseHex(text)
            let target = rgbToHSV(c.r, c.g, c.b)
            hue = target.h - base.h
            sat = target.s / max(base.s, 1e-6)
            val = target.v / max(base.v, 1e-6)
        }

        func pixel(_ r: Int, _ g: Int, _ b: Int) -> (Int, Int, Int) {
            let (h, s, v) = rgbToHSV(r, g, b)
            guard s > Accent.satMin && v > Accent.valMin else { return (r, g, b) }
            let o = hsvToRGB(mod(h + hue, 1.0), min(1.0, max(0.0, s * sat)), min(1.0, max(0.0, v * val)))
            let nr = byte(o.0), ng = byte(o.1), nb = byte(o.2)
            if nr >= 248 && ng >= 248 && nb >= 248 && !(r == 255 && g == 255 && b == 255) {
                return (247, 251, 247)      // pure white is the transparent colour of an RGB565 picture
            }
            return (nr, ng, nb)
        }
    }

    /// Change the accent pixels of one picture. Returns true if a byte changed.
    static func recolour(_ osos: inout [UInt8], _ pic: Picture, _ tint: Tint) -> Bool {
        guard pic.depth == 16 else { return false }
        let start = pic.dataPos, end = start + pic.bytesPerRow * pic.height
        let before = Array(osos[start..<end])
        for y in 0..<pic.height {
            let row = pic.dataPos + y * pic.bytesPerRow
            for x in 0..<pic.width {
                let (r, g, b, a) = pic.pixel(osos, x, y)
                let v: UInt16
                if pic.textureFormat == 0x1444 {
                    if a == 0 { continue }
                    let n = tint.pixel(Int(r), Int(g), Int(b))
                    v = UInt16(Int(a) >> 4) << 12 | UInt16(n.0 >> 4) << 8 | UInt16(n.1 >> 4) << 4 | UInt16(n.2 >> 4)
                } else {
                    let n = tint.pixel(Int(r), Int(g), Int(b))
                    v = UInt16(n.0 >> 3) << 11 | UInt16(n.1 >> 2) << 5 | UInt16(n.2 >> 3)
                }
                if pic.textureFormat == 0x2565 {
                    osos[row + 2 * x] = UInt8(v >> 8); osos[row + 2 * x + 1] = UInt8(v & 0xFF)
                } else {
                    osos[row + 2 * x] = UInt8(v & 0xFF); osos[row + 2 * x + 1] = UInt8(v >> 8)
                }
            }
        }
        return Array(osos[start..<end]) != before
    }

    /// Put the new gradient in each View. Returns the (label, start, end) of each View that changed.
    static func recolourViews(_ osos: inout [UInt8], _ block: ResourceBlock, bottom: [UInt8], top: [UInt8]) -> [(String, Int, Int)] {
        var touched: [(String, Int, Int)] = []
        for r in block.ofType("View") {
            let start = block.abs(r), end = start + Int(r.size)
            guard end <= osos.count, r.size >= 4 else { continue }
            let count = Int(Int32(bitPattern: le32(osos, start)))
            var p = start + 4, changed = false
            for _ in 0..<max(count, 0) {
                if p + 4 > end { break }
                let size = Int(le32(osos, p))
                var k = 16
                while k < size + 4 - 3 {
                    if p + k + 4 > end { break }
                    let word = Array(osos[p + k..<p + k + 4])
                    if word == appleTop { osos.replaceSubrange(p + k..<p + k + 4, with: top); changed = true }
                    else if word == appleBottom { osos.replaceSubrange(p + k..<p + k + 4, with: bottom); changed = true }
                    k += 4
                }
                p += size + 4
            }
            if changed { touched.append(("View \(r.id)", start, end)) }
        }
        return touched
    }

    /// Change the accent colour of osos. Returns the (label, start, end) of each resource that changed.
    /// `block` is the main resource block of Apple's firmware. A theme can move a table entry, thus the
    /// block must come from the firmware without the theme.
    static func apply(_ osos: inout [UInt8], accent: String, block: ResourceBlock) throws -> [(String, Int, Int)] {
        if isApple(accent) { return [] }
        let (bottom, top) = try words(accent)
        let tint = try Tint(accent)
        var touched: [(String, Int, Int)] = []
        for r in block.ofType("BMap") where pictures.contains(Int(r.id)) {
            guard let pic = Picture.parse(osos, at: block.abs(r)) else { continue }
            if recolour(&osos, pic, tint) {
                touched.append(("BMap \(r.id)", pic.dataPos, pic.dataPos + pic.bytesPerRow * pic.height))
            }
        }
        return touched + recolourViews(&osos, block, bottom: bottom, top: top)
    }

    /// The main resource block of Apple's firmware.
    static func mainBlock(_ osos: [UInt8], appleLength: Int) throws -> ResourceBlock {
        try Resources.mainBlock(Resources.scan(osos, limit: appleLength))
    }
}

public extension ImportedTheme {
    /// The theme with the accent colour. `osos` is the firmware without the theme. `appleLength` is the
    /// length of Apple's program in osos (`FirmwarePartition.appleOSLength`).
    ///
    /// The result holds the changes of the theme with the accent colour, and new changes for the bytes
    /// that the theme does not change, for example the selection bar of the Apple Views. With the accent
    /// of Apple the result is the theme itself.
    func withAccent(_ accent: String, osos: [UInt8], originalSHA256: String, appleLength: Int) throws -> ImportedTheme {
        _ = try Accent.parseHex(accent)
        if Accent.isApple(accent) { return self }
        var themed = osos
        try apply(to: &themed, originalSHA256: originalSHA256)
        var final = themed
        let touched = try Accent.apply(&final, accent: accent, block: Accent.mainBlock(osos, appleLength: appleLength))
        let base = try withOldBytes(osos).effectiveChanges.map { try $0.withCopiedBytes(osos) }
        var covered = [Bool](repeating: false, count: final.count)
        var changes: [ThemeChange] = []
        for c in base {
            let end = c.offset + c.new.count
            for i in c.offset..<end { covered[i] = true }
            changes.append(ThemeChange(resource: c.resource, offset: c.offset, old: c.old, new: Data(final[c.offset..<end])))
        }
        for (label, start, end) in touched {
            var i = start
            while i < end {
                if themed[i] == final[i] || covered[i] { i += 1; continue }
                var j = i
                while j < end && themed[j] != final[j] && !covered[j] { j += 1 }
                changes.append(ThemeChange(resource: label, offset: i, old: Data(osos[i..<j]), new: Data(final[i..<j])))
                i = j
            }
        }
        var out = ImportedTheme(name: name, source_sha256: source_sha256, osos_sha256: osos_sha256)
        out.imported = imported
        out.skipped = skipped
        out.changes = changes
        out.keep_apple = []
        out.keepsHighlight = false
        return out
    }
}
