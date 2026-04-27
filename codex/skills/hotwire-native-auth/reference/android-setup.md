# Android Setup for Hotwire Native Authentication

## AuthenticationComponent

Receives `signIn`/`signOut` messages from the JavaScript bridge and forwards them to MainActivity.

```kotlin
// AuthenticationComponent.kt
package com.example.app

import android.util.Log
import dev.hotwire.core.bridge.BridgeComponent
import dev.hotwire.core.bridge.BridgeDelegate
import dev.hotwire.core.bridge.Message
import dev.hotwire.navigation.destinations.HotwireDestination
import androidx.fragment.app.Fragment

class AuthenticationComponent(
    name: String,
    private val delegate: BridgeDelegate<HotwireDestination>
) : BridgeComponent<HotwireDestination>(name, delegate) {
    private val fragment: Fragment
        get() = delegate.destination.fragment

    private val mainActivity: MainActivity
        get() = fragment.activity as MainActivity

    override fun onReceive(message: Message) {
        when (message.event) {
            "signIn" -> mainActivity.signIn()
            "signOut" -> mainActivity.signOut()
            else -> Log.w("AuthenticationComponent", "Unknown event for message: $message")
        }
    }
}
```

## Application Subclass

Register the bridge component and load path configuration:

```kotlin
// AuthenticationApplication.kt
package com.example.app

import android.app.Application
import dev.hotwire.core.bridge.BridgeComponentFactory
import dev.hotwire.core.bridge.Hotwire
import dev.hotwire.core.config.Hotwire as HotwireConfig

class AuthenticationApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        Hotwire.registerBridgeComponents(
            BridgeComponentFactory("authentication", ::AuthenticationComponent)
        )

        HotwireConfig.loadPathConfiguration(
            context = this,
            location = PathConfiguration.Location(
                remoteFileUrl = "${rootUrl}/configuration/android.json"
            )
        )
    }
}
```

Don't forget to register in `AndroidManifest.xml`:

```xml
<application
    android:name=".AuthenticationApplication"
    ... >
```

## MainActivity

Manages bottom navigation and handles sign in/out transitions:

```kotlin
// MainActivity.kt
package com.example.app

import android.os.Bundle
import android.view.View
import androidx.activity.enableEdgeToEdge
import dev.hotwire.navigation.activities.HotwireActivity
import dev.hotwire.navigation.navigator.NavigatorConfiguration
import dev.hotwire.navigation.tabs.HotwireBottomNavigationController
import dev.hotwire.navigation.tabs.Visibility

const val rootUrl = "http://10.0.2.2:3000"

class MainActivity : HotwireActivity() {
    private var bottomNavigationController: HotwireBottomNavigationController? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        findViewById<View>(R.id.main_layout)
            .applyDefaultImeWindowInsets()

        initializeBottomTabs()
    }

    private fun initializeBottomTabs() {
        bottomNavigationController = HotwireBottomNavigationController(
            activity = this,
            bottomNavigationView = findViewById(R.id.bottom_nav)
        )
        // Start in unauthenticated state
        bottomNavigationController?.load(unauthenticatedTabs)
        bottomNavigationController?.visibility = Visibility.HIDDEN
    }

    override fun navigatorConfigurations(): List<NavigatorConfiguration> {
        return allTabs.map { it.configuration } +
               unauthenticatedTabs.map { it.configuration }
    }

    fun signIn() {
        if (bottomNavigationController?.tabs?.size != allTabs.size) {
            bottomNavigationController?.visibility = Visibility.DEFAULT
            bottomNavigationController?.load(allTabs)
            delegate.resetNavigators()
        }
    }

    fun signOut() {
        if (bottomNavigationController?.tabs?.size != unauthenticatedTabs.size) {
            bottomNavigationController?.visibility = Visibility.HIDDEN
            bottomNavigationController?.load(unauthenticatedTabs)
            delegate.resetNavigators()
        }
    }
}
```

### Why `delegate.resetNavigators()`?

On Android, calling `load()` on the bottom navigation controller only sets up the UI and callbacks - it does **not** trigger any network requests. `delegate.resetNavigators()` forces the navigators to reload their content, which is necessary after switching between tab sets.

## Tab Definitions

```kotlin
// Tabs.kt
package com.example.app

import dev.hotwire.navigation.navigator.NavigatorConfiguration
import dev.hotwire.navigation.tabs.HotwireBottomTab

val signInTab = HotwireBottomTab(
    title = "Sign In",
    iconResId = R.drawable.ic_tab_sign_in,
    configuration = NavigatorConfiguration(
        name = "sign-in",
        navigatorHostId = R.id.posts_navigator_host,
        startLocation = "$rootUrl/session/new"
    )
)

val postsTab = HotwireBottomTab(
    title = "Posts",
    iconResId = R.drawable.ic_tab_posts,
    configuration = NavigatorConfiguration(
        name = "posts",
        navigatorHostId = R.id.posts_navigator_host,
        startLocation = "$rootUrl/posts"
    )
)

val myProfileTab = HotwireBottomTab(
    title = "My Profile",
    iconResId = R.drawable.ic_tab_my_profile,
    configuration = NavigatorConfiguration(
        name = "my-profile",
        navigatorHostId = R.id.my_profile_navigator_host,
        startLocation = "$rootUrl/profile"
    )
)

val unauthenticatedTabs = listOf(signInTab)
val allTabs = listOf(postsTab, myProfileTab)
```

Create tab icons via Android Studio: **File -> New -> Image Asset** with "Action Bar and Tab Icons" type.

## Activity Layout

Each tab needs a `FragmentContainerView` with a unique ID matching the `navigatorHostId` in the tab definitions:

```xml
<!-- res/layout/activity_main.xml -->
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:id="@+id/main_layout"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <androidx.fragment.app.FragmentContainerView
        android:id="@+id/posts_navigator_host"
        android:name="dev.hotwire.navigation.navigator.NavigatorHost"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        app:layout_constraintBottom_toTopOf="@id/bottom_nav"
        app:layout_constraintTop_toTopOf="parent" />

    <androidx.fragment.app.FragmentContainerView
        android:id="@+id/my_profile_navigator_host"
        android:name="dev.hotwire.navigation.navigator.NavigatorHost"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        app:layout_constraintBottom_toTopOf="@id/bottom_nav"
        app:layout_constraintTop_toTopOf="parent" />

    <com.google.android.material.bottomnavigation.BottomNavigationView
        android:id="@+id/bottom_nav"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

## Key Implementation Notes

1. **Server URL**: Android emulator uses `10.0.2.2` to reach `localhost` on the host machine. Use `http://10.0.2.2:3000` for development.

2. **Start unauthenticated**: Load `unauthenticatedTabs` and set visibility to `HIDDEN` in `initializeBottomTabs()` so the app launches showing only the sign-in screen without a bottom nav.

3. **Navigator configurations**: The `navigatorConfigurations()` must return configs for ALL tabs (both authenticated and unauthenticated) so Hotwire Native can create the necessary fragment hosts.

4. **Idempotency guards**: Same as iOS - the bridge fires on every page load, so `signIn()`/`signOut()` must check if the correct tabs are already loaded before acting.

5. **Cookie sharing**: Android's `WebView` shares cookies across all instances in the same app process. Once the user signs in, the session cookie is available to all tabs.

6. **Edge-to-edge**: Call `enableEdgeToEdge()` and `applyDefaultImeWindowInsets()` for proper display on modern Android with gesture navigation.
