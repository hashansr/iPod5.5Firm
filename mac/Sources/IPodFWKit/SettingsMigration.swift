import Foundation

/// Copies the settings of the original iPodFirm one time. This app has its own bundle identifier,
/// so it does not share the settings of the original. The copy keeps the patch switches, the
/// appearance and the custom EQs. It does not copy the selected dark theme: the owner selects it again.
/// It does not copy the acceptance of the disclaimer either.
public enum SettingsMigration {
    /// The bundle identifier of the original iPodFirm.
    public static let originalDomain = "com.thefauxdreamer.ipodfirm"
    static let doneKey = "settingsCopiedFromOriginal"
    /// The settings that the copy takes. A setting that this app has already is not replaced.
    public static let keys = ["enabledPatches", "patchOptions", "appearance", "layout", "customEQs", "customVersionOn",
                              "customVersion", "versionLettersOn", "showPatchSummaries", "requireTouchID",
                              "checkForUpdates", "ososMargin", "showTestPatches", "colourfulEQCurve"]

    /// Do the copy one time. Nothing happens in a copy of the original app.
    public static func run(defaults: UserDefaults = .standard, bundleID: String? = Bundle.main.bundleIdentifier) {
        guard bundleID != originalDomain, !defaults.bool(forKey: doneKey) else { return }
        defaults.set(true, forKey: doneKey)
        if let old = defaults.persistentDomain(forName: originalDomain) { copy(old, to: defaults) }
    }

    public static func copy(_ old: [String: Any], to defaults: UserDefaults) {
        for key in keys where defaults.object(forKey: key) == nil {
            if let value = old[key] { defaults.set(value, forKey: key) }
        }
    }
}
