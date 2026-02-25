# iOS Setup for Hotwire Native Authentication

## AuthenticationComponent

The bridge component receives `signIn`/`signOut` messages from the JavaScript bridge and forwards them to SceneDelegate.

```swift
// App/Components/AuthenticationComponent.swift
import HotwireNative
import UIKit

class AuthenticationComponent: BridgeComponent {
    override nonisolated class var name: String { "authentication" }

    override func onReceive(message: Message) {
        switch message.event {
        case "signIn":
            sceneDelegate?.signIn()
        case "signOut":
            sceneDelegate?.signOut()
        default:
            print("AuthenticationComponent", "Unknown event for message: \(message)")
        }
    }

    private var viewController: UIViewController? {
        delegate?.destination as? UIViewController
    }

    private var sceneDelegate: SceneDelegate? {
        viewController?.view.window?
            .windowScene?.delegate as? SceneDelegate
    }
}
```

## AppDelegate

Register the bridge component and load path configuration:

```swift
// App/Delegates/AppDelegate.swift
import HotwireNative
import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        Hotwire.registerBridgeComponents([
            AuthenticationComponent.self
        ])

        Hotwire.loadPathConfiguration(from: [
            .server(rootURL.appending(path: "configuration/ios.json"))
        ])

        return true
    }
}
```

## SceneDelegate

Manages the tab bar and handles sign in/out transitions:

```swift
// App/Delegates/SceneDelegate.swift
import HotwireNative
import UIKit

let rootURL = URL(string: "http://localhost:3000")!

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    private let tabBarController = HotwireTabBarController()

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        window = UIWindow(windowScene: windowScene)
        window?.makeKeyAndVisible()
        window?.rootViewController = tabBarController

        // Start in unauthenticated state
        signOut()
    }

    func signIn() {
        if tabBarController.viewControllers?.count != Tab.all.count {
            tabBarController.setTabBarHidden(false, animated: true)
            tabBarController.load(Tab.all)
        }
    }

    func signOut() {
        if tabBarController.viewControllers?.count != Tab.unauthenticated.count {
            tabBarController.setTabBarHidden(true, animated: true)
            tabBarController.load(Tab.unauthenticated)
        }
    }
}
```

### Idempotency Guards

The `if` checks prevent an infinite loop. The bridge component fires on **every page load**. Without the guard:

1. User signs in -> bridge sends `signIn`
2. `signIn()` calls `tabBarController.load(tabs)`
3. Loading tabs triggers new page loads
4. Each page load fires the bridge again -> `signIn()` called again
5. Infinite loop

The guard checks if the correct tabs are already loaded before doing anything.

## Tab Definitions

```swift
// App/Models/Tab.swift
import HotwireNative
import UIKit

enum Tab {
    static let unauthenticated = [
        HotwireTab(
            title: "Sign In",
            image: UIImage(systemName: "person")!,
            url: rootURL.appending(path: "session/new")
        )
    ]

    static let all = [
        HotwireTab(
            title: "Posts",
            image: UIImage(systemName: "text.document")!,
            url: rootURL.appending(path: "posts")
        ),
        HotwireTab(
            title: "My Profile",
            image: UIImage(systemName: "person")!,
            url: rootURL.appending(path: "profile")
        )
    ]
}
```

Use SF Symbols for tab icons to avoid bundling custom image assets.

## Key Implementation Notes

1. **Start unauthenticated**: Call `signOut()` in `scene(_:willConnectTo:)` so the app launches showing only the sign-in tab with a hidden tab bar.

2. **Tab bar visibility**: `setTabBarHidden(true)` hides the tab bar when unauthenticated (showing just the sign-in screen). `setTabBarHidden(false)` shows it when authenticated.

3. **Cookie sharing**: The `WKWebView` used by Hotwire Native shares cookies with all web views in the app. Once the user signs in via the web form, the session cookie is available to all tabs.

4. **Path configuration**: Loaded from the server so you can control modal/default presentation without an app update. The `/session/new` path should always be `context: "default"` (not modal).

5. **Server URL**: Use `http://localhost:3000` for development. Change to your production URL for release builds. Consider using environment-based configuration.
