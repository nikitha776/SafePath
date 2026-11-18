const { getDefaultConfig } = require('expo/metro-config');
const path = require('node:path');
const config = getDefaultConfig(__dirname);
// Share the public city configuration without importing web components.
config.watchFolders = [path.resolve(__dirname, '../frontend/src/config')];
module.exports = config;
