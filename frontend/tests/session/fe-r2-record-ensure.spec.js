import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { useRecordStore } from '../../src/stores/record.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userA = { id: 101, nickname: 'User A' }
const userB = { id: 202, nickname: 'User B' }

function login(user) {
  useUserStore().loginSuccess(`token-${user.id}`, user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function respondError(options, error, statusCode = 409) {
  options.success({ statusCode, data: { success: false, error } })
}

function logoutResponse(options) {
  if (options.url.endsWith('/auth/logout')) {
    respond(options, {})
    return true
  }
  return false
}

function draftRecord(planId = 119, entries = []) {
  return { id: planId + 382, planId, status: 'draft', entries }
}

describe('FE-R2.2 JourneyRecord ensure', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('uses the real authenticated create-or-get POST and stores the ensured Record', async () => {
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (!options.url.endsWith('/plans/119/journey-record')) throw new Error(`Unexpected request: ${options.url}`)
      respond(options, { journeyRecord: draftRecord() })
    })

    const result = await record.ensureJourneyRecord(119)

    const requests = getRequestCalls().filter((request) => request.url.endsWith('/plans/119/journey-record'))
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('POST')
    expect(requests[0].header.Authorization).toBe('Bearer token-101')
    expect(result).toMatchObject({ planId: 119, status: 'draft' })
    expect(record.ensurePlanId).toBe(119)
    expect(record.ensureError).toBeNull()
    expect(record.ensureLoading).toBe(false)
    expect(record.ensuredRecord).toMatchObject({ planId: 119, status: 'draft' })
  })

  test('treats an already existing JourneyRecord as ensure success', async () => {
    login(userA)
    const record = useRecordStore()
    const existing = draftRecord(119, [{ id: 1, observation: 'already exists' }])
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respond(options, { journeyRecord: existing })
    })

    await expect(record.ensureJourneyRecord(119)).resolves.toMatchObject({ id: existing.id, planId: 119 })

    expect(record.ensuredRecord).toMatchObject({ id: existing.id, planId: 119 })
    expect(record.ensureError).toBeNull()
  })

  test('rejects missing or mismatched JourneyRecord responses without saving them', async () => {
    login(userA)
    const record = useRecordStore()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      respond(options, {
        journeyRecord: requestCount === 1 ? null : draftRecord(999),
      })
    })

    await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    expect(record.ensuredRecord).toBeNull()
    expect(record.ensureError).toMatchObject({ code: 'INVALID_RESPONSE' })
    await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })

    expect(record.ensuredRecord).toBeNull()
    expect(record.ensureError).toMatchObject({ code: 'INVALID_RESPONSE' })
  })

  test('dedupes concurrent ensure calls for the same Plan and session', async () => {
    const completion = createDeferred()
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      completion.promise.then((data) => respond(options, data))
    })

    const first = record.ensureJourneyRecord(119)
    const second = record.ensureJourneyRecord(119)
    await flushRuntimePromises()

    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/119/journey-record'))).toHaveLength(1)
    completion.resolve({ journeyRecord: draftRecord() })
    await expect(Promise.all([first, second])).resolves.toEqual([
      expect.objectContaining({ planId: 119, status: 'draft' }),
      expect.objectContaining({ planId: 119, status: 'draft' }),
    ])
  })

  test('keeps a network failure visible for the ensured Plan', async () => {
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      options.fail({ errMsg: 'network down' })
    })

    await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(record.ensureError).toMatchObject({ code: 'NETWORK_ERROR' })
    expect(record.ensureLoading).toBe(false)
    expect(record.ensurePlanId).toBe(119)
  })

  test('retries the last ensured Plan after a failure', async () => {
    login(userA)
    const record = useRecordStore()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      if (requestCount === 1) {
        options.fail({ errMsg: 'network down' })
        return
      }
      respond(options, { journeyRecord: draftRecord() })
    })

    await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    const recovered = await record.retryJourneyRecordEnsure()

    expect(requestCount).toBe(2)
    expect(recovered).toMatchObject({ planId: 119, status: 'draft' })
    expect(record.ensureError).toBeNull()
    expect(record.ensureLoading).toBe(false)
    expect(record.ensuredRecord).toMatchObject({ planId: 119 })
  })

  test('does not request an invalid Plan or retry when no Plan is available', async () => {
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respond(options, { journeyRecord: draftRecord() })
    })

    await expect(record.ensureJourneyRecord(0)).resolves.toBeNull()
    await expect(record.retryJourneyRecordEnsure()).resolves.toBeNull()

    expect(getRequestCalls()).toEqual([])
  })

  test('does not let a late User A ensure success overwrite User B recovery state', async () => {
    const ensureA = createDeferred()
    const ensureB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? ensureA : ensureB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const record = useRecordStore()
    const pendingA = record.ensureJourneyRecord(119)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    const pendingB = record.ensureJourneyRecord(220)
    await flushRuntimePromises()

    ensureB.resolve({ journeyRecord: draftRecord(220) })
    await pendingB
    ensureA.resolve({ journeyRecord: draftRecord(119) })
    await pendingA

    expect(record.ensurePlanId).toBe(220)
    expect(record.ensuredRecord).toMatchObject({ planId: 220 })
    expect(record.ensureError).toBeNull()
  })

  test('does not let a late User A ensure failure write into User B recovery state', async () => {
    const ensureA = createDeferred()
    const ensureB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? ensureA : ensureB
      pending.promise.then((data) => respond(options, data), (error) => options.fail(error))
    })

    login(userA)
    const record = useRecordStore()
    const pendingA = record.ensureJourneyRecord(119)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    const pendingB = record.ensureJourneyRecord(220)
    await flushRuntimePromises()

    ensureA.reject({ errMsg: 'late User A failure' })
    await expect(pendingA).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(record.ensureLoading).toBe(true)
    expect(record.ensureError).toBeNull()
    ensureB.resolve({ journeyRecord: draftRecord(220) })
    await pendingB
  })

  test('does not let a late User A ensure finally clear User B loading', async () => {
    const ensureA = createDeferred()
    const ensureB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? ensureA : ensureB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const record = useRecordStore()
    const pendingA = record.ensureJourneyRecord(119)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    const pendingB = record.ensureJourneyRecord(220)
    await flushRuntimePromises()

    ensureA.resolve({ journeyRecord: draftRecord(119) })
    await pendingA

    expect(record.ensureLoading).toBe(true)
    ensureB.resolve({ journeyRecord: draftRecord(220) })
    await pendingB
    expect(record.ensureLoading).toBe(false)
  })

  test('keeps the Record Store reset when a delayed ensure response arrives after logout', async () => {
    const ensure = createDeferred()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      ensure.promise.then((data) => respond(options, data))
    })

    login(userA)
    const record = useRecordStore()
    const pending = record.ensureJourneyRecord(119)
    await flushRuntimePromises()
    await endUserSession()
    ensure.resolve({ journeyRecord: draftRecord() })
    await pending

    expect(useUserStore().isLoggedIn).toBe(false)
    expect(record.records).toEqual([])
    expect(record.ensureLoading).toBe(false)
    expect(record.ensureError).toBeNull()
    expect(record.ensurePlanId).toBeNull()
    expect(record.ensuredRecord).toBeNull()
  })

  test('invalidates an in-flight ensure when Record state is reset', async () => {
    const ensure = createDeferred()
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      ensure.promise.then((data) => respond(options, data))
    })

    const pending = record.ensureJourneyRecord(119)
    await flushRuntimePromises()
    record.resetRecordState()
    ensure.resolve({ journeyRecord: draftRecord() })
    await pending

    expect(record.ensureLoading).toBe(false)
    expect(record.ensureError).toBeNull()
    expect(record.ensurePlanId).toBeNull()
    expect(record.ensuredRecord).toBeNull()
  })

  test('propagates authentication errors for the caller boundary without ending the session in the Store', async () => {
    login(userA)
    const record = useRecordStore()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respondError(options, { code: 'UNAUTHORIZED', message: 'expired' }, 401)
    })

    await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'UNAUTHORIZED', statusCode: 401 })

    expect(useUserStore().isLoggedIn).toBe(true)
    expect(record.ensureError).toMatchObject({ code: 'UNAUTHORIZED' })
  })
})
