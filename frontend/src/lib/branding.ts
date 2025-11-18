const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? '';

export function resolveBrandingAssetUrl(url?: string | null): string | null {
  if (!url) {
    return null;
  }
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  if (!url.startsWith('/')) {
    return url;
  }
  // Assets served by API live under /static; prepend API base in that case.
  if (url.startsWith('/static/')) {
    if (!API_BASE) {
      return url;
    }
    return `${API_BASE}${url}`;
  }
  // Relative assets (e.g., /logo-default.svg) live in Next.js public/ directory.
  return url;
}
