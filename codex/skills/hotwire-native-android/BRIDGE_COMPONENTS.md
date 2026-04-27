# Bridge Components - Android

Bridge components enable native UI elements controlled from web content via JS ↔ Kotlin communication.

## Three-Part Architecture

1. **HTML** - Data attributes on elements
2. **JavaScript** - Stimulus controller extending `BridgeComponent`
3. **Kotlin** - Native component extending `BridgeComponent`

## Part 1: HTML

```html
<button data-controller="button" 
        data-bridge-title="Save"
        data-bridge-icon="check">
  Save
</button>
```

## Part 2: JavaScript

```javascript
// app/javascript/controllers/button_controller.js
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "button"  // Must match Kotlin component name

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

## Part 3: Kotlin

```kotlin
class ButtonComponent(
    name: String,
    private val delegate: BridgeDelegate<HotwireDestination>
) : BridgeComponent<HotwireDestination>(name, delegate) {

    private val fragment: Fragment?
        get() = delegate.destination.fragment

    override fun onReceive(message: Message) {
        if (message.event == "connect") {
            handleConnect(message)
        }
    }

    private fun handleConnect(message: Message) {
        val data = message.data<ConnectData>() ?: return
        
        fragment?.apply {
            val menuHost = requireActivity() as MenuHost
            menuHost.addMenuProvider(object : MenuProvider {
                override fun onCreateMenu(menu: Menu, menuInflater: MenuInflater) {
                    menu.add(data.title).apply {
                        setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS)
                    }
                }
                
                override fun onMenuItemSelected(menuItem: MenuItem): Boolean {
                    replyTo(message.id)
                    return true
                }
            }, viewLifecycleOwner)
        }
    }

    @Serializable
    data class ConnectData(
        val title: String,
        val icon: String? = null
    )
}
```

## Registration

```kotlin
// Application class
Hotwire.registerBridgeComponents(
    BridgeComponentFactory("button", ::ButtonComponent),
    BridgeComponentFactory("form", ::FormComponent),
    BridgeComponentFactory("menu", ::MenuComponent)
)
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

### Kotlin

```kotlin
class FormComponent(
    name: String,
    private val delegate: BridgeDelegate<HotwireDestination>
) : BridgeComponent<HotwireDestination>(name, delegate) {

    private var submitMenuItem: MenuItem? = null
    private val fragment: Fragment?
        get() = delegate.destination.fragment

    override fun onReceive(message: Message) {
        when (message.event) {
            "connect" -> handleConnect(message)
            "submitEnabled" -> submitMenuItem?.isEnabled = true
            "submitDisabled" -> submitMenuItem?.isEnabled = false
        }
    }

    private fun handleConnect(message: Message) {
        val data = message.data<MessageData>() ?: return
        
        fragment?.apply {
            val menuHost = requireActivity() as MenuHost
            menuHost.addMenuProvider(object : MenuProvider {
                override fun onCreateMenu(menu: Menu, menuInflater: MenuInflater) {
                    submitMenuItem = menu.add(data.title).apply {
                        setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS)
                    }
                }
                
                override fun onMenuItemSelected(menuItem: MenuItem): Boolean {
                    submitMenuItem?.isEnabled = false
                    replyTo(message.id)
                    return true
                }
            }, viewLifecycleOwner)
        }
    }

    @Serializable
    data class MessageData(val title: String)
}
```

## Message Flow

```
Web                              Native
────                             ──────
send("connect", data) ─────────▶ onReceive(message)
                                 - Create native UI
User taps button
                    ◀─────────── replyTo(message.id)
Callback fires
```

## CSS: Hide Bridged Elements

```css
[data-bridge-components~="button"] [data-controller~="button"] {
  display: none;
}
```

## Serialization

Add kotlinx.serialization:

```kotlin
// build.gradle.kts
plugins {
    kotlin("plugin.serialization") version "1.9.0"
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
}
```

## Best Practices

1. **Match names** exactly between JS and Kotlin
2. **Use @Serializable** data classes for type-safe parsing
3. **Weak references** via delegate pattern
4. **Hide web elements** when native equivalents exist
5. **Reply to messages** to trigger JS callbacks
6. **Use viewLifecycleOwner** for menu providers
