// The pinned panel mixes Express response helpers with a native Node response.
// Keep authentication failures at HTTP 401 instead of throwing a TypeError/500.
const fs = require('node:fs');
const path = '/app/lib/Server.js';
const original = fs.readFileSync(path, 'utf8');
const pattern = /return res\.status\(401\)\.json\(\{\s+error: '([^']+)',\s+\}\);/g;
if ([...original.matchAll(pattern)].length !== 2) {
  throw new Error('Upstream authentication code changed; review this compatibility patch');
}
const fixed = original.replace(pattern, (_, message) =>
  `res.writeHead(401, { 'Content-Type': 'application/json' });\n`
  + `return res.end(JSON.stringify({ error: '${message}' }));`)
  .replaceAll('status: 401,', 'statusCode: 401,');
fs.writeFileSync(path, fixed);
