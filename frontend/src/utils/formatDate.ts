/**
 * Formats an ISO date string as a locale time string (HH:MM:SS AM/PM).
 */
export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString();
}
