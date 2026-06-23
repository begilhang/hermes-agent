import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { deleteSession, getSessionMessages, listAllProfileSessions, listSessions, renameSession, setSessionArchived } from './hermes'

const emptySessionsResponse = {
  limit: 0,
  offset: 0,
  sessions: [],
  total: 0
}

describe('Hermes REST session helpers', () => {
  let api: ReturnType<typeof vi.fn>

  beforeEach(() => {
    api = vi.fn().mockResolvedValue(emptySessionsResponse)
    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true,
      value: { api }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    Reflect.deleteProperty(window, 'hermesDesktop')
  })

  it('uses a longer timeout for the single-profile session list', async () => {
    await listSessions(50, 1)

    expect(api).toHaveBeenCalledWith(
      expect.objectContaining({
        path: '/api/sessions?limit=50&offset=0&min_messages=1&archived=exclude&order=recent',
        timeoutMs: 60_000
      })
    )
  })

  it('uses a longer timeout for the all-profile session list', async () => {
    await listAllProfileSessions(50, 1)

    expect(api).toHaveBeenCalledWith(
      expect.objectContaining({
        path: '/api/profiles/sessions?limit=50&offset=0&min_messages=1&archived=exclude&order=recent&profile=all',
        timeoutMs: 60_000
      })
    )
  })

  it('tags cross-profile message reads for Electron routing and backend lookup', async () => {
    api.mockResolvedValue({ messages: [], session_id: 'session-1' })

    await getSessionMessages('session-1', 'xiaoxuxu')

    expect(api).toHaveBeenCalledWith({
      path: '/api/sessions/session-1/messages?profile=xiaoxuxu',
      profile: 'xiaoxuxu'
    })
  })

  it('retries session rename against the resolved owning profile after a stale unprofiled row 404s', async () => {
    api
      .mockRejectedValueOnce(new Error('Session not found'))
      .mockResolvedValueOnce({
        ...emptySessionsResponse,
        sessions: [{ id: 'session-1', profile: '0-ceo-orchesteator' }]
      })
      .mockResolvedValueOnce({ ok: true, title: 'Renamed' })

    await expect(renameSession('session-1', 'Renamed')).resolves.toEqual({ ok: true, title: 'Renamed' })

    expect(api).toHaveBeenNthCalledWith(1, {
      path: '/api/sessions/session-1',
      method: 'PATCH',
      body: { title: 'Renamed' }
    })
    expect(api).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        path: '/api/profiles/sessions?limit=500&offset=0&min_messages=0&archived=include&order=recent&profile=all'
      })
    )
    expect(api).toHaveBeenNthCalledWith(3, {
      profile: '0-ceo-orchesteator',
      path: '/api/sessions/session-1',
      method: 'PATCH',
      body: { title: 'Renamed', profile: '0-ceo-orchesteator' }
    })
  })

  it('uses the same owning-profile fallback for archive and delete mutations', async () => {
    api
      .mockRejectedValueOnce(new Error('Session not found'))
      .mockResolvedValueOnce({
        ...emptySessionsResponse,
        sessions: [{ id: 'session-1', profile: 'coding35b_longtask' }]
      })
      .mockResolvedValueOnce({ ok: true })
      .mockRejectedValueOnce(new Error('Session not found'))
      .mockResolvedValueOnce({
        ...emptySessionsResponse,
        sessions: [{ id: 'session-1', profile: 'coding35b_longtask' }]
      })
      .mockResolvedValueOnce({ ok: true })

    await expect(setSessionArchived('session-1', true)).resolves.toEqual({ ok: true })
    await expect(deleteSession('session-1')).resolves.toEqual({ ok: true })

    expect(api).toHaveBeenNthCalledWith(3, {
      profile: 'coding35b_longtask',
      path: '/api/sessions/session-1',
      method: 'PATCH',
      body: { archived: true, profile: 'coding35b_longtask' }
    })
    expect(api).toHaveBeenNthCalledWith(6, {
      profile: 'coding35b_longtask',
      path: '/api/sessions/session-1',
      method: 'DELETE'
    })
  })
})
