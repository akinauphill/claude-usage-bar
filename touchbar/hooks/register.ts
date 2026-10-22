import type { EngineInterface, Register } from 'claude-code'

type Measured = {
  rateLimits: { kind: string; percentUsed: number; resetsAt?: string }[]
  context: { percent?: number }
  cost?: { usd: number }
}

const publish = async ($: EngineInterface, m: Measured, ended = false) => {
  const runtime = await $.env.get('XDG_RUNTIME_DIR')

  if (!runtime) return

  const snapshot = {
    v: 1,
    ended,
    updatedAt: await $.clock.now(),
    windows: m.rateLimits.map(w => ({ kind: w.kind, percentUsed: w.percentUsed, resetsAt: w.resetsAt })),
    contextPercent: m.context.percent ?? null,
    costUsd: m.cost?.usd ?? null,
  }

  await $.fs.write(`${runtime}/usage-bar/usage.json`, JSON.stringify(snapshot))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await publish($, await $.session.usage())

    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await publish($, e)

    return next(e)
  })

  on('session.end', async ($, e, next) => {
    await publish($, { rateLimits: [], context: {} }, true)

    return next(e)
  })
}
