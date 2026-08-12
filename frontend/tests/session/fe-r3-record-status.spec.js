import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { computed, nextTick } from 'vue'
import { createDeferred, flushRuntimePromises, getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { useRecordStore } from '../../src/stores/record.js'
import { useUserStore } from '../../src/stores/user.js'

const userA = { id: 7, nickname: 'User A' }
const userB = { id: 8, nickname: 'User B' }

function login(user = userA) {
  useUserStore().loginSuccess(`token-${user.id}`, user)
}

function succeed(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function fail(options, statusCode, code) {
  options.success({ statusCode, data: { success: false, error: { code, message: code } } })
}

function record(planId, status = 'draft') {
  return { id: planId + 1000, planId, status }
}

function expectCorrectionInterface(store) {
  expect(store.correctionRecordStatusForPlan).toBeTypeOf('function')
  expect(store.loadJourneyRecordCorrectionStatus).toBeTypeOf('function')
  expect(store.retryJourneyRecordCorrectionStatus).toBeTypeOf('function')
  expect(store.markJourneyRecordCorrectionFinalized).toBeTypeOf('function')
}

describe('FE-R3 journey record correction status contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
    login()
  })

  test('treats JOURNEY_RECORD_NOT_FOUND as the missing correction status', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    setRequestHandler((options) => fail(options, 404, 'JOURNEY_RECORD_NOT_FOUND'))

    await expect(store.loadJourneyRecordCorrectionStatus(101)).resolves.toMatchObject({ state: 'missing', error: null })
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ state: 'missing', error: null })
  })

  test('accepts draft and finalized records but rejects malformed server contracts', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    const responses = [
      { journeyRecord: record(101, 'draft') },
      { journeyRecord: record(102, 'finalized') },
      { journeyRecord: record(999, 'draft') },
      { journeyRecord: record(104, 'unexpected') },
      {},
      { journeyRecord: 'not-an-object' },
    ]
    setRequestHandler((options) => succeed(options, responses.shift()))

    await expect(store.loadJourneyRecordCorrectionStatus(101)).resolves.toMatchObject({ state: 'draft' })
    await expect(store.loadJourneyRecordCorrectionStatus(102)).resolves.toMatchObject({ state: 'finalized' })
    for (const planId of [103, 104, 105, 106]) {
      await expect(store.loadJourneyRecordCorrectionStatus(planId)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
      expect(store.correctionRecordStatusForPlan(planId)).toMatchObject({ state: 'error', error: { code: 'INVALID_RESPONSE' } })
    }
  })

  test('updates a previously evaluated correction status computed when its plan key is added', async () => {
    const store = useRecordStore()
    const planId = 155
    setRequestHandler((options) => succeed(options, { journeyRecord: record(planId, 'draft') }))

    const correctionStatus = computed(() => store.correctionRecordStatusForPlan(planId))
    expect(correctionStatus.value).toBeNull()

    await store.loadJourneyRecordCorrectionStatus(planId)
    await nextTick()

    expect(store.correctionRecordStatusForPlan(planId)).toMatchObject({
      state: 'draft',
      loading: false,
      error: null,
    })
    expect(correctionStatus.value).toMatchObject({
      state: 'draft',
      loading: false,
      error: null,
    })
  })

  test('dedupes the same request identity and a forced lookup bypasses that dedupe', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    const first = createDeferred()
    const second = createDeferred()
    let calls = 0
    setRequestHandler((options) => {
      calls += 1
      ;(calls === 1 ? first : second).promise.then((data) => succeed(options, data))
    })

    const requestA = store.loadJourneyRecordCorrectionStatus(101)
    const sameRequestA = store.loadJourneyRecordCorrectionStatus(101)
    const requestB = store.loadJourneyRecordCorrectionStatus(101, { force: true })
    expect(requestA).toBe(sameRequestA)
    expect(requestB).not.toBe(requestA)
    expect(getRequestCalls()).toHaveLength(2)
    second.resolve({ journeyRecord: record(101, 'finalized') })
    await requestB
    first.resolve({ journeyRecord: record(101, 'draft') })
    await requestA
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ state: 'finalized' })
  })

  test('retry forces a replacement lookup and an old finally cannot remove the new force request', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    const first = createDeferred()
    const second = createDeferred()
    let calls = 0
    setRequestHandler((options) => {
      calls += 1
      ;(calls === 1 ? first : second).promise.then((data) => succeed(options, data))
    })

    const requestA = store.loadJourneyRecordCorrectionStatus(101)
    const requestB = store.retryJourneyRecordCorrectionStatus(101)
    expect(requestB).not.toBe(requestA)
    first.resolve({ journeyRecord: record(101, 'draft') })
    await requestA
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ loading: true })
    second.resolve({ journeyRecord: record(101, 'finalized') })
    await requestB
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ loading: false, state: 'finalized' })
  })

  test('isolates stale success, errors, and finally work across plan and session changes', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    const pending = createDeferred()
    setRequestHandler((options) => pending.promise.then((data) => succeed(options, data)))

    const request = store.loadJourneyRecordCorrectionStatus(101)
    useUserStore().loginSuccess('token-b', userB)
    store.resetRecordState()
    pending.resolve({ journeyRecord: record(101, 'draft') })
    await request
    await flushRuntimePromises()
    expect(store.correctionRecordStatusForPlan(101)).toBeNull()
  })

  test('authoritative finalization invalidates older status lookups and reset clears every correction registry entry', async () => {
    const store = useRecordStore()
    expectCorrectionInterface(store)
    const pending = createDeferred()
    setRequestHandler((options) => pending.promise.then((data) => succeed(options, data)))

    const oldLookup = store.loadJourneyRecordCorrectionStatus(101)
    store.markJourneyRecordCorrectionFinalized(101)
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ state: 'finalized', loading: false })
    pending.resolve({ journeyRecord: record(101, 'draft') })
    await oldLookup
    expect(store.correctionRecordStatusForPlan(101)).toMatchObject({ state: 'finalized', loading: false })
    store.resetRecordState()
    expect(store.correctionRecordStatusForPlan(101)).toBeNull()
  })
})
