const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? '';

export function resolveBrandingAssetUrl(url?: string | null): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  if (!url.startsWith('/')) {
    return url;
  }
  if (!API_BASE) {
    return url;
  }
  return `${API_BASE}${url}`;
}
