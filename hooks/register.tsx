import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { UsageSnapshot } from '../types'
import { bar, costText, labelFor, levelColor, percentText, untilReset } from './format'

const snapshotAtom = atom({ plugin: 'usage-bar', key: 'snapshot' } as const, null)

type Measured = {
  rateLimits: { kind: string; percentUsed: number; resetsAt?: string }[]
  context: { percent?: number }
  cost?: { usd: number }
}

const toSnapshot = (m: Measured): UsageSnapshot => ({
  windows: m.rateLimits.map(w => ({ kind: w.kind, percentUsed: w.percentUsed, resetsAt: w.resetsAt })),
  contextPercent: m.context.percent ?? null,
  costUsd: m.cost?.usd ?? null,
})

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await update($, snapshotAtom, () => null)

    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await update($, snapshotAtom, () => toSnapshot(e))

    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) {
      return next(e)
    }

    const snapshot = (await read($, snapshotAtom)) ?? toSnapshot(await $.session.usage())
    const hasAnything =
      snapshot.windows.length > 0 || snapshot.contextPercent !== null || snapshot.costUsd !== null

    if (!hasAnything) {
      return next(e)
    }

    const now = await $.clock.now()
    const { Box, Text } = $.ui.resolve(e)

    return (
      <Box>
        {snapshot.windows.map((w, i) => {
          const reset = untilReset(w.resetsAt, now)

          return (
            <Text key={w.kind}>
              {i > 0 ? <Text dimColor>{'  │  '}</Text> : null}
              <Text dimColor>{labelFor(w.kind)} </Text>
              <Text color={levelColor(w.percentUsed)}>{bar(w.percentUsed)}</Text>
              <Text> {percentText(w.percentUsed)}</Text>
              {reset ? <Text dimColor> ↻{reset}</Text> : null}
            </Text>
          )
        })}
        {snapshot.contextPercent !== null ? (
          <Text key="ctx">
            {snapshot.windows.length > 0 ? <Text dimColor>{'  │  '}</Text> : null}
            <Text dimColor>ctx </Text>
            <Text color={levelColor(snapshot.contextPercent)}>{percentText(snapshot.contextPercent)}</Text>
          </Text>
        ) : null}
        {snapshot.costUsd !== null ? (
          <Text key="cost" dimColor>
            {'  │  '}
            {costText(snapshot.costUsd)}
          </Text>
        ) : null}
      </Box>
    )
  })
}
