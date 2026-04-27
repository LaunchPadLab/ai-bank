# Codex Instructions: android

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/android.md`

## Source: `claude/rules/android.md`

# Android App (Hotwire Native)

- Treat `android/` as a native shell around Rails web content.
- Use Kotlin and Hotwire Native conventions already present in the app.
- Discover actual package names, Gradle modules, path configuration files, and bridge components from the repository before editing.
- Keep local bundled path configuration and remote Rails-served configuration in sync when both exist.
- Register bridge components in the Application class or existing app-level registration point.
- For detailed setup, navigation, authentication, and bridge guidance, defer to the `hotwire-native-android` and `hotwire-native-auth` skills.
- Use the app's existing Gradle wrapper and configured JDK; do not hardcode project-specific package paths or version numbers unless they already exist in the repo.
