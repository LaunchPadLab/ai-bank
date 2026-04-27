# Authentication - Android

Cookie-based and token-based auth patterns for Hotwire Native.

## Cookie-Based (Simple)

WebView persists cookies automatically. Rails session cookies work out of the box.

```ruby
# Rails - sessions work normally
class SessionsController < ApplicationController
  def create
    session[:user_id] = user.id
    redirect_to root_path
  end
end
```

## Token-Based

For APIs using Bearer tokens, sync tokens to WebView cookies.

### Store Token in SharedPreferences (Encrypted)

```kotlin
// build.gradle.kts
dependencies {
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
}
```

```kotlin
class TokenStore(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "secure_prefs",
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun save(token: String) {
        prefs.edit().putString("auth_token", token).apply()
    }
    
    fun retrieve(): String? {
        return prefs.getString("auth_token", null)
    }
    
    fun clear() {
        prefs.edit().remove("auth_token").apply()
    }
}
```

### Sync to WebView Cookie

```kotlin
class CookieManager(private val tokenStore: TokenStore) {
    fun syncTokenToWebView() {
        val token = tokenStore.retrieve() ?: return
        
        val cookieManager = android.webkit.CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)
        
        val cookie = "auth_token=$token; Path=/; Secure; HttpOnly"
        cookieManager.setCookie("https://your-app.com", cookie)
        cookieManager.flush()
    }
    
    fun clearCookies() {
        val cookieManager = android.webkit.CookieManager.getInstance()
        cookieManager.removeAllCookies(null)
        cookieManager.flush()
    }
}
```

### Call Before Navigation

```kotlin
class MyApplication : Application() {
    lateinit var tokenStore: TokenStore
    lateinit var cookieManager: CookieManager
    
    override fun onCreate() {
        super.onCreate()
        
        tokenStore = TokenStore(this)
        cookieManager = CookieManager(tokenStore)
        cookieManager.syncTokenToWebView()
        
        // ... rest of Hotwire setup
    }
}
```

## Handle 401 Unauthorized

```kotlin
class MyRouteDecisionHandler(
    private val navigator: Navigator
) : RouteDecisionHandler {
    
    override fun decide(
        location: String,
        configuration: NavigatorConfiguration,
        properties: PathProperties
    ): RouteDecision {
        return RouteDecision.Navigate
    }
}

// In Fragment, override error handling
class WebFragment : HotwireWebFragment() {
    override fun onVisitErrorReceived(location: String, errorCode: Int) {
        if (errorCode == 401) {
            navigator.route("https://your-app.com/login")
        } else {
            super.onVisitErrorReceived(location, errorCode)
        }
    }
}
```

## OkHttp Interceptor for API Calls

```kotlin
class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = tokenStore.retrieve()
        
        val request = chain.request().newBuilder().apply {
            token?.let { addHeader("Authorization", "Bearer $it") }
        }.build()
        
        return chain.proceed(request)
    }
}

// Configure OkHttp
val client = OkHttpClient.Builder()
    .addInterceptor(AuthInterceptor(tokenStore))
    .build()
```

## OAuth / Custom Tabs

```kotlin
class AuthManager(private val activity: Activity) {
    fun authenticate() {
        val authUrl = "https://your-app.com/auth/google"
        
        val builder = CustomTabsIntent.Builder()
        val customTabsIntent = builder.build()
        customTabsIntent.launchUrl(activity, Uri.parse(authUrl))
    }
}

// Handle callback in Activity
override fun onNewIntent(intent: Intent?) {
    super.onNewIntent(intent)
    
    intent?.data?.let { uri ->
        if (uri.scheme == "yourapp" && uri.host == "auth") {
            val token = uri.getQueryParameter("token")
            token?.let {
                (application as MyApplication).tokenStore.save(it)
                (application as MyApplication).cookieManager.syncTokenToWebView()
                navigator.refresh()
            }
        }
    }
}
```

### AndroidManifest.xml

```xml
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="yourapp" android:host="auth" />
    </intent-filter>
</activity>
```

## Logout

```kotlin
fun logout() {
    val app = application as MyApplication
    
    // Clear token
    app.tokenStore.clear()
    
    // Clear cookies
    app.cookieManager.clearCookies()
    
    // Navigate to login
    navigator.clearAll()
    navigator.route("https://your-app.com/login")
}
```

## Rails Server Setup

```ruby
class ApplicationController < ActionController::Base
  before_action :authenticate_from_cookie
  
  private
  
  def authenticate_from_cookie
    return if current_user
    if token = cookies[:auth_token]
      self.current_user = User.find_by_auth_token(token)
    end
  end
end
```
