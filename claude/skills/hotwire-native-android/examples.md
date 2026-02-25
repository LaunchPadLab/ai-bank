# Examples - Android

## Complete App Setup

### MyApplication.kt

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
            BridgeComponentFactory("form", ::FormComponent),
            BridgeComponentFactory("menu", ::MenuComponent)
        )
        
        // Native fragments
        Hotwire.registerFragmentDestinations(
            FragmentDestination("hotwire://fragment/settings", SettingsFragment::class)
        )
        
        // Route handler
        Hotwire.config.routeDecisionHandler = AppRouteDecisionHandler()
        
        // Debug
        Hotwire.config.debugLoggingEnabled = BuildConfig.DEBUG
        Hotwire.config.webViewDebuggingEnabled = BuildConfig.DEBUG
    }
}
```

### MainActivity.kt

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

### activity_main.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.fragment.app.FragmentContainerView
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/navigator_host"
    android:name="dev.hotwire.navigation.navigator.NavigatorHost"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
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

### Kotlin

```kotlin
class MenuComponent(
    name: String,
    private val delegate: BridgeDelegate<HotwireDestination>
) : BridgeComponent<HotwireDestination>(name, delegate) {

    private val fragment: Fragment?
        get() = delegate.destination.fragment

    override fun onReceive(message: Message) {
        if (message.event == "show") {
            handleShow(message)
        }
    }

    private fun handleShow(message: Message) {
        val data = message.data<MenuData>() ?: return
        val context = fragment?.requireContext() ?: return

        AlertDialog.Builder(context)
            .setItems(data.items.map { it.title }.toTypedArray()) { _, which ->
                val item = data.items[which]
                replyTo(message.id, mapOf("event" to item.event))
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    @Serializable
    data class MenuData(val items: List<MenuItem>)

    @Serializable
    data class MenuItem(
        val title: String,
        val event: String,
        val destructive: Boolean = false
    )
}
```

## Bottom Navigation App

### MainActivity.kt

```kotlin
class MainActivity : HotwireActivity() {
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
    
    override fun navigatorConfigurations() = listOf(
        NavigatorConfiguration("home", "https://your-app.com", R.id.home_nav_host),
        NavigatorConfiguration("profile", "https://your-app.com/profile", R.id.profile_nav_host)
    )
    
    private fun showNavigator(name: String) {
        val transaction = supportFragmentManager.beginTransaction()
        supportFragmentManager.fragments.filterIsInstance<NavigatorHost>().forEach { host ->
            if (host.navigator.configuration.name == name) {
                transaction.show(host)
            } else {
                transaction.hide(host)
            }
        }
        transaction.commit()
    }
}
```

### activity_main.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
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

## Native Settings Screen

### SettingsFragment.kt

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
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        view.findViewById<Button>(R.id.btn_notifications).setOnClickListener {
            // Handle notifications settings
        }
        
        view.findViewById<Button>(R.id.btn_logout).setOnClickListener {
            logout()
        }
    }
    
    private fun logout() {
        // Clear auth and navigate to login
        navigator.clearAll()
        navigator.route("https://your-app.com/login")
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
        "uri": "hotwire://fragment/settings"
      }
    }
  ]
}
```

## Route Decision Handler

```kotlin
class AppRouteDecisionHandler : RouteDecisionHandler {
    override fun decide(
        location: String,
        configuration: NavigatorConfiguration,
        properties: PathProperties
    ): RouteDecision {
        return when {
            // External links
            !location.contains("your-app.com") -> {
                RouteDecision.NavigateToExternalBrowser(location)
            }
            // Sign out
            location.contains("/sign_out") -> {
                // Handle sign out logic here
                RouteDecision.Cancel
            }
            else -> RouteDecision.Navigate
        }
    }
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
