import AppKit
import IPodFWKit
import SwiftUI
import UniformTypeIdentifiers

/// A disclosure group that opens and closes with a click on the title, not only on the chevron.
struct TitleDisclosure<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content
    @State private var expanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $expanded, content: content) {
            Text(title)
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
                .onTapGesture { withAnimation { expanded.toggle() } }
        }
    }
}

/// The controls of a patch from the "ui" object of its patch.json: actions, switches, steps, a readme
/// and built-in tools. A new patch gets these controls with no change to the Swift code.
struct PatchControls: View {
    @EnvironmentObject var model: AppModel
    let patch: PatchInfo

    var body: some View {
        if let ui = patch.spec.ui {
            let actions = ui.actions ?? [], toggles = ui.toggles ?? []
            if !actions.isEmpty || !toggles.isEmpty {
                Section("On the iPod") {
                    if !actions.isEmpty {
                        IPodActionsRow {
                            ForEach(actions, id: \.title) { a in
                                Button(a.title) { model.runPatchAction(patch, a) }
                            }
                        }
                    }
                    ForEach(toggles, id: \.path) { t in
                        Toggle(t.title, isOn: Binding(get: { model.patchToggleStates[t.path] ?? false },
                                                      set: { model.setPatchToggle(t, on: $0) }))
                            .toggleStyle(.switch)
                            .disabled(model.currentIPod == nil)
                    }
                    if actions.isEmpty && model.currentIPod == nil {
                        Text("Connect the iPod.").font(.caption).foregroundStyle(.secondary)
                    }
                    if let s = model.patchActionStatus[patch.spec.name] { Label(s, systemImage: "checkmark.circle").font(.callout) }
                }
            }
            if let steps = ui.steps, !steps.isEmpty {
                Section {
                    TitleDisclosure(title: ui.steps_title ?? "Procedure") {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(Array(steps.enumerated()), id: \.offset) { i, text in Step(n: i + 1, text: text) }
                        }
                        .font(.callout)
                        .padding(.top, 4)
                    }
                    .id(patch.spec.name)   // each patch starts closed
                }
            }
            if let file = ui.readme, !file.contains("/"),
               let text = try? String(contentsOf: patch.folder.appendingPathComponent(file), encoding: .utf8) {
                Section("Read Me") {
                    Text((try? AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
                         ?? AttributedString(text))
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            ForEach(ui.tools ?? [], id: \.self) { PatchTool(id: $0) }
        }
    }
}

/// The built-in Swift tools that a patch can name in "ui.tools". Keep the ids in PatchSpec.knownTools.
struct PatchTool: View {
    let id: String

    var body: some View {
        switch id {
        case "album-thumbnails": AlbumArtSections()
        case "battery-curve": BatteryCurveSection()
        default: EmptyView()
        }
    }
}

// MARK: battery-curve

/// The curve of the option Custom Battery in the battery-display patch. It comes from a battery log.
struct BatteryCurveSection: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        Section {
            Text("To make a curve for your battery, import a battery log from a full charge until the iPod stopped. Then flash the iPod again.")
                .fixedSize(horizontal: false, vertical: true)
            HStack {
                Button("Import Log File…") { model.chooseBatteryLogFile() }
                Spacer()
                if model.batteryCurve != nil {
                    Button("Use the Built-In Curve") { model.batteryCurve = nil }
                }
            }
            if let curve = model.batteryCurve {
                Text("Imported curve: \(curve.hours, specifier: "%.1f") hours, raw value \(curve.raw[0]) to \(curve.raw[curve.raw.count - 1]).")
                    .foregroundStyle(.secondary)
            } else {
                Text("The patch uses its built-in curve. This curve is provisional, and it is for one larger battery.")
                    .foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
        } header: {
            Text("Battery Curve")
        }
    }
}

// MARK: album-thumbnails

/// The thumbnail file and the playlist artwork of the album-art patch.
struct AlbumArtSections: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        Section {
            Text("Albums show the artwork that iTunes or Finder put on the iPod. They need no step here. After a sync, the iPod makes the album pictures one time and keeps them in a file. The iPod also makes the collage of each playlist. The thumbnail file of iPodFirm is necessary only for custom playlist images. Write it after you flash this patch, and again after each change. The file also has the album covers and the collages. On the iPod, the pictures of the file come first. Thus write the file again after you change a cover.")
                .fixedSize(horizontal: false, vertical: true)
            IPodActionsRow {
                Button("Write Thumbnails to iPod") { Task { await model.writeThumbnails() } }
            }
            if let s = model.thumbnailStatus { Label(s, systemImage: "checkmark.circle").font(.callout) }
        } header: {
            Text("Thumbnails")
        }
        .task(id: model.currentIPod?.disk) { await model.loadPlaylists() }
        if !model.playlistArt.isEmpty {
            Section {
                if model.playlistArtChanged {
                    Label("Click Write Thumbnails to iPod to send the changes to the iPod.", systemImage: "exclamationmark.circle")
                        .labelStyle(StatusLabelStyle(tint: .orange))
                }
                ForEach(model.playlistArt) { p in PlaylistArtRow(playlist: p) }
            } header: {
                Text("Playlist Artwork")
            }
        }
    }
}

struct PlaylistArtRow: View {
    @EnvironmentObject var model: AppModel
    let playlist: MusicImport.PlaylistArt
    @State private var targeted = false

    var body: some View {
        HStack(spacing: 10) {
            Group {
                if let data = playlist.image, let img = NSImage(data: data) {
                    Image(nsImage: img).resizable().interpolation(.high).aspectRatio(1, contentMode: .fill)
                } else {
                    Image(systemName: "music.note.list").foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.secondary.opacity(0.15))
                }
            }
            .frame(width: 40, height: 40).clipShape(RoundedRectangle(cornerRadius: 4))
            .accessibilityHidden(true)
            Text(playlist.name.isEmpty ? "(No name)" : playlist.name).lineLimit(1)
                .help(playlist.isCustom ? "Custom image" : playlist.image == nil ? "No album covers" : "Automatic")
            Spacer()
            Button("Choose Image…") { model.choosePlaylistArt(playlist.name) }
            Button("Use Automatic") { Task { await model.resetPlaylistArt(playlist.name) } }
                .disabled(!playlist.isCustom)
        }
        .padding(4)
        .background(RoundedRectangle(cornerRadius: 6).stroke(Color.accentColor, lineWidth: targeted ? 2 : 0))
        .onDrop(of: [.fileURL], isTargeted: $targeted) { providers in
            guard let provider = providers.first else { return false }
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                guard let url else { return }
                Task { @MainActor in await model.setPlaylistArt(playlist.name, from: url) }
            }
            return true
        }
    }
}

// MARK: install

/// The patch that the owner opened: what it is, the problems and the notes. Install or Cancel.
struct InstallPatchSheet: View {
    @EnvironmentObject var model: AppModel
    let candidate: PatchCandidate
    @State private var confirmBuiltIn = false

    /// For example "1.2", or "1.1 → 1.2" for an update.
    func versionText(_ spec: PatchSpec) -> String {
        candidate.change == .new ? spec.versionText : "\(candidate.installedVersion ?? "–") → \(spec.versionText)"
    }

    var buttonTitle: String {
        if candidate.replacesBuiltIn { return "Replace Built-In Patch" }
        switch candidate.change {
        case .new: return "Install"
        case .update: return "Update"
        case .same: return "Reinstall"
        case .downgrade: return "Downgrade"
        }
    }

    /// A caution for a downgrade or for a patch that replaces a built-in patch.
    var caution: String? {
        if candidate.replacesBuiltIn {
            return "This patch replaces a patch that is built into iPodFirm. Make sure that you trust the person that made it."
        }
        if candidate.change == .downgrade {
            return "This file has an older version than the installed patch. The older version can have problems that the newer version corrects."
        }
        return nil
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if let spec = candidate.spec {
                HStack(spacing: 14) {
                    SymbolTile(symbol: validSymbol(spec.symbol), tint: .accentColor, size: 44)
                    Text(spec.displayTitle).font(.title2.weight(.semibold))
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 10) {
                        if let caution = spec.caution {
                            Label(caution, systemImage: "exclamationmark.triangle.fill")
                                .labelStyle(StatusLabelStyle(tint: .orange)).fixedSize(horizontal: false, vertical: true)
                        }
                        if let d = spec.description { Text(d).fixedSize(horizontal: false, vertical: true) }
                        ForEach(spec.details ?? [], id: \.self) { BulletRow(text: $0) }
                        ForEach(spec.requires ?? [], id: \.self) { BulletRow(text: "You need: \($0)", symbol: "checkmark.circle", tint: .green) }
                        Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 4) {
                            GridRow { Text("Name").foregroundStyle(.secondary); Text(spec.name).monospaced() }
                            GridRow { Text("Version").foregroundStyle(.secondary); Text(versionText(spec)) }
                            GridRow { Text("For").foregroundStyle(.secondary); Text(spec.targetText) }
                            GridRow { Text("Letter").foregroundStyle(.secondary); Text(candidate.assignedLetter ?? spec.version_letter ?? "-") }
                            GridRow { Text("Code").foregroundStyle(.secondary); Text(candidate.codeSize.map { "\($0) bytes" } ?? "No code (data only)") }
                            GridRow { Text("Size on iPod").foregroundStyle(.secondary); Text((candidate.assignedSize ?? spec.size).map(PatchSpec.byteText) ?? "–") }
                            GridRow { Text("Changes").foregroundStyle(.secondary); Text("\(spec.hooks?.count ?? 0) hooks, \(spec.bytes?.count ?? 0) byte runs") }
                        }
                        .font(.callout)
                        ForEach(candidate.errors, id: \.self) { e in
                            Label(e, systemImage: "xmark.octagon.fill").labelStyle(StatusLabelStyle(tint: .red)).fixedSize(horizontal: false, vertical: true)
                        }
                        ForEach(candidate.notes, id: \.self) { n in
                            Label(n, systemImage: "info.circle").foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 280)
            } else {
                Label("iPodFirm cannot install this patch", systemImage: "xmark.octagon.fill").font(.title3.bold())
                ForEach(candidate.errors, id: \.self) { e in Text(e).fixedSize(horizontal: false, vertical: true) }
            }
            if candidate.canInstall, let caution {
                Label(caution, systemImage: "exclamationmark.triangle.fill")
                    .labelStyle(StatusLabelStyle(tint: .orange)).font(.callout).fixedSize(horizontal: false, vertical: true)
            }
            if candidate.canInstall {
                Label("A patch puts new code on your iPod. Install only patches from people that you trust. iPodFirm makes a backup before each flash.",
                      systemImage: "exclamationmark.triangle.fill")
                    .labelStyle(StatusLabelStyle(tint: .orange)).font(.callout).fixedSize(horizontal: false, vertical: true)
            }
            HStack {
                Spacer()
                Button("Cancel") { model.cancelInstall(candidate) }.keyboardShortcut(.cancelAction)
                if candidate.canInstall {
                    Button(buttonTitle) {
                        if candidate.replacesBuiltIn { confirmBuiltIn = true } else { model.confirmInstall(candidate) }
                    }
                    .keyboardShortcut(.defaultAction).buttonStyle(.borderedProminent)
                }
            }
        }
        .padding(22)
        .frame(width: 520)
        .confirmationDialog("Replace the built-in patch \"\(candidate.spec?.displayTitle ?? "")\"?", isPresented: $confirmBuiltIn) {
            Button("Replace Built-In Patch", role: .destructive) { model.confirmInstall(candidate) }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("iPodFirm uses this patch in place of the built-in patch. To use the built-in patch again, remove this patch.")
        }
    }
}

/// The SF Symbol of a patch, or the puzzle piece if macOS does not have the symbol.
func validSymbol(_ name: String?) -> String {
    guard let name, NSImage(systemSymbolName: name, accessibilityDescription: nil) != nil else { return "puzzlepiece.extension" }
    return name
}

/// true: the URL is a .ipodpatch file or a folder with patch.json.
func isPatchURL(_ url: URL) -> Bool {
    url.pathExtension == PatchLibrary.fileExtension
        || FileManager.default.fileExists(atPath: url.appendingPathComponent("patch.json").path)
}
