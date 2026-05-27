/// SCAFFOLD — actual Android build requires:
//   npm i -D @capacitor/cli @capacitor/core @capacitor/android
//   VITE_BUILD_TARGET=capacitor npm run build
//   npx cap add android
//   npx cap sync android
//   npx cap open android   # opens Android Studio
//
// iOS is intentionally NOT scaffolded — out of scope for this milestone.

import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'ai.echolens.android',
  appName: 'EchoLens',
  webDir: 'dist',
  bundledWebRuntime: false,
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
  server: {
    androidScheme: 'https',
    cleartext: true,
  },
}

export default config
