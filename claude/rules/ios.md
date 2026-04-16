---
paths:
  - "ios/**/*"
---


# iOS App (Hotwire Native)

The `ios/` directory contains the native iOS shell built with Swift/UIKit and Hotwire Native (v1.2.2). It has its own `ios/CLAUDE.md` with iOS-specific guidance.

### Key files
- `ios/LifeMuse-iOS/AppDelegate.swift` — App entry point, initializes Hotwire and path configuration
- `ios/LifeMuse-iOS/SceneDelegate.swift` — Creates the Hotwire Navigator with the base URL
- `ios/LifeMuse-iOS/Environment.swift` — Reads `BaseURL` from Info.plist (set via xcconfig)
- `ios/LifeMuse-iOS/Configuration/` — Per-environment xcconfig files (Development, Staging, Production)
- `ios/LifeMuse-iOS/BridgeComponents/` — Native bridge components (AlertComponent, FlashComponent)
- `ios/LifeMuse-iOS/Controllers/LifeMuseVisitableViewController.swift` — Custom view controller with navigation bar hiding support
- `ios/LifeMuse-iOS/path-configuration.json` — Local Hotwire path routing rules (bundled with app)
- `/configurations/ios_v1.json` — Remote Hotwire path configuration (served by Rails)

### Commands
```bash
# Build
cd ios && xcodebuild -project LifeMuse-iOS.xcodeproj -scheme LifeMuse-iOS -sdk iphonesimulator build

# Run tests
cd ios && xcodebuild -project LifeMuse-iOS.xcodeproj -scheme LifeMuse-iOS -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 16' test
```