import { beforeEach, describe, expect, test } from 'vitest'
import { getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { isAuthenticationError, request } from '../../src/utils/request.js'

function respond(statusCode, data) {
  setRequestHandler((options) => options.success({ statusCode, data }))
}

describe('request authentication normalization', () => {
  beforeEach(() => resetUniRuntime())

  test('normalizes an INVALID_TOKEN 401 as an authentication error', async () => {
    respond(401, { error: { code: 'INVALID_TOKEN', message: 'test authentication expired' } })

    await expect(request({ path: '/plans/7001', auth: true })).rejects.toMatchObject({
      statusCode: 401,
      code: 'INVALID_TOKEN',
    })

    expect(isAuthenticationError({ statusCode: 401, code: 'INVALID_TOKEN' })).toBe(true)
  })

  test('treats a 401 without a backend error code as an authentication error', async () => {
    respond(401, { message: 'unauthorized' })

    await expect(request({ path: '/plans/7001', auth: true })).rejects.toMatchObject({
      statusCode: 401,
      code: 'HTTP_ERROR',
    })

    expect(isAuthenticationError({ statusCode: 401, code: 'HTTP_ERROR' })).toBe(true)
  })

  test('recognizes TOKEN_EXPIRED as an authentication error', async () => {
    respond(401, { error: { code: 'TOKEN_EXPIRED', message: 'expired' } })

    await expect(request({ path: '/plans/7001', auth: true })).rejects.toMatchObject({ code: 'TOKEN_EXPIRED' })
    expect(isAuthenticationError({ statusCode: 401, code: 'TOKEN_EXPIRED' })).toBe(true)
  })

  test('normalizes a transport failure without ending authentication classification', async () => {
    setRequestHandler((options) => options.fail({ errMsg: 'request:fail connection refused' }))

    await expect(request({ path: '/plans/7001', auth: true })).rejects.toMatchObject({
      statusCode: 0,
      code: 'NETWORK_ERROR',
    })

    expect(isAuthenticationError({ statusCode: 0, code: 'NETWORK_ERROR' })).toBe(false)
  })

  test('does not classify RECORD_FINALIZED 409 as an authentication error', async () => {
    respond(409, { error: { code: 'RECORD_FINALIZED', message: 'record is final' } })

    await expect(request({ path: '/journey-records/7001', auth: true })).rejects.toMatchObject({
      statusCode: 409,
      code: 'RECORD_FINALIZED',
    })

    expect(isAuthenticationError({ statusCode: 409, code: 'RECORD_FINALIZED' })).toBe(false)
  })

  test('sends the in-memory authentication token as a Bearer header', async () => {
    uni.setStorageSync('tonglvji_auth', { token: 'test-session-token', userInfo: { id: 9001 } })
    respond(200, { success: true, data: {} })

    await request({ path: '/plans/7001', auth: true })

    expect(getRequestCalls()).toEqual([expect.objectContaining({
      header: expect.objectContaining({ Authorization: 'Bearer test-session-token' }),
    })])
  })
})
