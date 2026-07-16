import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

const requiredFiles = [
  'components/AppTabbar.vue',
  'components/AiPet.vue',
  'components/AiChatSheet.vue',
  'components/WatercolorCard.vue',
  'components/PolaroidCard.vue',
  'components/GrowthBadge.vue',
  'components/TaskCard.vue',
  'components/PlanSection.vue',
  'stores/index.js',
  'stores/user.js',
  'stores/child.js',
  'stores/plan.js',
  'stores/task.js',
  'stores/record.js',
  'stores/pet.js',
  'mock/plans.js',
  'mock/tasks.js',
  'mock/records.js',
  'mock/ai.js',
  'styles/variables.scss',
  'styles/global.scss',
  'styles/mixins.scss',
  'pages/home/index.vue',
  'pages/plan/index.vue',
  'pages/guide/index.vue',
  'pages/tasks/index.vue',
  'pages/task-detail/index.vue',
  'pages/record/index.vue',
  'pages/profile/index.vue',
  'pages/login/index.vue',
]

const requiredPages = [
  'pages/home/index',
  'pages/plan/index',
  'pages/guide/index',
  'pages/tasks/index',
  'pages/task-detail/index',
  'pages/record/index',
  'pages/profile/index',
  'pages/login/index',
]

const missing = requiredFiles.filter((file) => !existsSync(join(src, file)))
if (missing.length) {
  throw new Error(`Missing phase 1 files:\n${missing.join('\n')}`)
}

const textFiles = requiredFiles.concat(['main.js', 'App.vue', 'pages.json'])
for (const file of textFiles) {
  const content = readFileSync(join(src, file))
  if (content[0] === 0xef && content[1] === 0xbb && content[2] === 0xbf) {
    throw new Error(`${file} must be saved as UTF-8 without BOM`)
  }
}

const pagesJson = readFileSync(join(src, 'pages.json'), 'utf8')
for (const page of requiredPages) {
  if (!pagesJson.includes(`"path": "${page}"`)) {
    throw new Error(`pages.json does not register ${page}`)
  }
}

const mainJs = readFileSync(join(src, 'main.js'), 'utf8')
if (!mainJs.includes('createPinia') || !mainJs.includes('app.use(pinia)')) {
  throw new Error('Pinia is not installed in main.js')
}

const taskStore = readFileSync(join(src, 'stores/task.js'), 'utf8')
if (!taskStore.includes('completedCount') || !taskStore.includes('progress')) {
  throw new Error('taskStore must expose completedCount and progress getters')
}

const petStore = readFileSync(join(src, 'stores/pet.js'), 'utf8')
for (const token of ['hidden', 'peek', 'open', 'chatOpen', 'pageContext']) {
  if (!petStore.includes(token)) {
    throw new Error(`petStore is missing ${token}`)
  }
}

console.log('phase1 smoke checks passed')
