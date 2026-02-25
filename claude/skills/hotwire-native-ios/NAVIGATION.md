# Navigation - iOS

Configure URL-to-presentation mappings and control navigation behavior.

## Path Configuration

Bundle locally + load remote for updates:

```swift
// AppDelegate
let localURL = Bundle.main.url(forResource: "path-configuration", withExtension: "json")!
let remoteURL = URL(string: "https://your-app.com/path-configuration.json")!

Hotwire.loadPathConfiguration(from: [
    .file(localURL),
    .server(remoteURL)
])
```

### JSON Structure

```json
{
  "settings": {
    "screenshots_enabled": true
  },
  "rules": [
    {
      "patterns": [".*"],
      "properties": {
        "context": "default",
        "pull_to_refresh_enabled": true
      }
    },
    {
      "patterns": ["/new$", "/edit$"],
      "properties": {
        "context": "modal",
        "pull_to_refresh_enabled": false
      }
    },
    {
      "patterns": ["/settings"],
      "properties": {
        "view_controller": "settings"
      }
    }
  ]
}
```

### Properties

| Property | Values | Description |
|----------|--------|-------------|
| context | `default`, `modal` | Push vs present modally |
| pull_to_refresh_enabled | bool | Enable pull-to-refresh |
| view_controller | string | Native screen identifier |
| presentation | `default`, `pop`, `replace`, `refresh`, `clear_all`, `replace_root`, `none` | How to present |

## Navigator Setup

### Basic

```swift
let navigator = Navigator(configuration: .init(
    name: "main",
    startLocation: URL(string: "https://your-app.com")!
))
window?.rootViewController = navigator.rootViewController
navigator.start()
```

### With Delegate

```swift
class SceneDelegate: UIResponder, UIWindowSceneDelegate, NavigatorDelegate {
    private lazy var navigator = Navigator(
        configuration: .init(name: "main", startLocation: startURL),
        delegate: self
    )
    
    func handle(proposal: VisitProposal) -> ProposalResult {
        // Custom handling
        return .accept
    }
}
```

## Tab Navigation

```swift
let mainNavigator = Navigator(configuration: .init(name: "main", startLocation: mainURL))
let settingsNavigator = Navigator(configuration: .init(name: "settings", startLocation: settingsURL))

let tabBarController = HotwireTabBarController()
tabBarController.viewControllers = [
    mainNavigator.rootViewController,
    settingsNavigator.rootViewController
]

// Configure tab items
mainNavigator.rootViewController.tabBarItem = UITabBarItem(
    title: "Home",
    image: UIImage(systemName: "house"),
    tag: 0
)
```

## Programmatic Navigation

```swift
// Push
navigator.route(URL(string: "https://your-app.com/posts/1")!)

// Present modal
navigator.route(
    URL(string: "https://your-app.com/posts/new")!,
    options: VisitOptions(action: .advance),
    properties: ["context": "modal"]
)

// Replace current
navigator.route(
    url,
    options: VisitOptions(action: .replace)
)

// Pop/dismiss
navigator.pop()
navigator.dismiss()
```

## Native Screens

### Protocol Conformance

```swift
class SettingsViewController: UIViewController, PathConfigurationIdentifiable {
    static var pathConfigurationIdentifier: String { "settings" }
}
```

### Registration

```swift
// AppDelegate or SceneDelegate
Hotwire.registerPathConfigurationIdentifiable(SettingsViewController.self)
```

### Path Configuration

```json
{
  "patterns": ["/settings"],
  "properties": {
    "view_controller": "settings"
  }
}
```

## NavigatorDelegate

```swift
extension SceneDelegate: NavigatorDelegate {
    func handle(proposal: VisitProposal) -> ProposalResult {
        switch proposal.url.path {
        case "/sign_out":
            signOut()
            return .reject
        case let path where path.hasPrefix("/external"):
            UIApplication.shared.open(proposal.url)
            return .reject
        default:
            return .accept
        }
    }
    
    func visitableDidFailRequest(_ visitable: Visitable, error: Error) {
        // Handle errors
    }
}
```

## External Links

Handle links that should open in Safari:

```swift
func handle(proposal: VisitProposal) -> ProposalResult {
    guard proposal.url.host == "your-app.com" else {
        UIApplication.shared.open(proposal.url)
        return .reject
    }
    return .accept
}
```
