# Navigation - Android

Configure URL-to-presentation mappings, deep links, and navigation behavior.

## Path Configuration

Bundle locally + load remote for updates:

```kotlin
// Application class
Hotwire.loadPathConfiguration(
    context = this,
    location = PathConfiguration.Location(
        assetFilePath = "json/path-configuration.json",
        remoteFileUrl = "https://your-app.com/path-configuration.json"
    )
)
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
        "uri": "hotwire://fragment/settings"
      }
    }
  ]
}
```

### Properties

| Property | Values | Description |
|----------|--------|-------------|
| context | `default`, `modal` | Forward navigation vs bottom sheet |
| pull_to_refresh_enabled | bool | Enable pull-to-refresh |
| uri | string | Native destination URI |
| presentation | `default`, `pop`, `replace`, `refresh`, `clear_all`, `replace_root`, `none` | How to present |

## Navigator Configuration

### Single Navigator

```kotlin
class MainActivity : HotwireActivity() {
    override fun navigatorConfigurations() = listOf(
        NavigatorConfiguration(
            name = "main",
            startLocation = "https://your-app.com",
            navigatorHostId = R.id.navigator_host
        )
    )
}
```

### Layout

```xml
<androidx.fragment.app.FragmentContainerView
    android:id="@+id/navigator_host"
    android:name="dev.hotwire.navigation.navigator.NavigatorHost"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

## Bottom Navigation

### Activity

```kotlin
class MainActivity : HotwireActivity() {
    override fun navigatorConfigurations() = listOf(
        NavigatorConfiguration(
            name = "home",
            startLocation = "https://your-app.com",
            navigatorHostId = R.id.home_nav_host
        ),
        NavigatorConfiguration(
            name = "profile",
            startLocation = "https://your-app.com/profile",
            navigatorHostId = R.id.profile_nav_host
        )
    )
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        findViewById<BottomNavigationView>(R.id.bottom_nav).setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> showNavigator("home")
                R.id.nav_profile -> showNavigator("profile")
            }
            true
        }
    }
    
    private fun showNavigator(name: String) {
        supportFragmentManager.fragments.forEach { fragment ->
            if (fragment is NavigatorHost) {
                supportFragmentManager.beginTransaction()
                    .apply {
                        if (fragment.navigator.configuration.name == name) show(fragment)
                        else hide(fragment)
                    }
                    .commit()
            }
        }
    }
}
```

### Layout

```xml
<LinearLayout
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <FrameLayout
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1">

        <androidx.fragment.app.FragmentContainerView
            android:id="@+id/home_nav_host"
            android:name="dev.hotwire.navigation.navigator.NavigatorHost"
            android:layout_width="match_parent"
            android:layout_height="match_parent" />

        <androidx.fragment.app.FragmentContainerView
            android:id="@+id/profile_nav_host"
            android:name="dev.hotwire.navigation.navigator.NavigatorHost"
            android:layout_width="match_parent"
            android:layout_height="match_parent"
            android:visibility="gone" />
    </FrameLayout>

    <com.google.android.material.bottomnavigation.BottomNavigationView
        android:id="@+id/bottom_nav"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        app:menu="@menu/bottom_nav" />
</LinearLayout>
```

## Programmatic Navigation

```kotlin
// From Fragment
navigator.route("https://your-app.com/posts/1")

// With options
navigator.route(
    location = "https://your-app.com/posts/new",
    options = VisitOptions(action = VisitAction.ADVANCE),
    properties = PathProperties(context = "modal")
)

// Pop
navigator.pop()

// Clear and go
navigator.clearAll()
navigator.route("https://your-app.com")

// Refresh
navigator.refresh()
```

## Native Screens (Fragments)

### Annotate Fragment

```kotlin
@HotwireDestinationDeepLink(uri = "hotwire://fragment/settings")
class SettingsFragment : HotwireFragment() {
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        return inflater.inflate(R.layout.fragment_settings, container, false)
    }
}
```

### Path Configuration

```json
{
  "patterns": ["/settings"],
  "properties": {
    "uri": "hotwire://fragment/settings"
  }
}
```

## Deep Links

### AndroidManifest.xml

```xml
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data
            android:scheme="https"
            android:host="your-app.com" />
    </intent-filter>
</activity>
```

### Handle in Activity

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    
    intent?.data?.let { uri ->
        navigator.route(uri.toString())
    }
}
```

## Route Decision Handler

Override navigation decisions:

```kotlin
class MyRouteDecisionHandler : RouteDecisionHandler {
    override fun decide(
        location: String,
        configuration: NavigatorConfiguration,
        properties: PathProperties
    ): RouteDecision {
        return when {
            location.contains("/external") -> {
                RouteDecision.NavigateToExternalBrowser(location)
            }
            location.contains("/sign_out") -> {
                RouteDecision.Cancel
            }
            else -> RouteDecision.Navigate
        }
    }
}

// Register in Application
Hotwire.config.routeDecisionHandler = MyRouteDecisionHandler()
```

### RouteDecision Options

| Decision | Description |
|----------|-------------|
| `Navigate` | Continue with normal navigation |
| `Cancel` | Cancel the navigation |
| `NavigateToExternalBrowser(url)` | Open in Chrome Custom Tab |
| `NavigateToSystemBrowser(url)` | Open in default browser |
