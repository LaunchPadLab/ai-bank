# Examples - iOS

## Complete App Setup

### AppDelegate.swift

```swift
import UIKit
import HotwireNative

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Path configuration
        let localURL = Bundle.main.url(forResource: "path-configuration", withExtension: "json")!
        let remoteURL = URL(string: "https://your-app.com/path-configuration.json")!
        Hotwire.loadPathConfiguration(from: [.file(localURL), .server(remoteURL)])
        
        // Bridge components
        Hotwire.registerBridgeComponents([
            ButtonComponent.self,
            FormComponent.self,
            MenuComponent.self
        ])
        
        // Native screens
        Hotwire.registerPathConfigurationIdentifiable(SettingsViewController.self)
        
        Hotwire.config.debugLoggingEnabled = true
        
        return true
    }
}
```

### SceneDelegate.swift

```swift
import UIKit
import HotwireNative

class SceneDelegate: UIResponder, UIWindowSceneDelegate, NavigatorDelegate {
    var window: UIWindow?
    
    private lazy var navigator = Navigator(
        configuration: .init(name: "main", startLocation: URL(string: "https://your-app.com")!),
        delegate: self
    )
    
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = navigator.rootViewController
        window?.makeKeyAndVisible()
        
        navigator.start()
    }
    
    // MARK: - NavigatorDelegate
    
    func handle(proposal: VisitProposal) -> ProposalResult {
        // External links
        guard proposal.url.host == "your-app.com" else {
            UIApplication.shared.open(proposal.url)
            return .reject
        }
        
        // Sign out
        if proposal.url.path == "/sign_out" {
            logout()
            return .reject
        }
        
        return .accept
    }
    
    func visitableDidFailRequest(_ visitable: Visitable, error: Error) {
        if case TurboError.http(401) = error {
            navigator.route(URL(string: "https://your-app.com/login")!)
        }
    }
    
    private func logout() {
        // Clear session and navigate to login
    }
}
```

## Menu Bridge Component

### HTML

```html
<div data-controller="menu" 
     data-menu-items-value='[{"title":"Edit","event":"edit"},{"title":"Delete","event":"delete","destructive":true}]'>
  <button data-action="menu#show">⋮</button>
</div>
```

### JavaScript

```javascript
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "menu"
  static values = { items: Array }

  show() {
    this.send("show", { items: this.itemsValue }, (message) => {
      this.dispatch(message.data.event)
    })
  }
}
```

### Swift

```swift
final class MenuComponent: BridgeComponent {
    override class var name: String { "menu" }
    
    private var viewController: UIViewController? {
        delegate?.destination as? UIViewController
    }
    
    override func onReceive(message: Message) {
        guard message.event == "show",
              let data: MenuData = message.data() else { return }
        
        let alert = UIAlertController(title: nil, message: nil, preferredStyle: .actionSheet)
        
        for item in data.items {
            let style: UIAlertAction.Style = item.destructive ? .destructive : .default
            alert.addAction(UIAlertAction(title: item.title, style: style) { [weak self] _ in
                self?.reply(to: "show", with: ["event": item.event])
            })
        }
        
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        viewController?.present(alert, animated: true)
    }
    
    struct MenuData: Decodable {
        let items: [MenuItem]
    }
    
    struct MenuItem: Decodable {
        let title: String
        let event: String
        var destructive: Bool = false
    }
}
```

## Tab Bar App

```swift
class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    
    private lazy var homeNavigator = Navigator(configuration: .init(
        name: "home",
        startLocation: URL(string: "https://your-app.com")!
    ))
    
    private lazy var profileNavigator = Navigator(configuration: .init(
        name: "profile", 
        startLocation: URL(string: "https://your-app.com/profile")!
    ))
    
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        
        let tabBar = UITabBarController()
        
        homeNavigator.rootViewController.tabBarItem = UITabBarItem(
            title: "Home",
            image: UIImage(systemName: "house"),
            tag: 0
        )
        
        profileNavigator.rootViewController.tabBarItem = UITabBarItem(
            title: "Profile",
            image: UIImage(systemName: "person"),
            tag: 1
        )
        
        tabBar.viewControllers = [
            homeNavigator.rootViewController,
            profileNavigator.rootViewController
        ]
        
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = tabBar
        window?.makeKeyAndVisible()
        
        homeNavigator.start()
        profileNavigator.start()
    }
}
```

## Native Settings Screen

### SettingsViewController.swift

```swift
import UIKit
import HotwireNative

class SettingsViewController: UITableViewController, PathConfigurationIdentifiable {
    static var pathConfigurationIdentifier: String { "settings" }
    
    private let options = ["Notifications", "Privacy", "About"]
    
    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Settings"
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "cell")
    }
    
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        options.count
    }
    
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "cell", for: indexPath)
        cell.textLabel?.text = options[indexPath.row]
        cell.accessoryType = .disclosureIndicator
        return cell
    }
}
```

### path-configuration.json

```json
{
  "rules": [
    {
      "patterns": ["/settings"],
      "properties": {
        "view_controller": "settings"
      }
    }
  ]
}
```

## Rails Helpers

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  include Turbo::Native::Navigation
  
  def redirect_back_or_to(fallback, **options)
    if turbo_native_app?
      recede_or_redirect_to(fallback, **options)
    else
      redirect_back(fallback_location: fallback, **options)
    end
  end
end

# app/controllers/posts_controller.rb  
class PostsController < ApplicationController
  def create
    @post = Post.create(post_params)
    redirect_back_or_to posts_path
  end
  
  def update
    @post.update(post_params)
    recede_or_redirect_to @post
  end
end
```

## Hide Web Elements in Native

```css
/* app/assets/stylesheets/hotwire_native.css */
[data-bridge-components~="button"] [data-controller~="button"],
[data-bridge-components~="form"] [data-controller~="form"] button[type="submit"],
[data-bridge-components~="menu"] [data-controller~="menu"] {
  display: none;
}
```

```erb
<!-- app/views/layouts/application.html.erb -->
<body data-bridge-components="<%= Hotwire::Native.bridge_components.join(' ') %>">
```
