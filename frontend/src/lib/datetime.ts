export const DATE_LOCALE = 'cs-CZ';
export const DATE_TIMEZONE = 'Europe/Prague';

export function safeDate(value?: string | null): Date | null {
  if (!value) return null;
  const ts = new Date(value);
  return Number.isNaN(ts.getTime()) ? null : ts;
}
