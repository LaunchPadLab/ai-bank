# API Reference - Android

## Hotwire Configuration

```kotlin
// Debug logging
Hotwire.config.debugLoggingEnabled = true

// WebView debugging (for Chrome DevTools)
Hotwire.config.webViewDebuggingEnabled = true

// Custom user agent
Hotwire.config.userAgent = "MyApp/1.0 Hotwire Native Android"

// JSON converter (for bridge component data)
Hotwire.config.jsonConverter = KotlinXJsonConverter()

// Path configuration
Hotwire.loadPathConfiguration(
    context = this,
    location = PathConfiguration.Location(
        assetFilePath = "json/path-configuration.json",
        remoteFileUrl = "https://your-app.com/path-configuration.json"
    )
)

// Register bridge components
Hotwire.registerBridgeComponents(
    BridgeComponentFactory("button", ::ButtonComponent),
    BridgeComponentFactory("form", ::FormComponent)
)

// Register fragments
Hotwire.registerFragmentDestinations(
    FragmentDestination(
        uri = "hotwire://fragment/settings",
        klass = SettingsFragment::class
    )
)

// Route decision handler
Hotwire.config.routeDecisionHandler = MyRouteDecisionHandler()
```

## HotwireActivity

```kotlin
abstract class HotwireActivity : AppCompatActivity() {
    abstract fun navigatorConfigurations(): List<NavigatorConfiguration>
}
```

## NavigatorConfiguration

```kotlin
data class NavigatorConfiguration(
    val name: String,
    val startLocation: String,
    val navigatorHostId: Int
)
```

## Navigator

### Access

```kotlin
// From HotwireFragment
val navigator = navigator

// From Activity
val navigator = findNavigator("main")
```

### Methods

| Method | Description |
|--------|-------------|
| `route(location: String)` | Navigate to URL |
| `route(location, options, properties)` | Navigate with options |
| `pop()` | Pop current screen |
| `clearAll()` | Clear navigation stack |
| `refresh()` | Refresh current page |

### VisitOptions

```kotlin
VisitOptions(action = VisitAction.ADVANCE)   // Push new
VisitOptions(action = VisitAction.REPLACE)   // Replace current
VisitOptions(action = VisitAction.RESTORE)   // Restore from cache
```

## BridgeComponent

```kotlin
abstract class BridgeComponent<D : HotwireDestination>(
    val name: String,
    protected val delegate: BridgeDelegate<D>
) {
    abstract fun onReceive(message: Message)
    
    protected fun replyTo(messageId: String)
    protected fun replyTo(messageId: String, data: Any)
}
```

### Message

```kotlin
data class Message(
    val id: String,
    val component: String,
    val event: String,
    val metadata: Metadata,
    val jsonData: String
) {
    inline fun <reified T> data(): T?
}
```

## HotwireFragment / HotwireWebFragment

```kotlin
// Base fragment for native screens
abstract class HotwireFragment : Fragment(), HotwireDestination

// Web-backed fragment
abstract class HotwireWebFragment : HotwireFragment() {
    open fun onVisitErrorReceived(location: String, errorCode: Int)
    open fun onVisitCompleted(location: String, completedOffline: Boolean)
}
```

## Path Configuration Properties

| Property | Type | Description |
|----------|------|-------------|
| `context` | String | `default` or `modal` |
| `presentation` | String | How to present screen |
| `pull_to_refresh_enabled` | Bool | Enable pull-to-refresh |
| `uri` | String | Native destination URI |

### Presentation Values

- `default` - Standard forward navigation
- `pop` - Pop to previous
- `replace` - Replace current
- `refresh` - Refresh current page
- `clear_all` - Clear stack
- `replace_root` - Replace root
- `none` - No navigation

## RouteDecisionHandler

```kotlin
interface RouteDecisionHandler {
    fun decide(
        location: String,
        configuration: NavigatorConfiguration,
        properties: PathProperties
    ): RouteDecision
}
```

### RouteDecision

| Value | Description |
|-------|-------------|
| `Navigate` | Continue with visit |
| `Cancel` | Cancel visit |
| `NavigateToExternalBrowser(url)` | Open in Chrome Custom Tab |
| `NavigateToSystemBrowser(url)` | Open in default browser |

## Annotations

### Deep Link

```kotlin
@HotwireDestinationDeepLink(uri = "hotwire://fragment/settings")
class SettingsFragment : HotwireFragment()
```

## KotlinX Serialization

```kotlin
class KotlinXJsonConverter : JsonConverter {
    private val json = Json { ignoreUnknownKeys = true }
    
    override fun <T> fromJson(jsonString: String, type: KClass<T>): T? {
        return try {
            json.decodeFromString(serializer(type.java), jsonString) as T
        } catch (e: Exception) {
            null
        }
    }
    
    override fun toJson(obj: Any): String {
        return json.encodeToString(serializer(obj::class.java), obj)
    }
}
```

## WebView Access

```kotlin
// In HotwireWebFragment
val webView = hotwireView?.webView
```
