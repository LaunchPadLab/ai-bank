# Hotwire Native Path Configuration Reference

## Overview

Path configuration controls how URLs are routed and displayed in Hotwire Native apps. It consists of `settings` (app-level config) and `rules` (URL pattern matching).

## Structure

```json
{
  "settings": {},
  "rules": [
    {
      "patterns": ["regex_pattern"],
      "properties": { "key": "value" }
    }
  ]
}
```

## Rule Matching

Rules are read **sequentially**. Later rules override earlier ones for matching URLs.

**Recommended pattern:** First rule establishes defaults (`".*"`), subsequent rules override for specific paths.

```json
{
  "rules": [
    {
      "patterns": [".*"],
      "properties": { "context": "default", "pull_to_refresh_enabled": true }
    },
    {
      "patterns": ["/new$", "/edit$"],
      "properties": { "context": "modal", "pull_to_refresh_enabled": false }
    }
  ]
}
```

## Common Properties (Both Platforms)

| Property | Values | Default | Description |
|----------|--------|---------|-------------|
| `context` | `default`, `modal` | `default` | Presentation context |
| `presentation` | `default`, `push`, `pop`, `replace`, `replace_root`, `clear_all`, `refresh`, `none` | `default` | Navigation style |
| `pull_to_refresh_enabled` | `true`, `false` | iOS: `true`, Android: `false` | Enable pull-to-refresh |
| `animated` | `true`, `false` | `true` | Animate navigation transitions |

## iOS-Specific Properties

| Property | Values | Default | Description |
|----------|--------|---------|-------------|
| `view_controller` | string | none | Custom `UIViewController` identifier (conform to `PathConfigurationIdentifiable`) |
| `modal_style` | `large`, `medium`, `full`, `page_sheet`, `form_sheet` | `large` | Modal presentation style |
| `modal_dismiss_gesture_enabled` | `true`, `false` | `true` | Allow swipe-to-dismiss on modals |

**Modal styles:**
- `large` — Default system presentation (automatic)
- `medium` — Half-sheet, expandable via drag
- `full` — Full-screen, covers status bar
- `page_sheet` — iPad: partial cover; iPhone: default system
- `form_sheet` — iPad: centered modal; iPhone: default system

## Android-Specific Properties

| Property | Required | Description |
|----------|----------|-------------|
| `uri` | **Yes** | Destination URI (e.g., `hotwire://fragment/web`). Must map to a Fragment with `HotwireDestinationDeepLink` annotation. |
| `fallback_uri` | No | Fallback if destination not found (useful for backwards compatibility) |
| `title` | No | Toolbar title (web pages use `<title>` tag) |

**Common URIs:**
- `hotwire://fragment/web` — Standard web fragment
- `hotwire://fragment/web/modal/sheet` — Modal sheet presentation

## Configuration Loading

### iOS (Swift)

```swift
// In AppDelegate.swift
let localURL = Bundle.main.url(forResource: "path-configuration", withExtension: "json")!
let remoteURL = URL(string: "https://example.com/configurations/ios_v1.json")!

Hotwire.loadPathConfiguration(from: [
    .file(localURL),
    .server(remoteURL)
])
```

### Android (Kotlin)

```kotlin
// In Application subclass
Hotwire.loadPathConfiguration(
    context = this,
    location = PathConfiguration.Location(
        assetFilePath = "json/configuration.json",
        remoteFileUrl = "https://example.com/configurations/android_v1.json"
    )
)
```

**Loading order (both platforms):**
1. Bundled local file (immediate)
2. Cached server file (if previously downloaded)
3. Fresh server download (async, cached for next launch)

## Query String Matching (iOS)

By default, patterns match path + query string. Use wildcards for query params:

```json
{
  "patterns": [".*\\?.*foo=bar.*"],
  "properties": { "custom_property": true }
}
```

Disable query string matching:
```swift
Hotwire.config.pathConfiguration.matchQueryStrings = false
```

## Settings Object

Use `settings` for app-level configuration (feature flags, Action Cable URLs, etc.):

```json
{
  "settings": {
    "use_local_db": true,
    "cable": {
      "script_url": "https://example.com/action_cable.js"
    },
    "feature_flags": [
      { "name": "new_onboarding", "enabled": true }
    ]
  },
  "rules": []
}
```

## Custom Properties

Add custom properties as needed. The framework only handles built-in properties automatically; custom properties require app-side implementation.

Example: `navigation_bar_hidden` for hiding the native nav bar on specific screens.

## Best Practices

1. **Always bundle a local config** — Ensures offline functionality
2. **Version remote configs** — Use versioned URLs (`ios_v1.json`) for breaking changes
3. **Disable pull-to-refresh on modals** — Prevents interference with dismiss gestures
4. **Disable pull-to-refresh on forms** — Prevents accidental data loss
5. **Use `$` anchor for exact path endings** — `/new$` vs `/new` (latter matches `/newsletter`)
6. **Keep iOS and Android configs in sync** — Same rules, Android adds `uri` property

## Debugging Tips

1. **View not presenting as modal?** Check `context: "modal"` and pattern regex
2. **Pull-to-refresh not working?** Verify `pull_to_refresh_enabled: true` and no overriding rule
3. **Wrong screen appearing?** Rules are sequential — check for pattern conflicts
4. **Android crash on navigation?** Verify `uri` maps to registered Fragment
5. **iOS custom controller not loading?** Confirm `PathConfigurationIdentifiable` conformance
