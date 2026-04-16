---
paths:
  - "android/**/*"
---

## Android App (Hotwire Native)

The `android/` directory contains the native Android shell built with Kotlin and Hotwire Native (v1.2.5). It mirrors the iOS app's functionality.

### Stack
- **AGP:** 8.13.2, **Kotlin:** 2.3.0, **Gradle:** 8.13
- **compileSdk / targetSdk:** 36, **minSdk:** 28
- **Hotwire Native:** `dev.hotwire:core:1.2.5` + `dev.hotwire:navigation-fragments:1.2.5`
- **JDK:** 21 (bundled with Android Studio)

### Key files
- `android/app/src/main/java/com/example/lifemuse/MainActivity.kt` — Activity entry point, auth state management, bottom navigation
- `android/app/src/main/java/com/example/lifemuse/LifeMuseApplication.kt` — Application subclass; loads path config, registers bridge components
- `android/app/src/main/java/com/example/lifemuse/AuthenticationComponent.kt` — Bridge component for sign-in/sign-out events
- `android/app/src/main/java/com/example/lifemuse/Tabs.kt` — Tab definitions (sign-in + authenticated tabs)
- `android/app/src/main/res/layout/activity_main.xml` — Layout with navigator hosts and bottom navigation
- `android/app/src/main/assets/json/path-configuration.json` — Local Hotwire path routing rules (bundled with app)
- `/configurations/android_v1.json` — Remote Hotwire path configuration (served by Rails)

### Commands
```bash
# Build (requires Android Studio's bundled JDK)
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
cd android && ./gradlew assembleDebug

# Run tests
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
cd android && ./gradlew test
```

### Notes
- Hotwire Native 1.2.5 requires Kotlin 2.3.0 — downgrading causes metadata version errors
- Kotlin 2.3.0 removed the `kotlinOptions` DSL; use `kotlin { compilerOptions { ... } }` instead
- AGP 8+ disables `BuildConfig` by default; `buildFeatures { buildConfig = true }` is enabled
- Android emulator uses `10.0.2.2` to reach host machine's `localhost`
