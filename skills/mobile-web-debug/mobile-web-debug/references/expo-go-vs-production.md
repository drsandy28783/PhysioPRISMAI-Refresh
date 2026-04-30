# Expo Go vs EAS Production Build — Complete Differences

This is the definitive reference for why something works in Expo Go but breaks in a production build.

---

## 1. Environment Variables

| Expo Go | Production Build |
|---|---|
| Reads `.env` at runtime via Metro | Only includes vars baked in at build time via `eas.json` |
| `process.env.MY_VAR` may work | Must use `EXPO_PUBLIC_` prefix or `app.config.js` |
| Can change vars without rebuild | Requires new EAS build for every env change |

**Fix:**
```js
// app.config.js (preferred — dynamic)
export default ({ config }) => ({
  ...config,
  extra: {
    apiUrl: process.env.API_URL ?? 'https://physiologicprism.azurecontainerapps.io',
  },
});

// Access in app:
import Constants from 'expo-constants';
const API_URL = Constants.expoConfig.extra.apiUrl;
```

Or simpler with `EXPO_PUBLIC_` prefix (Expo SDK 49+):
```js
// .env.production (committed to EAS, NOT git)
EXPO_PUBLIC_API_URL=https://physiologicprism.azurecontainerapps.io

// Usage in code (auto-available, no import needed):
const API_URL = process.env.EXPO_PUBLIC_API_URL;
```

---

## 2. Native Modules

| Expo Go | Production Build |
|---|---|
| Pre-bundles 100+ native modules | Only includes modules declared in `app.json` plugins |
| Can use expo-camera without config | Must add `"expo-camera"` to plugins array |
| Crashes silently or works unexpectedly | NativeModule null error or crash on launch |

**Check every `import` from an Expo package and ensure it's in `app.json`:**
```json
{
  "expo": {
    "plugins": [
      "expo-camera",
      "expo-file-system",
      "expo-document-picker",
      "expo-print",
      "expo-sharing",
      "expo-secure-store",
      "@react-native-async-storage/async-storage"
    ]
  }
}
```

---

## 3. Firebase Auth Persistence

| Expo Go | Production Build |
|---|---|
| May use memory persistence and still "work" | Requires AsyncStorage persistence or tokens are lost |
| Session survives Metro hot reload | Session lost on app restart without proper persistence |

**Fix — always use AsyncStorage persistence in React Native:**
```js
import { initializeAuth, getReactNativePersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

const auth = initializeAuth(firebaseApp, {
  persistence: getReactNativePersistence(AsyncStorage)
});
```

---

## 4. Network Requests

| Expo Go | Production Build |
|---|---|
| Runs on your dev machine's network | Runs on device's actual network |
| `http://localhost:5000` resolves to dev machine | `localhost` = the phone itself (nothing there) |
| `http://192.168.x.x:5000` works on same WiFi | Fails on mobile data or different network |
| HTTP requests generally allowed | Android blocks HTTP (cleartext) by default |

**Fix:**
```js
// Always use the Azure production URL in production builds
const API_URL = process.env.EXPO_PUBLIC_API_URL 
  ?? 'https://physiologicprism.azurecontainerapps.io';
```

For dev, point to your local Azure Container Apps dev URL or use ngrok:
```bash
# Tunnel local Flask to HTTPS for mobile testing
ngrok http 5000
# Then set EXPO_PUBLIC_API_URL=https://{ngrok-id}.ngrok.io in .env.development
```

---

## 5. SSL / TLS

| Expo Go | Production Build |
|---|---|
| Self-signed certs often accepted | Only valid HTTPS certs accepted |
| HTTP allowed | HTTP blocked on Android (cleartext policy) |

**Azure Container Apps provides valid TLS by default — always use the `*.azurecontainerapps.io` URL.**

---

## 6. Permissions

| Expo Go | Production Build |
|---|---|
| Many permissions auto-granted | Must be declared in `app.json` |
| Camera works without config | Requires `expo-camera` plugin + `NSCameraUsageDescription` |
| File access works | Requires `READ_EXTERNAL_STORAGE` on Android |

**Required permissions for PRISM mobile (add to `app.json`):**
```json
{
  "expo": {
    "android": {
      "permissions": [
        "INTERNET",
        "READ_EXTERNAL_STORAGE",
        "WRITE_EXTERNAL_STORAGE"
      ]
    },
    "ios": {
      "infoPlist": {
        "NSCameraUsageDescription": "Used to scan documents",
        "NSPhotoLibraryUsageDescription": "Used to attach patient photos"
      }
    }
  }
}
```

---

## 7. Metro Bundler vs Hermes Engine

| Expo Go | Production Build |
|---|---|
| Uses Metro bundler in dev mode | Uses Hermes JS engine (Android default) |
| Full JS debugging available | Hermes has stricter parsing |
| Some ES features polyfilled by Metro | May fail on certain syntax in Hermes |

**Hermes incompatibility symptoms:** app crashes immediately after splash screen with no error shown.

**Fix:** Enable Hermes in local dev to catch issues early:
```json
// app.json
{
  "expo": {
    "android": {
      "jsEngine": "hermes"
    }
  }
}
```

---

## 8. Deep Links / URI Scheme

| Expo Go | Production Build |
|---|---|
| Uses `exp://` scheme | Must use your declared `scheme` in `app.json` |
| OAuth redirects go to Expo Go | OAuth redirects must go to your app's scheme |

**If Firebase Auth Google/phone sign-in is used:**
```json
{
  "expo": {
    "scheme": "physiologicprism",
    "android": {
      "intentFilters": [
        {
          "action": "VIEW",
          "data": [{ "scheme": "physiologicprism" }],
          "category": ["BROWSABLE", "DEFAULT"]
        }
      ]
    }
  }
}
```

---

## 9. SecureStore vs AsyncStorage

| Use case | Storage to use |
|---|---|
| Sensitive tokens (Firebase token, API key) | `expo-secure-store` (encrypted) |
| Non-sensitive app state, user preferences | `@react-native-async-storage/async-storage` |
| Large data (patient records cache) | `expo-sqlite` or `expo-file-system` |

**Never store Firebase token or API keys in AsyncStorage in production.**

---

## 10. Build Profile Mistakes

Common `eas.json` mistakes:

```json
// WRONG — same env for all profiles
{
  "build": {
    "production": {},
    "preview": {},
    "development": {}
  }
}

// CORRECT — explicit env per profile
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "env": {
        "EXPO_PUBLIC_API_URL": "http://192.168.1.10:5000"
      }
    },
    "preview": {
      "distribution": "internal",
      "env": {
        "EXPO_PUBLIC_API_URL": "https://physiologicprism-staging.azurecontainerapps.io"
      }
    },
    "production": {
      "env": {
        "EXPO_PUBLIC_API_URL": "https://physiologicprism.azurecontainerapps.io",
        "EXPO_PUBLIC_FIREBASE_PROJECT_ID": "physiologicprism"
      }
    }
  }
}
```
