# API Reference - iOS

## Hotwire Configuration

```swift
// Debug logging
Hotwire.config.debugLoggingEnabled = true

// Custom user agent
Hotwire.config.userAgent = "MyApp/1.0 Hotwire Native iOS"

// Path configuration
Hotwire.loadPathConfiguration(from: [
    .file(localURL),
    .server(remoteURL)
])

// Register bridge components
Hotwire.registerBridgeComponents([
    ButtonComponent.self,
    FormComponent.self
])

// Register native screens
Hotwire.registerPathConfigurationIdentifiable(SettingsViewController.self)
```

## Navigator

### Initialization

```swift
let navigator = Navigator(
    configuration: NavigatorConfiguration(
        name: "main",
        startLocation: URL(string: "https://your-app.com")!
    ),
    delegate: self
)
```

### Methods

| Method | Description |
|--------|-------------|
| `start()` | Begin navigation |
| `route(_ url: URL)` | Navigate to URL |
| `route(_ url: URL, options:, properties:)` | Navigate with options |
| `pop()` | Pop current screen |
| `dismiss()` | Dismiss modal |
| `clearAll()` | Clear navigation stack |
| `refresh()` | Refresh current page |

### VisitOptions

```swift
VisitOptions(action: .advance)  // Push new
VisitOptions(action: .replace)  // Replace current
VisitOptions(action: .restore)  // Restore from cache
```

## NavigatorDelegate

```swift
protocol NavigatorDelegate {
    func handle(proposal: VisitProposal) -> ProposalResult
    func visitableDidFailRequest(_ visitable: Visitable, error: Error)
    func visitableDidRender(_ visitable: Visitable)
}
```

### ProposalResult

| Value | Description |
|-------|-------------|
| `.accept` | Continue with visit |
| `.acceptCustom(ViewController)` | Use custom view controller |
| `.reject` | Cancel visit |

## BridgeComponent

```swift
class MyComponent: BridgeComponent {
    override class var name: String { "my-component" }
    
    // Access destination
    var viewController: UIViewController? {
        delegate?.destination as? UIViewController
    }
    
    override func onReceive(message: Message) {
        // Handle message from JS
    }
    
    // Send to JS
    func sendToWeb() {
        reply(to: "eventName")
        reply(to: "eventName", with: ["key": "value"])
    }
}
```

### Message

```swift
struct Message {
    let id: String
    let component: String
    let event: String
    let metadata: Metadata
    
    func data<T: Decodable>() -> T?
}
```

## Path Configuration Properties

| Property | Type | Description |
|----------|------|-------------|
| `context` | String | `default` or `modal` |
| `presentation` | String | How to present screen |
| `pull_to_refresh_enabled` | Bool | Enable pull-to-refresh |
| `view_controller` | String | Native screen identifier |

### Presentation Values

- `default` - Standard navigation push/present
- `pop` - Pop to previous
- `replace` - Replace current
- `refresh` - Refresh current page
- `clear_all` - Clear stack
- `replace_root` - Replace root
- `none` - No navigation

## Error Handling (v1.3+)

### Custom Error Views

```swift
class MyErrorViewController: UIViewController, ErrorPresenter {
    func presentError(_ error: Error, retryHandler: @escaping () -> Void) {
        // Show error UI with retry button
    }
}

// Register
Hotwire.config.makeCustomErrorViewController = { error in
    return MyErrorViewController()
}
```

## PathConfigurationIdentifiable

```swift
protocol PathConfigurationIdentifiable {
    static var pathConfigurationIdentifier: String { get }
}
```

## HotwireTabBarController

```swift
let tabBar = HotwireTabBarController()
tabBar.viewControllers = [nav1.rootViewController, nav2.rootViewController]
```

## WKWebView Access

```swift
// Access WebView on Visitable
if let visitable = viewController as? VisitableViewController {
    let webView = visitable.visitableView.webView
}
```
