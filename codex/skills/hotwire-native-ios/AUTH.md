# Authentication - iOS

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

For APIs using Bearer tokens, sync tokens to WebView cookies:

### Store Token in Keychain

```swift
import Security

class TokenStore {
    static let shared = TokenStore()
    
    func save(token: String) {
        let data = token.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "authToken",
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    func retrieve() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "authToken",
            kSecReturnData as String: true
        ]
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        guard let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}
```

### Sync to WebView Cookie

```swift
import WebKit

func syncTokenToWebView() {
    guard let token = TokenStore.shared.retrieve() else { return }
    
    let cookie = HTTPCookie(properties: [
        .name: "auth_token",
        .value: token,
        .domain: "your-app.com",
        .path: "/",
        .secure: true,
        .expires: Date().addingTimeInterval(86400 * 30)
    ])!
    
    WKWebsiteDataStore.default().httpCookieStore.setCookie(cookie)
}
```

### Call Before Navigation Starts

```swift
// SceneDelegate
func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
    syncTokenToWebView()
    navigator.start()
}
```

## Handle 401 Unauthorized

```swift
extension SceneDelegate: NavigatorDelegate {
    func visitableDidFailRequest(_ visitable: Visitable, error: Error) {
        if let httpError = error as? TurboError,
           case .http(let statusCode) = httpError,
           statusCode == 401 {
            showLoginScreen()
        }
    }
    
    private func showLoginScreen() {
        let loginURL = URL(string: "https://your-app.com/login")!
        navigator.route(loginURL, options: VisitOptions(action: .replace))
    }
}
```

## OAuth / SSO

Present auth in ASWebAuthenticationSession:

```swift
import AuthenticationServices

class AuthManager: NSObject, ASWebAuthenticationPresentationContextProviding {
    func authenticate(completion: @escaping (String?) -> Void) {
        let url = URL(string: "https://your-app.com/auth/google")!
        let session = ASWebAuthenticationSession(
            url: url,
            callbackURLScheme: "yourapp"
        ) { callbackURL, error in
            guard let url = callbackURL,
                  let token = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                    .queryItems?.first(where: { $0.name == "token" })?.value
            else {
                completion(nil)
                return
            }
            TokenStore.shared.save(token: token)
            completion(token)
        }
        session.presentationContextProvider = self
        session.prefersEphemeralWebBrowserSession = true
        session.start()
    }
    
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.windows.first!
    }
}
```

## Clear Session on Logout

```swift
func logout() {
    // Clear Keychain
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: "authToken"
    ]
    SecItemDelete(query as CFDictionary)
    
    // Clear WebView data
    let dataStore = WKWebsiteDataStore.default()
    dataStore.fetchDataRecords(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes()) { records in
        records.forEach { dataStore.removeData(ofTypes: $0.dataTypes, for: [$0]) { } }
    }
    
    // Navigate to login
    navigator.route(loginURL, options: VisitOptions(action: .replace))
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
