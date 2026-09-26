// Add optional native HTTPS to the pinned upstream HTTP server.
const fs = require('node:fs');
const path = '/app/lib/Server.js';
let source = fs.readFileSync(path, 'utf8');
function replaceOnce(before, after) {
  if (source.split(before).length !== 2) {
    throw new Error('Upstream TLS integration point changed; review the patch');
  }
  source = source.replace(before, () => after);
}
replaceOnce("const { createServer } = require('node:http');", `
const tlsEnabled = process.env.TLS_ENABLED === 'true';
const createServer = tlsEnabled
  ? (listener) => require('node:https').createServer({
    key: require('node:fs').readFileSync('/etc/amneziawg-tls/key.pem'),
    cert: require('node:fs').readFileSync('/etc/amneziawg-tls/cert.pem'),
    minVersion: 'TLSv1.2',
  }, listener)
  : require('node:http').createServer;
`);
replaceOnce('saveUninitialized: true,',
  "saveUninitialized: true,\n      cookie: { secure: tlsEnabled, httpOnly: true, sameSite: 'lax' },");
replaceOnce('Listening on http://', "Listening on ${tlsEnabled ? 'https' : 'http'}://");
fs.writeFileSync(path, source);
