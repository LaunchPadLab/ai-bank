---
name: hotwire-native-auth
description: Implements web-based authentication for Hotwire Native iOS and Android apps. Use when adding authentication to a Hotwire Native app, integrating sign in/sign out with native tab bars, setting up bridge components for auth state, or when user mentions Hotwire Native authentication, native app auth, or mobile auth with Rails.
allowed-tools: Read, Write, Edit, Bash
---

# Hotwire Native: Web-Based Authentication

## Overview

Web-based authentication reuses your existing Rails authentication screens and logic for Hotwire Native iOS and Android apps. Instead of building native login UI with SwiftUI/Jetpack Compose and JSON API endpoints, the native app renders the same `/session/new` HTML form and submits it via the web view.

**Benefits over native authentication:**
- Zero additional native UI code for login screens
- Zero additional API endpoints
- Reuses existing server-side authentication logic
- Single source of truth: the Rails server

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Rails Server                      │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Auth Concern │  │ Sessions │  │ Layout <meta>  │ │
│  │ (permanent   │  │Controller│  │ data-bridge-   │ │
│  │  cookie)     │  │          │  │ authenticated  │ │
│  └─────────────┘  └──────────┘  └───────┬────────┘ │
└─────────────────────────────────────────┼───────────┘
                                          │
              ┌───────────────────────────┼──────┐
              │  JS Bridge Component      │      │
              │  (Stimulus controller)    ▼      │
              │  sends signIn/signOut message    │
              └──────────┬──────────────────────┘
                         │
            ┌────────────┼────────────┐
            ▼                         ▼
   ┌─────────────────┐    ┌─────────────────────┐
   │  iOS Bridge      │    │  Android Bridge      │
   │  Component       │    │  Component           │
   │  → SceneDelegate │    │  → MainActivity      │
   │  → Toggle tabs   │    │  → Toggle bottom nav │
   └─────────────────┘    └─────────────────────┘
```

## Implementation Steps

### Step 1: Generate a Long-Lived Cookie

Use `cookies.signed.permanent` so the session persists even after the native app is closed.

**Rolling your own auth (or Rails 8 authentication generator):**

Keep this cookie shape aligned with the web authentication concern and Action Cable connection. This skill standardizes on a signed, permanent `session_token` cookie whose value is `session.token`.

```ruby
# app/controllers/concerns/authentication.rb
def start_new_session_for(user)
  session = user.sessions.create!(
    ip_address: request.remote_ip,
    user_agent: request.user_agent
  )
  Current.session = session
  cookies.signed.permanent[:session_token] = {
    value: session.token, httponly: true, same_site: :lax
  }
end
```

**If using Devise**, always remember the user on native:

```erb
<%= form_with url: session_path do |form| %>
  <% if hotwire_native_app? %>
    <%= form.hidden_field :remember_me, value: true %>
  <% else %>
    <%= form.check_box :remember_me %>
    <%= form.label :remember_me %>
  <% end %>
<% end %>
```

### Step 2: Surface the Authentication Status

Add a `<meta>` tag in your application layout that exposes auth state on every page:

```erb
<%# app/views/layouts/application.html.erb %>
<html>
  <body>
    <meta data-controller="bridge--authentication"
      data-bridge-authenticated="<%= authenticated? %>">
    <%# ... %>
  </body>
</html>
```

Create the bridge Stimulus controller:

```bash
bin/rails generate stimulus bridge/authentication
```

```javascript
// app/javascript/controllers/bridge/authentication_controller.js
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "authentication"

  connect() {
    const authenticated = this.bridgeElement
      .bridgeAttribute("authenticated") === "true"

    if (authenticated) {
      this.send("signIn")
    } else {
      this.send("signOut")
    }
  }
}
```

> **Gotcha:** `bridgeAttribute()` returns a string, not a boolean. Both `"true"` and `"false"` are truthy in JavaScript. You MUST compare with `=== "true"`.

Pin the bridge package in your importmap:

```ruby
# config/importmap.rb
pin "@hotwired/hotwire-native-bridge", to: "@hotwired--hotwire-native-bridge.js"
```

### Step 3: Create Native Bridge Components

#### iOS Bridge Component

```swift
// App/Components/AuthenticationComponent.swift
import HotwireNative

class AuthenticationComponent: BridgeComponent {
    override nonisolated class var name: String { "authentication" }

    override func onReceive(message: Message) {
        switch message.event {
        case "signIn": sceneDelegate?.signIn()
        case "signOut": sceneDelegate?.signOut()
        default: print("AuthenticationComponent", "Unknown event: \(message)")
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

Register in AppDelegate:

```swift
Hotwire.registerBridgeComponents([
    AuthenticationComponent.self
])
```

#### Android Bridge Component

```kotlin
// AuthenticationComponent.kt
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
        }
    }
}
```

Register in your Application subclass:

```kotlin
Hotwire.registerBridgeComponents(
    BridgeComponentFactory("authentication", ::AuthenticationComponent)
)
```

### Step 4: Toggle the Tab Bar

#### iOS SceneDelegate

```swift
func signIn() {
    if tabBarController.viewControllers?.count != Tab.all.count {
        tabBarController.setTabBarHidden(false, animated: true)
        tabBarController.load(Tab.all)
    }
}

func signOut() {
    if tabBarController.viewControllers?.count != 1 {
        tabBarController.setTabBarHidden(true, animated: true)
        tabBarController.load(Tab.unauthenticated)
    }
}
```

#### Android MainActivity

```kotlin
fun signIn() {
    if (bottomNavigationController?.tabs?.size != tabs.size) {
        bottomNavigationController?.visibility = Visibility.DEFAULT
        bottomNavigationController?.load(tabs)
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
```

> **Gotcha - Infinite loop:** The bridge component fires on every page load. Without the idempotency guard (`if ... count != ...`), signing in calls `signIn()` for each tab, which reloads tabs, which triggers `signIn()` again - infinite loop.

> **Android-specific:** You must call `delegate.resetNavigators()` after `load()` because on Android, `load()` only sets up UI and callbacks - it doesn't trigger network requests.

## Supporting Rails Setup

### Native-Only CSS

Conditionally load a stylesheet that hides web-only elements from native apps:

```erb
<%# app/views/layouts/application.html.erb %>
<% if hotwire_native_app? %>
  <%= stylesheet_link_tag "native" %>
<% end %>
```

```css
/* app/assets/stylesheets/native.css */
.d-hotwire-native-none {
  display: none;
}
```

Apply to elements like page headers that are redundant in native apps:

```erb
<header class="d-hotwire-native-none">
  <%= link_to "Home", root_path %>
</header>
```

### Path Configuration Controller

Serve path configuration JSON so native apps know which URLs should be modals:

```ruby
# app/controllers/configurations_controller.rb
class ConfigurationsController < ApplicationController
  allow_unauthenticated_access

  def ios
    render json: {
      settings: {},
      rules: [
        { patterns: ["/new$", "/edit$"], properties: { context: "modal" } },
        { patterns: ["/session/new"], properties: { context: "default" } }
      ]
    }
  end

  def android
    render json: {
      settings: {},
      rules: [
        { patterns: [".*"], properties: { context: "default", pull_to_refresh_enabled: true } },
        { patterns: ["/new$", "/edit$"], properties: { context: "modal" } },
        { patterns: ["/session/new"], properties: { context: "default" } }
      ]
    }
  end
end
```

```ruby
# config/routes.rb
resource :configuration, only: [], constraints: { format: :json } do
  get :ios, on: :member
  get :android, on: :member
end
```

> **Important:** `/session/new` must be `context: "default"` (not modal) so the sign-in screen displays as a full page, and place it after the modal rules so it takes precedence.

### Sign-In View for Native

Hide the page header on native since navigation is handled natively:

```erb
<%# app/views/sessions/new.html.erb %>
<header class="d-hotwire-native-none">
  <h1>Sign In</h1>
</header>

<%= form_with url: session_path, data: { turbo_action: "replace" } do |form| %>
  <%= form.email_field :email_address %>
  <%= form.password_field :password %>
  <%= form.submit "Sign in" %>
<% end %>
```

Use `data: { turbo_action: "replace" }` on the form so Turbo replaces the page instead of pushing to the navigation stack after sign-in.

## Workflow Checklist

```
Hotwire Native Auth Implementation:

Rails:
- [ ] Authentication uses cookies.signed.permanent (not session-only cookies)
- [ ] <meta> tag with data-bridge-authenticated in application layout
- [ ] Bridge Stimulus controller at bridge/authentication_controller.js
- [ ] @hotwired/hotwire-native-bridge pinned in importmap
- [ ] native.css loaded conditionally for hotwire_native_app?
- [ ] .d-hotwire-native-none hides web headers in native
- [ ] Path configuration endpoints (iOS + Android)
- [ ] /session/new set to default context (not modal)
- [ ] Sign-in form uses data-turbo-action="replace"

iOS:
- [ ] AuthenticationComponent registered in AppDelegate
- [ ] SceneDelegate has signIn()/signOut() with idempotency guards
- [ ] Tab definitions for authenticated and unauthenticated states
- [ ] Path configuration loaded from server
- [ ] App starts in unauthenticated state

Android:
- [ ] AuthenticationComponent registered in Application subclass
- [ ] MainActivity has signIn()/signOut() with idempotency guards
- [ ] delegate.resetNavigators() called after loading tabs
- [ ] Tab definitions for authenticated and unauthenticated states
- [ ] activity_main.xml has FragmentContainerViews + BottomNavigationView
- [ ] Path configuration loaded from server
- [ ] App starts in unauthenticated state
```

## Common Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Bridge never fires | Missing `@hotwired/hotwire-native-bridge` pin | Add to importmap.rb |
| Auth always truthy in JS | `bridgeAttribute()` returns string | Compare with `=== "true"` |
| Infinite loop on sign in | `signIn()` reloads tabs, triggers bridge again | Add idempotency check on tab count |
| Tab bar flashes on cold start | App starts with all tabs visible | Start in unauthenticated state |
| Android tabs don't load content | `load()` doesn't trigger requests | Call `delegate.resetNavigators()` |
| Sign-in opens as modal | Path config matches `/new$` | Add `/session/new` rule with `context: "default"` after modal rules |
| Native app loses session | Cookie not permanent | Use `cookies.signed.permanent` |

## References

- See [rails-setup.md](reference/rails-setup.md) for complete Rails-side code
- See [ios-setup.md](reference/ios-setup.md) for complete iOS code
- See [android-setup.md](reference/android-setup.md) for complete Android code
