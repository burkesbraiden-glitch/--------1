import { spawn } from 'node:child_process'
import { mkdirSync, readdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const root = process.cwd()
const projectRoot = join(root, '..')
const outDir = join(root, 'rendered', 'phase2c2')
mkdirSync(outDir, { recursive: true })

const backend = spawn(join(projectRoot, 'backend', '.venv', 'Scripts', 'python.exe'), ['run.py'], {
  cwd: join(projectRoot, 'backend'),
})
const frontend = spawn(process.execPath, ['node_modules/@dcloudio/vite-plugin-uni/bin/uni.js', '--host', '127.0.0.1'], {
  cwd: root,
})

let chrome

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForUrl(url, timeoutMs = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url)
      if (response.status < 500) {
        return
      }
    } catch {}
    await delay(500)
  }
  throw new Error(`Timeout waiting for ${url}`)
}

async function api(path, method = 'GET', body = null, token = '') {
  const response = await fetch(`http://127.0.0.1:5000/api/v1${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  return response.json()
}

async function login(phone) {
  await api('/auth/send-code', 'POST', { phone })
  const response = await api('/auth/login', 'POST', { phone, code: '123456' })
  return response.data
}

async function ensureChild(loginData) {
  const listed = await api('/children', 'GET', null, loginData.accessToken)
  if (listed.data.currentChild) {
    return listed.data.currentChild
  }
  const created = await api(
    '/children',
    'POST',
    { name: '小小探索家', age: 7, city: '北京', interests: ['历史故事', '古建筑', '观察探索'] },
    loginData.accessToken,
  )
  return created.data.child
}

async function connectChrome(port) {
  const start = Date.now()
  while (Date.now() - start < 30000) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json`)
      if (response.ok) {
        const targets = await response.json()
        const page = targets.find((target) => target.type === 'page')
        if (page?.webSocketDebuggerUrl) {
          return page.webSocketDebuggerUrl
        }
      }
    } catch {}
    await delay(300)
  }
  throw new Error('Chrome DevTools did not start')
}

async function createCdp(wsUrl) {
  const ws = new WebSocket(wsUrl)
  await new Promise((resolve, reject) => {
    ws.onopen = resolve
    ws.onerror = reject
  })

  let id = 0
  const pending = new Map()
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data)
    if (!message.id || !pending.has(message.id)) {
      return
    }
    const callbacks = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) {
      callbacks.reject(new Error(JSON.stringify(message.error)))
    } else {
      callbacks.resolve(message.result)
    }
  }

  function send(method, params = {}) {
    const commandId = ++id
    ws.send(JSON.stringify({ id: commandId, method, params }))
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        pending.delete(commandId)
        reject(new Error(`CDP timeout: ${method}`))
      }, 10000)
      pending.set(commandId, {
        resolve: (result) => {
          clearTimeout(timeout)
          resolve(result)
        },
        reject: (error) => {
          clearTimeout(timeout)
          reject(error)
        },
      })
    })
  }

  return { send, close: () => ws.close() }
}

async function main() {
  await waitForUrl('http://127.0.0.1:5000/api/v1/health')
  await waitForUrl('http://localhost:5173/#/pages/profile/index')

  const emptyLogin = await login('13900002043')
  const childLogin = await login('13900002044')
  const existingChild = await ensureChild(childLogin)
  await api(`/children/${existingChild.id}`, 'PATCH', { city: '北京' }, childLogin.accessToken)

  const port = 9228
  chrome = spawn(
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    [
      '--headless=new',
      '--no-sandbox',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      `--remote-debugging-port=${port}`,
      '--window-size=390,844',
      `--user-data-dir=${join(tmpdir(), `tonglvji-phase2c2-${Date.now()}`)}`,
      'about:blank',
    ],
  )

  const wsUrl = await connectChrome(port)
  const cdp = await createCdp(wsUrl)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  })

  async function setProfile(loginData) {
    await cdp.send('Page.navigate', { url: 'http://localhost:5173/#/pages/home/index' })
    await delay(1200)
    const auth = { token: loginData.accessToken, userInfo: loginData.user }
    await cdp.send('Runtime.evaluate', {
      expression: `uni.setStorageSync('tonglvji_auth', ${JSON.stringify(auth)})`,
    })
    await cdp.send('Page.navigate', { url: 'http://localhost:5173/#/pages/profile/index' })
    await delay(2500)
  }

  async function screenshot(name) {
    const result = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    writeFileSync(join(outDir, name), Buffer.from(result.data, 'base64'))
  }

  await setProfile(emptyLogin)
  await cdp.send('Runtime.evaluate', {
    expression: 'window.scrollTo(0, 900)',
  })
  await delay(500)
  await screenshot('01-empty-child.png')
  await cdp.send('Runtime.evaluate', {
    expression: `document.elementFromPoint(195, 433)?.click()`,
  })
  await delay(800)
  await screenshot('02-child-form.png')

  await setProfile(childLogin)
  await screenshot('03-created-child.png')
  const listed = await api('/children', 'GET', null, childLogin.accessToken)
  await api(`/children/${listed.data.currentChild.id}`, 'PATCH', { city: '上海' }, childLogin.accessToken)
  await setProfile(childLogin)
  await screenshot('04-updated-child.png')
  cdp.close()

  console.log(readdirSync(outDir).filter((file) => file.endsWith('.png')).join('\n'))
}

main()
  .finally(() => {
    backend.kill()
    frontend.kill()
    if (chrome) {
      chrome.kill()
    }
  })
  .catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
