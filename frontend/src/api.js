let cachedToken = null;

export async function getAuthToken() {
  if (cachedToken) return cachedToken;
  try {
    const res = await fetch('/api/bootstrap');
    if (res.ok) {
      const data = await res.json();
      cachedToken = data.token;
      return cachedToken;
    }
  } catch (e) {
    console.error('Failed to bootstrap auth token:', e);
  }
  return null;
}

export async function apiFetch(url, options = {}) {
  const token = await getAuthToken();
  const headers = new Headers(options.headers || {});
  if (token && !headers.has('X-LENS-Token')) {
    headers.set('X-LENS-Token', token);
  }
  return fetch(url, {
    ...options,
    headers,
    credentials: 'same-origin'
  });
}
