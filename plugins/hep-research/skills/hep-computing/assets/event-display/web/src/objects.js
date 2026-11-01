// Fetch a bundle object and check its sha256 before use. Objects are content-addressed
// (objects/<sha256>.<ext>), so the same digest is fetched and parsed once and shared read-only.
const cache = new Map();

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function fetchObject(path, sha256, kind = 'json') {
  if (!/^objects\/[0-9a-f]{64}\.[a-z]+$/.test(path)) {
    return Promise.reject(new Error(`not a bundle object path: ${path}`));
  }
  if (!cache.has(sha256)) {
    cache.set(sha256, (async () => {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
      const buffer = await response.arrayBuffer();
      const actual = await sha256Hex(buffer);
      if (actual !== sha256) throw new Error(`${path}: digest mismatch (integrity failure)`);
      const text = new TextDecoder().decode(buffer);
      return kind === 'json' ? JSON.parse(text) : text;
    })());
    cache.get(sha256).catch(() => cache.delete(sha256)); // a failed fetch may be retried
  }
  return cache.get(sha256);
}
