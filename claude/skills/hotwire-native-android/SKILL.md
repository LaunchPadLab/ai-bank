---
name: hotwire-native-android
description: Build hybrid Android apps with Hotwire Native. Covers Kotlin setup, Gradle configuration, path-based routing, bridge components (JS ↔ Kotlin), cookie/token authentication, deep linking, native fragment integration, and Rails server patterns (turbo-rails helpers, conditional rendering).
allowed-tools: Read, Write, Edit, Bash
---

# Hotwire Native Android Skill

Build hybrid Android apps wrapping Rails web content in native navigation with bridge components for JS ↔ Kotlin communication.

## When to Use

- Building Android apps with Hotwire Native
- Implementing bridge components (native buttons, forms, menus)
- Configuring path-based navigation rules
- Integrating Kotlin with Rails backends
- Setting up cookie or token-based authentication

## Requirements

| Component | Version |
|-----------|---------|
| Kotlin | 1.9+ |
| Android | API 28+ |
| Turbo.js | 7+ |
| hotwire-native-android | 1.2.2+ |

## Quick Start

### 1. Add Gradle Dependencies

```kotlin
// build.gradle.kts (app)
dependencies {
    implementation("dev.hotwire:hotwire-native-android:1.2.2")
}
```

### 2. Application Class

```kotlin
class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        
        // Path configuration
        Hotwire.loadPathConfiguration(
            context = this,
            location = PathConfiguration.Location(
                assetFilePath = "json/path-configuration.json",
                remoteFileUrl = "https://your-app.com/path-configuration.json"
            )
        )
        
        // Bridge components
        Hotwire.registerBridgeComponents(
            BridgeComponentFactory("button", ::ButtonComponent),
            BridgeComponentFactory("form", ::FormComponent)
        )
        
        Hotwire.config.debugLoggingEnabled = true
    }
}
```

### 3. MainActivity

```kotlin
class MainActivity : HotwireActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
    }
    
    override fun navigatorConfigurations() = listOf(
        NavigatorConfiguration(
            name = "main",
            startLocation = "https://your-app.com",
            navigatorHostId = R.id.navigator_host
        )
    )
}
```

### 4. Layout (activity_main.xml)

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.fragment.app.FragmentContainerView
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/navigator_host"
    android:name="dev.hotwire.navigation.navigator.NavigatorHost"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

### 5. Path Configuration (assets/json/path-configuration.json)

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
| HotwireActivity | Base activity with navigator support |
| NavigatorConfiguration | Start URL + navigator host binding |
| Path Configuration | JSON rules mapping URL patterns to behavior |
| Bridge Components | Three-part system: HTML → JS → Kotlin |
| Context | `default` (forward) or `modal` (bottom sheet) |

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
- `NAVIGATION.md` - Navigation patterns and deep links
- `AUTH.md` - Authentication flows
- `reference.md` - Full API reference
- `examples.md` - Complete code examples

## Links

- Docs: https://native.hotwired.dev
- Repo: https://github.com/hotwired/hotwire-native-android
