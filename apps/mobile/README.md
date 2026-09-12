# PhaseGuard Mobile App

A React Native mobile application for real-time scam protection with AI voice deepfake detection, live call analysis, and India-first security.

## Features

✨ **AI Voice Deepfake Detection** - Spectral AI flags synthetic or cloned voices in real time
📊 **Real-Time Risk Score** - Continuous scoring updates as conversations unfold
🔍 **Live Fact Checking** - Cross-checks claims against verified public databases
🔐 **Forensic Evidence** - Secure, tamper-proof logs ready for authorities
📱 **Multi-Screen Interface** - Home, Calls, Reports, and Settings screens
🎨 **Beautiful UI** - Glass morphism design with smooth animations

## Tech Stack

- **Framework**: React Native 0.73
- **Expo**: 50.0 (for easier development and web support)
- **Navigation**: React Navigation 6
- **State Management**: Zustand
- **API Client**: Axios
- **UI Animations**: Reanimated 3, React Native Gesture Handler
- **Styling**: React Native StyleSheet with custom theme
- **TypeScript**: Full type safety

## Project Structure

```
apps/mobile/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Header.tsx
│   │   ├── Hero.tsx
│   │   ├── ProtectionCard.tsx
│   │   ├── FeatureGrid.tsx
│   │   ├── CallSimulation.tsx
│   │   ├── Timeline.tsx
│   │   ├── ActionButtons.tsx
│   │   ├── GlassCard.tsx
│   │   ├── PulseDot.tsx
│   │   ├── Waveform.tsx
│   │   ├── ShieldLogo.tsx
│   │   └── TabBarIcon.tsx
│   ├── screens/             # Screen components
│   │   ├── HomeScreen.tsx
│   │   ├── CallsScreen.tsx
│   │   ├── ReportsScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── services/            # API and external services
│   │   └── api.ts
│   ├── store/               # State management (Zustand)
│   │   └── appStore.ts
│   ├── constants/           # Theme colors and constants
│   │   └── Colors.ts
│   └── utils/               # Helper functions
│       └── helpers.ts
├── App.tsx                  # Main app entry point
├── app.json                 # Expo configuration
├── package.json             # Dependencies
├── tsconfig.json            # TypeScript config
├── babel.config.js          # Babel configuration
└── react-native.config.js   # React Native config
```

## Getting Started

### Prerequisites

- Node.js 16.x or higher
- npm or yarn
- Expo CLI: `npm install -g expo-cli`
- For iOS: Xcode and CocoaPods
- For Android: Android Studio and SDK

### Installation

1. **Navigate to the mobile app directory**:
```bash
cd apps/mobile
```

2. **Install dependencies**:
```bash
npm install
# or
yarn install
```

3. **Create environment file**:
```bash
cp .env.example .env
```

4. **Configure API endpoint** (edit `.env`):
```
REACT_APP_API_URL=http://your-backend-url/api
```

### Running the App

**Development Server**:
```bash
npm start
# or
expo start
```

This will start the Expo development server. You can then:
- Press `i` for iOS simulator
- Press `a` for Android emulator
- Press `w` for web browser
- Scan QR code with Expo app on physical device

**Android**:
```bash
npm run android
# or
expo run:android
```

**iOS**:
```bash
npm run ios
# or
expo run:ios
```

**Web**:
```bash
npm run web
# or
expo start --web
```

## API Integration

The app integrates with the PhaseGuard backend API. All API calls are handled through the `PhaseGuardAPI` service class in `src/services/api.ts`.

### Available API Methods

- `analyzeCall(metadata)` - Analyze incoming call for deepfakes
- `blockAndReport(report)` - Block number and submit report
- `getCallHistory(limit)` - Fetch call history
- `getReports(limit)` - Fetch submitted reports
- `getProtectionStatus()` - Get current protection status
- `continueMonitoring(callId)` - Monitor specific call
- `getFactCheckResults(claim)` - Verify claims

### State Management

Use the Zustand store for global state:

```typescript
import { useAppStore } from '@store/appStore';

const MyComponent = () => {
  const { currentCall, analyzeCall } = useAppStore();
  
  // Use store data and actions
};
```

## Styling & Theme

All colors and styles are defined in `src/constants/Colors.ts`:

```typescript
export const Colors = {
  bgPrimary: '#021024',
  bgSecondary: '#052659',
  accentBlue: '#5483B3',
  mediumBlue: '#7DA0CA',
  lightBlue: '#C1E8FF',
  safe: '#5EE1C4',
  warn: '#F4C95D',
  crit: '#FF5D6C',
  // ... more colors
};
```

## Building for Production

### Android

```bash
eas build --platform android
```

### iOS

```bash
eas build --platform ios
```

For more details, see [Expo EAS Build documentation](https://docs.expo.dev/build/introduction/).

## Performance Optimization

- ✅ Lazy loading screens with React Navigation
- ✅ Optimized animations with Reanimated
- ✅ Memoized components to prevent unnecessary re-renders
- ✅ Efficient state management with Zustand
- ✅ Image optimization and caching

## Accessibility

- ✅ Proper color contrast ratios
- ✅ Touch target sizes (minimum 44x44)
- ✅ Semantic HTML structure
- ✅ Screen reader support (labels, descriptions)
- ✅ Keyboard navigation support

## Testing

To add tests, install testing libraries:

```bash
npm install --save-dev @testing-library/react-native jest
```

Run tests:

```bash
npm test
```

## Troubleshooting

### Common Issues

**Port 8081 already in use**:
```bash
expo start --clear
```

**Module not found errors**:
```bash
npm install
# Clear cache
npm start -- --reset-cache
```

**API connection issues**:
- Check `.env` file has correct `REACT_APP_API_URL`
- Ensure backend server is running
- Check network connectivity

**Metro bundler issues**:
```bash
npm start -- --reset-cache --clear
```

## Contributing

1. Follow existing code style and patterns
2. Use TypeScript for type safety
3. Test components before committing
4. Keep components focused and reusable
5. Document complex logic with comments

## License

Proprietary - PhaseGuard 2026

## Support

For issues or feature requests, contact the development team.
