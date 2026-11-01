import Foundation

// Swift port of src/ipodfw/darkmode.py: the firmware for the appearance "Switch on iPod". It is
// light at the start and has a Dark Mode item in Settings.
//
// RetailOS makes its screens one time, at the start, from the View resources. Thus the dark theme
// cannot change while the iPod runs. The patch patches/dark-mode applies a switch table at the
// start, before the first View is read, if iPod_Control/iTunes/iPodFirmDarkMode contains '1'. The
// Settings item writes that file and restarts the iPod.
//
// The build puts these items after the end of osos (below ThemeImport.ososLimit):
//   the theme data outside osos (for example the background picture: in both modes)
//   the switch table: "IFD2", u32 count N, u32 total size, N entries with the new bytes of one change
//                     each, as an LZ4 block or as bytes (refer to `switchTable`)
//   the Settings menu with the Dark Mode item (the resource table entry points to it)
//   the code of the patch (its symbol dark_table is the address of the table)

public enum DarkMode {
    public static let magic: UInt32 = 0x3244_4649                 // "IFD2"
    static let settingsMenu = ThemeImport.Key(block: "main", type: "Menu", id: 24598)
    static let templateKey: UInt32 = 0x6000_60B7                  // the Sound Check item: an On/Off item
    static let insertAfterKey: UInt32 = 0x6000_6088               // the Clicker item
    public static let darkKey: UInt32 = 0x6000_60E0               // the Dark Mode item (patch: KEY)
    public static let labelID: UInt32 = 0x7E00                    // the label "Dark Mode" (patch: LABEL_ID)
    static let patchAreaEnd = 0x736800                            // the other patches use the area before this address
    /// The setting on the iPod: one byte, '0' (light) or '1' (dark).
    public static let settingFile = "iPod_Control/iTunes/iPodFirmDarkMode"

    public struct Info {
        public var table: (at: Int, length: Int)
        public var menu: (at: Int, length: Int)
        public var patchAt: Int
        /// Changes left out because the owner changed the same bytes.
        public var changesLeftOut: Int
    }

    static func align(_ n: Int, _ a: Int) -> Int { (n + a - 1) / a * a }

    /// Bytes of the Split layout that are different in the two modes.
    public struct LayoutRun {
        var at: Int
        var old: [UInt8]
        var new: [UInt8]
    }

    /// The Split layout for "Switch on iPod", with its View at `end`.
    static func layoutParts(theme: ImportedTheme, layout: ImportedTheme, osos: [UInt8], end: Int) throws
        -> (at: Int, view: [UInt8], entry: ThemeChange, extra: [LayoutRun]) {
        let at = align(end, 16)
        let place = [UInt8](repeating: 0, count: at)
        let moved = layout.movedLayout(after: place)
        let light = [UInt8](try moved.changes[0].withCopiedBytes(osos).new)
        var themed = osos
        try theme.apply(to: &themed, originalSHA256: theme.osos_sha256)
        let dark = [UInt8](try layout.movedLayout(after: place, dark: true).changes[0].withCopiedBytes(themed).new)
        var extra: [LayoutRun] = []
        var i = 0
        while i < light.count {
            var j = i
            while j < light.count && light[j] != dark[j] { j += 1 }
            if j > i { extra.append(LayoutRun(at: at + i, old: Array(light[i..<j]), new: Array(dark[i..<j]))) }
            i = max(j, i + 1)
        }
        return (at, light, moved.changes[1], extra)
    }

    static func varint(_ value: Int) -> [UInt8] {
        var out: [UInt8] = [], v = value
        while v >= 0x80 { out.append(UInt8(v & 0x7F | 0x80)); v >>= 7 }
        out.append(UInt8(v))
        return out
    }

    static func readVarint(_ d: [UInt8], _ pos: inout Int) throws -> Int {
        var v = 0, shift = 0
        while true {
            guard pos < d.count, shift <= 28 else { throw ThemeError("The switch table is not correct.") }
            let b = d[pos]
            pos += 1
            v |= Int(b & 0x7F) << shift
            if b & 0x80 == 0 { return v }
            shift += 7
        }
    }

    /// The bytes after a nibble of 15. `n` is the value minus 15.
    private static func lz4Extra(_ out: inout [UInt8], _ n: Int) {
        var n = n
        while n >= 255 { out.append(255); n -= 255 }
        out.append(UInt8(n))
    }

    /// One LZ4 sequence. `length` is the match length (at least 4), or 0 for the last sequence.
    private static func lz4Sequence(_ out: inout [UInt8], _ literals: ArraySlice<UInt8>, _ offset: Int, _ length: Int) {
        let lit = literals.count, match = max(length - 4, 0)
        out.append(UInt8(min(lit, 15) << 4 | (length > 0 ? min(match, 15) : 0)))
        if lit >= 15 { lz4Extra(&out, lit - 15) }
        out += literals
        if length > 0 {
            out.append(UInt8(offset & 0xFF)); out.append(UInt8(offset >> 8))
            if match >= 15 { lz4Extra(&out, match - 15) }
        }
    }

    /// An LZ4 block. The algorithm is simple, and the Python version (darkmode.lz4_compress) is the same,
    /// so both give the same bytes: a table of 4096 positions, a hash of 4 bytes, the first match, no
    /// search inside a match. The last 5 bytes are bytes, and no match starts in the last 12 bytes.
    public static func lz4Compress(_ src: [UInt8]) -> [UInt8] {
        let n = src.count
        var out: [UInt8] = []
        out.reserveCapacity(n / 2 + 16)
        var table = [Int32](repeating: -1, count: 4096)
        var anchor = 0, ip = 0
        let startLimit = n - 12, endLimit = n - 5
        func read32(_ i: Int) -> UInt32 {
            UInt32(src[i]) | UInt32(src[i + 1]) << 8 | UInt32(src[i + 2]) << 16 | UInt32(src[i + 3]) << 24
        }
        while ip < startLimit {
            let v = read32(ip)
            let h = Int((v &* 2_654_435_761) >> 20)
            let ref = Int(table[h])
            table[h] = Int32(ip)
            if ref >= 0 && ip - ref <= 65535 && read32(ref) == v {
                var length = 4
                while ip + length < endLimit && src[ref + length] == src[ip + length] { length += 1 }
                lz4Sequence(&out, src[anchor..<ip], ip - ref, length)
                ip += length
                anchor = ip
            } else {
                ip += 1
            }
        }
        lz4Sequence(&out, src[anchor...], 0, 0)
        return out
    }

    /// The reference decoder (the patch does the same). Throws if the block is not correct.
    public static func lz4Decompress(_ block: [UInt8], length: Int) throws -> [UInt8] {
        let bad = ThemeError("An LZ4 block is not correct.")
        var out: [UInt8] = []
        var pos = 0
        func next() throws -> Int {
            guard pos < block.count else { throw bad }
            pos += 1
            return Int(block[pos - 1])
        }
        while pos < block.count {
            let token = try next()
            var lit = token >> 4, match = token & 15
            if lit == 15 {
                while true { let b = try next(); lit += b; if b != 255 { break } }
            }
            guard pos + lit <= block.count else { throw bad }
            out += block[pos..<pos + lit]
            pos += lit
            if pos == block.count { break }
            let low = try next(), high = try next()
            let offset = low | high << 8
            guard offset != 0, offset <= out.count else { throw bad }
            if match == 15 {
                while true { let b = try next(); match += b; if b != 255 { break } }
            }
            for _ in 0..<match + 4 { out.append(out[out.count - offset]) }
        }
        guard out.count == length else { throw ThemeError("An LZ4 block has the wrong length.") }
        return out
    }

    /// The switch table for the changes inside osos, with the rules of `ImportedTheme.apply`: a change
    /// is used if the bytes are the old bytes, and left out if they are already the new bytes (the same
    /// change two times) or other bytes (an edit by the owner).
    ///
    /// The table holds the new bytes (the patch only changes the light osos to the dark osos):
    /// "IFD2", u32 count, u32 total size, then for each change: varint zigzag(address - end of the
    /// previous change), varint length * 2 + (1 if LZ4), varint size of the LZ4 block (only with LZ4),
    /// the block or the bytes.
    public static func switchTable(_ theme: ImportedTheme, osos: [UInt8],
                                   extra: [LayoutRun] = []) -> (table: [UInt8], leftOut: Int) {
        var changes: [(at: Int, new: [UInt8])] = [], leftOut = 0
        var work = osos
        for c in theme.withOldBytes(osos).effectiveChanges where c.offset + c.old.count <= osos.count {
            let cur = work[c.offset..<c.offset + c.old.count]
            guard cur.elementsEqual(c.old) else {
                if !cur.elementsEqual(c.new) { leftOut += 1 }
                continue
            }
            work.replaceSubrange(c.offset..<c.offset + c.new.count, with: c.new)
            changes.append((c.offset, [UInt8](c.new)))
        }
        for e in extra { changes.append((e.at, e.new)) }
        var body: [UInt8] = []
        var prevEnd = 0
        for (at, new) in changes {
            let delta = at - prevEnd
            body += varint(delta >= 0 ? delta << 1 : ((-delta - 1) << 1) | 1)
            let packed = lz4Compress(new)
            if packed.count < new.count {
                body += varint(new.count * 2 + 1) + varint(packed.count) + packed
            } else {
                body += varint(new.count * 2) + new
            }
            prevEnd = at + new.count
        }
        var head = [UInt8](repeating: 0, count: 12)
        put32(&head, 0, magic); put32(&head, 4, UInt32(changes.count)); put32(&head, 8, UInt32(12 + body.count))
        return (head + body, leftOut)
    }

    /// What the patch does at the start (for tests). Throws if the table is not correct.
    public static func applySwitchTable(_ osos: inout [UInt8], _ table: [UInt8]) throws {
        let bad = ThemeError("The switch table is not correct.")
        guard table.count >= 12, le32(table, 0) == magic, Int(le32(table, 8)) == table.count else { throw bad }
        var pos = 12, prevEnd = 0
        for _ in 0..<Int(le32(table, 4)) {
            let zz = try readVarint(table, &pos), len2 = try readVarint(table, &pos)
            let length = len2 >> 1
            let size = len2 & 1 == 1 ? try readVarint(table, &pos) : length
            let at = prevEnd + ((zz >> 1) ^ -(zz & 1))
            guard at >= 0, at + length <= osos.count, pos + size <= table.count else { throw bad }
            let data = Array(table[pos..<pos + size])
            osos.replaceSubrange(at..<at + length, with: len2 & 1 == 1 ? try lz4Decompress(data, length: length) : data)
            pos += size
            prevEnd = at + length
        }
        guard pos == table.count else { throw bad }
    }

    /// Menu 24598 with a Dark Mode item after Clicker (a copy of the Sound Check item).
    public static func settingsMenu(_ menu: [UInt8]) throws -> [UInt8] {
        let count = Int(le32(menu, 0))
        let keys = (0..<count).map { le32(menu, 4 + 40 * $0 + 0x1C) }
        guard !keys.contains(darkKey) else { throw ThemeError("The Settings menu already has the Dark Mode item.") }
        guard keys.contains(templateKey), keys.contains(insertAfterKey) else {
            throw ThemeError("The Settings menu is not the menu of firmware 1.3.")
        }
        return try Patcher.insertSettingsItem(menu, key: darkKey, label: labelID, after: insertAfterKey, template: templateKey)
    }

    /// The positions of the items after the theme data (refer to the comment at the top).
    static func layout(themeEnd: Int, table: Int, menu: Int) -> (tableAt: Int, menuAt: Int, patchAt: Int) {
        let tableAt = align(themeEnd, 16)
        let menuAt = align(tableAt + table, 16)
        return (tableAt, menuAt, align(menuAt + menu, 16))
    }

    /// The end of the theme data after the end of osos, or `patchAreaEnd` if there is none.
    static func themeEnd(_ theme: ImportedTheme, osos: [UInt8]) -> Int {
        theme.withOldBytes(osos).effectiveChanges.filter { $0.offset + $0.old.count > osos.count }.map { $0.offset + $0.new.count }
            .reduce(patchAreaEnd, max)
    }

    /// Menu 24598 with the Dark Mode item, and its resource table entry.
    static func settingsMenu(partition: FirmwarePartition, osos: [UInt8]) throws -> ([UInt8], Resource, ResourceBlock) {
        let image = try ThemeImport.Image(partition)
        guard let entry = image.res[settingsMenu] else { throw ThemeError("The firmware has no Settings menu (Menu 24598).") }
        let (res, block) = entry
        return (try settingsMenu(Array(osos[block.abs(res)..<block.abs(res) + Int(res.size)])), res, block)
    }

    /// The bytes that "Switch on iPod" adds after the end of osos (`patchAreaEnd`): the theme data, the
    /// switch table, the Settings menu and the code of the patch (`codeSize`, the `size` in patch.json).
    /// The value is the same as the layout of `build`. The Patches pane shows it.
    public static func addedSize(partition: FirmwarePartition, osos: [UInt8], theme: ImportedTheme, codeSize: Int,
                                 layout splitLayout: ImportedTheme? = nil) throws -> Int {
        let menu = try settingsMenu(partition: partition, osos: osos).0
        var end = themeEnd(theme, osos: osos)
        var extra: [LayoutRun] = []
        if let splitLayout {
            let parts = try layoutParts(theme: theme, layout: splitLayout, osos: osos, end: end)
            end = parts.at + parts.view.count
            extra = parts.extra
        }
        let at = layout(themeEnd: end, table: switchTable(theme, osos: osos, extra: extra).table.count, menu: menu.count)
        return at.patchAt + codeSize - patchAreaEnd
    }

    /// The osos for "Switch on iPod". `osos` can have edits of the owner; `partition` gives its resources.
    /// With `layout`, both modes have the Split main menu.
    public static func build(partition: FirmwarePartition, osos: [UInt8], theme: ImportedTheme, patch: PatchInfo,
                             originalSHA256: String, layout splitLayout: ImportedTheme? = nil) throws -> ([UInt8], Info) {
        guard originalSHA256 == theme.osos_sha256 else { throw ThemeError("The theme \"\(theme.name)\" is for a different firmware.") }
        let theme = theme.withOldBytes(osos)
        var out = osos
        // 1. theme data outside osos: in both modes
        for c in theme.effectiveChanges where c.offset + c.old.count > osos.count {
            if out.count < c.offset + c.new.count { out += [UInt8](repeating: 0, count: c.offset + c.new.count - out.count) }
            out.replaceSubrange(c.offset..<c.offset + c.new.count, with: c.new)
        }
        // The layout: in both modes. The switch table changes only its colours and text styles.
        var end = themeEnd(theme, osos: osos)
        var extra: [LayoutRun] = []
        if let splitLayout {
            let parts = try layoutParts(theme: theme, layout: splitLayout, osos: osos, end: end)
            if out.count < parts.at + parts.view.count {
                out += [UInt8](repeating: 0, count: parts.at + parts.view.count - out.count)
            }
            out.replaceSubrange(parts.at..<parts.at + parts.view.count, with: parts.view)
            out.replaceSubrange(parts.entry.offset..<parts.entry.offset + parts.entry.new.count, with: parts.entry.new)
            end = parts.at + parts.view.count
            extra = parts.extra
        }
        // 2. the switch table and 3. the Settings menu
        let (table, leftOut) = switchTable(theme, osos: osos, extra: extra)
        let (menu, res, block) = try settingsMenu(partition: partition, osos: osos)
        let (tableAt, menuAt, patchAt) = layout(themeEnd: end, table: table.count, menu: menu.count)
        // 4. the patch, then the table and the menu
        out = try Patcher.apply(patch, to: out, originalSHA256: originalSHA256, loadAddress: UInt32(patchAt),
                                symbols: ["dark_table": UInt32(tableAt)], maxSize: ThemeImport.ososLimit)
        guard out[tableAt..<patchAt].allSatisfy({ $0 == 0 }) else { throw ThemeError("The space for the switch table is not empty.") }
        out.replaceSubrange(tableAt..<tableAt + table.count, with: table)
        out.replaceSubrange(menuAt..<menuAt + menu.count, with: menu)
        put32(&out, res.tablePos + 4, UInt32(menuAt - block.dataStart))
        put32(&out, res.tablePos + 8, UInt32(menu.count))
        return (out, Info(table: (tableAt, table.count), menu: (menuAt, menu.count), patchAt: patchAt, changesLeftOut: leftOut))
    }
}
