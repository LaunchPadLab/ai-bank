---
paths:
  - "ios/**/*"
---

# iOS App (Hotwire Native)

- Treat `ios/` as a native shell around Rails web content.
- Use Swift/UIKit and Hotwire Native conventions already present in the app.
- Discover actual project names, targets, bundle IDs, and path configuration files from the repository before editing.
- Keep local bundled path configuration and remote Rails-served configuration in sync when both exist.
- Register bridge components in the native app and keep their JavaScript counterparts aligned.
- For detailed setup, navigation, authentication, and bridge guidance, defer to the `hotwire-native-ios` and `hotwire-native-auth` skills.
- Run the app's existing `xcodebuild` commands or scheme-specific tests; do not assume a hardcoded scheme name.
