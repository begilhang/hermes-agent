import { atom } from 'nanostores'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { HermesConnection } from '@/global'

// Keep profile.ts's side-effecting imports inert: the gateway socket layer and
// the REST query client must not run for real in a unit test.
const ensureGatewayForProfile = vi.fn(async () => undefined)
const $gateway = atom<unknown>({ id: 'live-socket' })

vi.mock('@/store/gateway', () => ({ $gateway, ensureGatewayForProfile }))
vi.mock('@/hermes', () => ({
  getProfiles: vi.fn(async () => ({ profiles: [] })),
  setApiRequestProfile: vi.fn()
}))
vi.mock('@/lib/query-client', () => ({ queryClient: { invalidateQueries: vi.fn() } }))

const { $activeGatewayProfile, ensureGatewayProfile, newSessionInProfile, selectProfile } = await import('./profile')
const {
  $connection,
  $currentFastMode,
  $currentModel,
  $currentModelProfile,
  $currentProvider,
  setCurrentFastMode,
  setCurrentModel,
  setCurrentModelProfile,
  setCurrentProvider
} = await import('./session')

const remoteConn = (over: Partial<HermesConnection> = {}): HermesConnection =>
  ({ baseUrl: 'https://hermes-roy.tail.ts.net', mode: 'remote', profile: 'vps-remote', ...over }) as HermesConnection

const localConn = (over: Partial<HermesConnection> = {}): HermesConnection =>
  ({ baseUrl: '', mode: 'local', profile: 'default', ...over }) as HermesConnection

const getConnection = vi.fn<(profile?: string | null) => Promise<HermesConnection>>()

beforeEach(() => {
  getConnection.mockReset()
  ensureGatewayForProfile.mockClear()
  $gateway.set({ id: 'live-socket' })
  $activeGatewayProfile.set('default')
  $connection.set(localConn())
  setCurrentModel('')
  setCurrentModelProfile('')
  setCurrentProvider('')
  setCurrentFastMode(false)
  vi.stubGlobal('window', { hermesDesktop: { getConnection } })
})

afterEach(() => {
  vi.unstubAllGlobals()
  $connection.set(null)
  setCurrentModel('')
  setCurrentModelProfile('')
  setCurrentProvider('')
  setCurrentFastMode(false)
})

describe('ensureGatewayProfile → $connection sync (#46651)', () => {
  it('refreshes $connection to the remote descriptor when activating a remote pool profile', async () => {
    // Regression: the primary window backend is local, so $connection.mode is
    // "local". Activating the remote profile must flip it to "remote" — without
    // this, image attach uses path-based image.attach against the remote
    // gateway ("image not found: C:\\…") instead of image.attach_bytes.
    getConnection.mockResolvedValue(remoteConn())

    await ensureGatewayProfile('vps-remote')

    expect(ensureGatewayForProfile).toHaveBeenCalledWith('vps-remote')
    expect(getConnection).toHaveBeenCalledWith('vps-remote')
    expect($connection.get()?.mode).toBe('remote')
    expect($connection.get()?.profile).toBe('vps-remote')
  })

  it('resyncs $connection back to local when returning to the default profile', async () => {
    $activeGatewayProfile.set('vps-remote')
    $connection.set(remoteConn())
    getConnection.mockResolvedValue(localConn())

    await ensureGatewayProfile('default')

    expect(getConnection).toHaveBeenCalledWith('default')
    expect($connection.get()?.mode).toBe('local')
  })

  it('leaves the prior connection intact when the descriptor fetch fails', async () => {
    getConnection.mockRejectedValue(new Error('backend unreachable'))

    await ensureGatewayProfile('vps-remote')

    // Best-effort: boot/reconnect resyncs later; we must not null it out here.
    expect($connection.get()?.mode).toBe('local')
  })

  it('does not churn $connection when the target is already the active profile', async () => {
    $activeGatewayProfile.set('vps-remote')
    $connection.set(remoteConn())

    await ensureGatewayProfile('vps-remote')

    expect(getConnection).not.toHaveBeenCalled()
    expect(ensureGatewayForProfile).not.toHaveBeenCalled()
    expect($connection.get()?.mode).toBe('remote')
  })
})

describe('profile switches clear profile-owned composer runtime selection', () => {
  function seedEmergencyModel() {
    setCurrentModel('Qwopus3.6-35B-A3B-v1-6bit-MTPLX-Optimized-Speed')
    setCurrentProvider('custom:omlx-local')
    setCurrentModelProfile('emergency_local_ceo_router')
    setCurrentFastMode(true)
  }

  it('clears a stale model immediately when selecting another profile', () => {
    seedEmergencyModel()

    selectProfile('0-ceo-orchesteator')

    expect($currentModel.get()).toBe('')
    expect($currentProvider.get()).toBe('')
    expect($currentModelProfile.get()).toBe('')
    expect($currentFastMode.get()).toBe(false)
  })

  it('clears a stale model immediately when creating a new session in another profile', () => {
    seedEmergencyModel()

    newSessionInProfile('0-ceo-orchesteator')

    expect($currentModel.get()).toBe('')
    expect($currentProvider.get()).toBe('')
    expect($currentModelProfile.get()).toBe('')
    expect($currentFastMode.get()).toBe(false)
  })
})
