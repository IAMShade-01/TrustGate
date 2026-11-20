const feed = process.env.TRUSTGATE_UPDATE_FEED;
const publisher = process.env.TRUSTGATE_UPDATE_PUBLISHER;
if ((feed || publisher) && (!feed || !publisher?.trim() || new URL(feed).protocol !== 'https:'))
  throw new Error('Automatic updates require an HTTPS feed and an Authenticode publisher.');

module.exports = {
  appId: 'com.trustgate.enterprise',
  productName: 'TrustGate Enterprise',
  files: ['main.cjs', 'preload.cjs', 'winget.cjs', 'ui/**/*', 'icons/**/*'],
  directories: { output: 'dist' },
  forceCodeSigning: Boolean(feed),
  win: {
    icon: 'icons/trustgate.ico',
    target: ['nsis', 'zip'],
    verifyUpdateCodeSignature: true,
    ...(feed ? { publisherName: publisher } : {}),
  },
  ...(feed ? { publish: [{ provider: 'generic', url: feed }] } : {}),
};
