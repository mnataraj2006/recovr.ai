/**
 * Formats an ISO date string as a locale time string (HH:MM:SS AM/PM).
 */
export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString();
}

/**
 * Formats an ISO date string into a readable date and time string.
 */
export function formatDate(isoString?: string): string {
  if (!isoString) return '-';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return isoString;
  return d.toLocaleString();
}

