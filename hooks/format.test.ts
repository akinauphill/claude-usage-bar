import { describe, expect, test } from 'claude-code/testing'

import { bar, costText, labelFor, levelColor, percentText, untilReset } from './format'

describe('format', () => {
  test('bar fills proportionally and clamps', () => {
    expect(bar(0)).toBe('░░░░░░░░░░')
    expect(bar(50)).toBe('█████░░░░░')
    expect(bar(250)).toBe('██████████')
  })

  test('levelColor steps at 60 and 85', () => {
    expect(levelColor(59)).toBe('success')
    expect(levelColor(60)).toBe('warning')
    expect(levelColor(85)).toBe('error')
  })

  test('untilReset reads minutes, hours and days', () => {
    const now = Date.parse('2026-01-01T00:00:00Z')
    expect(untilReset('2026-01-01T00:20:00Z', now)).toBe('20m')
    expect(untilReset('2026-01-01T02:05:00Z', now)).toBe('2h05m')
    expect(untilReset('2026-01-03T05:00:00Z', now)).toBe('2d5h')
    expect(untilReset('2025-12-31T00:00:00Z', now)).toBe('')
    expect(untilReset(undefined, now)).toBe('')
  })

  test('labels and numbers', () => {
    expect(labelFor('five_hour')).toBe('5h')
    expect(labelFor('some_new_window')).toBe('some new window')
    expect(percentText(23.5)).toBe('23.5%')
    expect(percentText(7)).toBe('7%')
    expect(costText(1.234)).toBe('$1.23')
  })
})
