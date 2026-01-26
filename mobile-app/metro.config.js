const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// .riv 파일을 asset으로 인식하도록 추가
config.resolver.assetExts.push('riv');

module.exports = config;
