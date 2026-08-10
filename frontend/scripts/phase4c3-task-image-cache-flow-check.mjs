import { spawnSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const result = spawnSync(process.execPath, [join(root, 'node_modules', 'vitest', 'vitest.mjs'), 'run', join(root, 'tests', 'session', 'task-runtime-compatibility.spec.js'), '--config', join(root, 'vitest.session.config.mjs')], { cwd: root, stdio: 'inherit' })
if (result.error) throw result.error
if (result.status !== 0) throw new Error(`task image cache Vitest check failed with exit code ${result.status}`)
console.log('phase4c3 task image cache flow checks passed')
