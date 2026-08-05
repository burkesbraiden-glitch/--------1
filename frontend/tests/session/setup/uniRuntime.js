import { afterEach } from 'vitest'

const storage = new Map()
const requestCalls = []
const uploadCalls = []
const downloadCalls = []
const fetchCalls = []
const reLaunchCalls = []

let requestHandler = null
let uploadHandler = null
let downloadHandler = null
let fetchHandler = null

function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value))
}

function requestSnapshot(options) {
  return {
    url: options.url,
    method: options.method,
    header: clone(options.header),
    data: clone(options.data),
  }
}

function callHandler(handler, name, options) {
  if (!handler) {
    throw new Error(`Test runtime ${name} handler has not been configured`)
  }
  Promise.resolve().then(() => handler(options))
}

export function resetUniRuntime() {
  storage.clear()
  requestCalls.splice(0)
  uploadCalls.splice(0)
  downloadCalls.splice(0)
  fetchCalls.splice(0)
  reLaunchCalls.splice(0)
  requestHandler = null
  uploadHandler = null
  downloadHandler = null
  fetchHandler = null
}

export function setRequestHandler(handler) { requestHandler = handler }
export function setUploadHandler(handler) { uploadHandler = handler }
export function setDownloadHandler(handler) { downloadHandler = handler }
export function setFetchHandler(handler) { fetchHandler = handler }
export function getStorageSnapshot() { return Object.fromEntries([...storage].map(([key, value]) => [key, clone(value)])) }
export function getRequestCalls() { return requestCalls.map(clone) }
export function getFetchCalls() { return fetchCalls.map(clone) }
export function getReLaunchCalls() { return reLaunchCalls.map(clone) }

export function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

export async function flushRuntimePromises() {
  await Promise.resolve()
  await Promise.resolve()
}

globalThis.uni = {
  getStorageSync(key) { return clone(storage.get(key)) },
  setStorageSync(key, value) { storage.set(key, clone(value)) },
  removeStorageSync(key) { storage.delete(key) },
  clearStorageSync() { storage.clear() },
  request(options) {
    requestCalls.push(requestSnapshot(options))
    callHandler(requestHandler, 'uni.request', options)
  },
  uploadFile(options) {
    uploadCalls.push(requestSnapshot(options))
    callHandler(uploadHandler, 'uni.uploadFile', options)
  },
  downloadFile(options) {
    downloadCalls.push(requestSnapshot(options))
    callHandler(downloadHandler, 'uni.downloadFile', options)
  },
  reLaunch(options) {
    reLaunchCalls.push(clone(options))
    return Promise.resolve()
  },
}

globalThis.window = {}
globalThis.fetch = (...args) => {
  if (!fetchHandler) {
    throw new Error('Test runtime fetch handler has not been configured')
  }
  fetchCalls.push({ url: args[0], options: clone(args[1]) })
  return Promise.resolve().then(() => fetchHandler(...args))
}

afterEach(() => resetUniRuntime())
