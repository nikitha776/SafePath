import type { ConfigContext, ExpoConfig } from 'expo/config';
export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'SafePath',
  slug: 'safepath-mobile',
  plugins: [...(config.plugins || []), ['expo-build-properties', {
    android: { usesCleartextTraffic: process.env.SAFEPATH_DEV_HTTP === '1' },
  }]],
});
