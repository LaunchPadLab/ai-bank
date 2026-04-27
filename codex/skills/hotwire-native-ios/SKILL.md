---
name: "hotwire-native-ios"
description: "Build hybrid iOS apps with Hotwire Native. Covers Swift/UIKit setup, path configuration routing, bridge components (JS \u2194 Swift), cookie/token authentication, native screen integration, and Rails server patterns (turbo-rails helpers, conditional rendering)."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# Hotwire Native iOS Skill

Build hybrid iOS apps wrapping Rails web content in native navigation with bridge components for JS ↔ Swift communication.

## When to Use

- Building iOS apps with Hotwire Native
- Implementing bridge components (native buttons, forms, menus)
- Configuring path-based navigation rules
- Integrating Swift with Rails backends
- Setting up cookie or token-based authentication

## Requirements

| Component | Version |
|-----------|---------|
| Swift | 5.3+ |
| iOS | 14+ |
| Turbo.js | 7+ |
| hotwire-native-ios | 1.2.2+ |

## Quick Start

### 1. Add SPM Dependency

Xcode → File → Add Package Dependencies → `https://github.com/hotwired/hotwire-native-ios`

### 2. SceneDelegate Setup

```swift
import HotwireNative

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    
    private let navigator = Navigator(configuration: .init(
        name: "main",
        startLocation: URL(string: "https://your-app.com")!
    ))

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        window?.rootViewController = navigator.rootViewController
        navigator.start()
    }
}
```

### 3. AppDelegate Configuration

```swift
import HotwireNative

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Path configuration
        let localURL = Bundle.main.url(forResource: "path-configuration", withExtension: "json")!
        Hotwire.loadPathConfiguration(from: [.file(localURL)])
        
        // Bridge components
        Hotwire.registerBridgeComponents([
            ButtonComponent.self,
            FormComponent.self
        ])
        
        Hotwire.config.debugLoggingEnabled = true
        return true
    }
}
```

### 4. Path Configuration (path-configuration.json)

```json
{
  "settings": { "screenshots_enabled": true },
  "rules": [
    { "patterns": [".*"], "properties": { "context": "default", "pull_to_refresh_enabled": true } },
    { "patterns": ["/new$", "/edit$"], "properties": { "context": "modal" } }
  ]
}
```

## Core Concepts

| Concept | Description |
|---------|-------------|
| Navigator | Manages navigation stack, handles routing |
| Path Configuration | JSON rules mapping URL patterns to behavior |
| Bridge Components | Three-part system: HTML → JS → Swift |
| Context | `default` (push) or `modal` (present) |

## Rails Server Integration

```ruby
class ApplicationController < ActionController::Base
  include Turbo::Native::Navigation
end
```

**Helpers:** `recede_or_redirect_to`, `resume_or_redirect_to`, `refresh_or_redirect_to`

## Additional Resources

Load these files as needed:
- `BRIDGE_COMPONENTS.md` - Bridge component implementation
- `AUTH.md` - Authentication integration patterns
- `NAVIGATION.md` - Navigation and path configuration patterns
- `reference.md` - Full API reference  
- `examples.md` - Complete code examples

## Links

- Docs: https://native.hotwired.dev
- Repo: https://github.com/hotwired/hotwire-native-ios
