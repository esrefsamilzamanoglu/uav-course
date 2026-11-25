export function number(value: number | null | undefined, digits = 1): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—'
}
export function duration(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds)) return '—:—'
  const s = Math.max(0, Math.floor(seconds))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
export function eventTime(value: number | string | undefined) {
  if (value == null) return '—'
  if (typeof value === 'string' && /^\d\d:\d\d/.test(value)) return value
  const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString('tr-TR', { hour12: false })
}
