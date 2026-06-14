/**
 * Format a number of minutes since midnight into "HH:MM" string.
 * @param {number} minutes - Minutes since midnight (0–1439).
 * @returns {string} Formatted time string, e.g. "07:30".
 */
export function formatTime(minutes) {
  const h = Math.floor(minutes / 60) % 24;
  const m = Math.floor(minutes % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Linear interpolation between two values.
 * @param {number} a - Start value.
 * @param {number} b - End value.
 * @param {number} t - Interpolation factor (0 to 1).
 * @returns {number} Interpolated value.
 */
export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Clamp a value between a minimum and maximum.
 * @param {number} value - Value to clamp.
 * @param {number} min - Minimum bound.
 * @param {number} max - Maximum bound.
 * @returns {number} Clamped value.
 */
export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

/**
 * Convert a "HH:MM" time string to total minutes since midnight.
 * @param {string} timeString - Time in "HH:MM" format.
 * @returns {number} Minutes since midnight.
 */
export function timeToMinutes(timeString) {
  const [hours, minutes] = timeString.split(':').map(Number);
  return hours * 60 + minutes;
}
