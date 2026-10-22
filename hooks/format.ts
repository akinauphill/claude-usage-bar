export const WINDOW_LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: '7d',
  spend_limit: 'spend',
}

export const labelFor = (kind: string): string =>
  WINDOW_LABELS[kind] ?? kind.replace(/_/g, ' ')

export const bar = (percent: number, cells = 10): string => {
  const filled = Math.max(0, Math.min(cells, Math.round((percent / 100) * cells)))

  return '█'.repeat(filled) + '░'.repeat(cells - filled)
}

export const levelColor = (percent: number): 'success' | 'warning' | 'error' =>
  percent >= 85 ? 'error' : percent >= 60 ? 'warning' : 'success'

export const untilReset = (resetsAt: string | undefined, now: number): string => {
  if (!resetsAt) return ''

  const ms = Date.parse(resetsAt) - now
  if (Number.isNaN(ms) || ms <= 0) return ''

  const minutes = Math.round(ms / 60000)
  if (minutes < 60) return `${minutes}m`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h${String(minutes % 60).padStart(2, '0')}m`

  return `${Math.floor(hours / 24)}d${hours % 24}h`
}

export const percentText = (percent: number): string =>
  `${Number.isInteger(percent) ? percent : percent.toFixed(1)}%`

export const costText = (usd: number): string => `$${usd.toFixed(2)}`
