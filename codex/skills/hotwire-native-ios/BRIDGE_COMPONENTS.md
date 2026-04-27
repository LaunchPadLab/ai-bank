# Bridge Components - iOS

Bridge components enable native UI elements controlled from web content via JS ↔ Swift communication.

## Three-Part Architecture

1. **HTML** - Data attributes on elements
2. **JavaScript** - Stimulus controller extending `BridgeComponent`
3. **Swift** - Native component extending `BridgeComponent`

## Part 1: HTML

```html
<button data-controller="button" 
        data-bridge-title="Save"
        data-bridge-icon="checkmark">
  Save
</button>
```

## Part 2: JavaScript

```javascript
// app/javascript/controllers/button_controller.js
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "button"  // Must match Swift component name

  connect() {
    super.connect()
    
    const title = this.bridgeElement.bridgeAttribute("title")
    const icon = this.bridgeElement.bridgeAttribute("icon")
    
    this.send("connect", { title, icon }, () => {
      this.element.click()  // Callback when native replies
    })
  }
}
```

## Part 3: Swift

```swift
import HotwireNative

final class ButtonComponent: BridgeComponent {
    override class var name: String { "button" }
    
    private var viewController: UIViewController? {
        delegate?.destination as? UIViewController
    }

    override func onReceive(message: Message) {
        guard message.event == "connect",
              let data: ConnectData = message.data() else { return }
        
        let action = UIAction { [weak self] _ in
            self?.reply(to: "connect")
        }
        
        let button = UIBarButtonItem(title: data.title, primaryAction: action)
        if let icon = data.icon {
            button.image = UIImage(systemName: icon)
        }
        viewController?.navigationItem.rightBarButtonItem = button
    }
    
    struct ConnectData: Decodable {
        let title: String
        let icon: String?
    }
}
```

## Registration

```swift
// AppDelegate
Hotwire.registerBridgeComponents([
    ButtonComponent.self,
    FormComponent.self,
    MenuComponent.self
])
```

## Form Component

### JavaScript
```javascript
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "form"
  static targets = ["submit"]

  connect() {
    super.connect()
    this.send("connect", { title: this.submitTarget.value }, () => {
      this.submitTarget.click()
    })
  }

  submitStarted() { this.send("submitDisabled") }
  submitEnded() { this.send("submitEnabled") }
}
```

### Swift
```swift
final class FormComponent: BridgeComponent {
    override class var name: String { "form" }
    private weak var submitButton: UIBarButtonItem?
    
    private var viewController: UIViewController? {
        delegate?.destination as? UIViewController
    }

    override func onReceive(message: Message) {
        switch message.event {
        case "connect":
            guard let data: MessageData = message.data() else { return }
            let action = UIAction { [weak self] _ in
                self?.submitButton?.isEnabled = false
                self?.reply(to: "connect")
            }
            let button = UIBarButtonItem(title: data.title, primaryAction: action)
            button.style = .done
            viewController?.navigationItem.rightBarButtonItem = button
            submitButton = button
        case "submitEnabled":
            submitButton?.isEnabled = true
        case "submitDisabled":
            submitButton?.isEnabled = false
        default: break
        }
    }
    
    struct MessageData: Decodable { let title: String }
}
```

## Message Flow

```
Web                              Native
────                             ──────
send("connect", data) ─────────▶ onReceive(message)
                                 - Create native UI
User taps button
                    ◀─────────── reply(to: "connect")
Callback fires
```

## CSS: Hide Bridged Elements

```css
[data-bridge-components~="button"] [data-controller~="button"] {
  display: none;
}
```

## Best Practices

1. **Match names** exactly between JS and Swift
2. **Use Decodable** structs for type-safe parsing
3. **Weak references** to view controllers
4. **Hide web elements** when native equivalents exist
5. **Reply to messages** to trigger JS callbacks
