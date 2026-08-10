import { spawnSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const vitest = join(root, 'node_modules', 'vitest', 'vitest.mjs')
const config = join(root, 'vitest.session.config.mjs')
const testFile = join(root, 'tests', 'session', 'task-plan-compatibility.spec.js')

const result = spawnSync(process.execPath, [vitest, 'run', testFile, '--config', config], {
  cwd: root,
  stdio: 'inherit',
})

if (result.error) {
  throw result.error
}

if (result.status !== 0) {
  throw new Error(`task plan compatibility Vitest check failed with exit code ${result.status}`)
}

console.log('phase3c1 task compatibility checks passed')
