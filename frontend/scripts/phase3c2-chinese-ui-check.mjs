import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const guidePage = read('pages/guide/index.vue')
const guidesApiPath = join(src, 'api/guides.js')
const guidesApi = read('api/guides.js')

const forbiddenUserCopyPatterns = [
  />Audio</,
  /['"`]Audio unavailable['"`]/,
  /['"`]This guide has no audio yet['"`]/,
  /title: ['"`]simple['"`]/,
  /title: ['"`]child words['"`]/,
  /title: ['"`]story['"`]/,
  /['"`]Loading guide/,
  /['"`]Preparing guide/,
  />Retry</,
  /['"`]Guide failed/,
  /['"`]Plan not found['"`]/,
  /['"`]Network is unavailable/,
  /Please try again/,
  /Please sign in again/,
  /['"`]Tap to play audio['"`]/,
  /['"`]Audio is playing['"`]/,
  /['"`]Paused['"`]/,
  /['"`]Pause guide['"`]/,
  /['"`]Resume guide['"`]/,
  /['"`]Play guide['"`]/,
]

for (const pattern of forbiddenUserCopyPatterns) {
  assert(!pattern.test(guidePage), `Guide page still contains English UI copy: ${pattern}`)
}

const knownMojibake = [
  '娴犲﹤銇夌憰浣稿箵',
  '鐏忓繑姊?',
  '璁茶В鍗?',
  '閾?',
  '鍋?',
  '鎾?',
  '闂佹彃绉甸弻濠囧礉閻樼儤绁?',
]

for (const text of knownMojibake) {
  assert(!guidePage.includes(text), `Guide page still contains known mojibake: ${text}`)
}

const requiredChineseCopy = [
  '讲解卡',
  '语音讲解',
  '暂不提供语音讲解',
  '正在加载讲解卡',
  '正在准备专属讲解卡',
  '重新加载',
  '讲给孩子听',
  '可以先问孩子',
  '今天重点看',
]

for (const text of requiredChineseCopy) {
  assert(guidePage.includes(text), `Guide page missing Chinese UI copy: ${text}`)
}

assert(guidePage.includes('currentGuide.childIntro'), 'Guide childIntro must still come from backend guide data')
assert(guidePage.includes('currentGuide.questions'), 'Guide questions must still come from backend guide data')
assert(guidePage.includes('currentGuide.focusItems'), 'Guide focusItems must still come from backend guide data')
assert(guidePage.includes('currentGuide.destination'), 'Guide destination must still come from backend guide data')
assert(!guidePage.includes("questions: ['"), 'Guide page must not restore hardcoded questions')
assert(!guidePage.includes("focusItems: ['"), 'Guide page must not restore hardcoded focus items')

assert(existsSync(guidesApiPath), 'Guide API file must still exist')
assert(
  guidesApi.trim() === `import request from '../utils/request.js'

export function getGuide(planId) {
  return request({
    path: \`/plans/\${planId}/guide\`,
    method: 'GET',
    auth: true,
  })
}

export function generateGuide(planId) {
  return request({
    path: \`/plans/\${planId}/guide/generate\`,
    method: 'POST',
    auth: true,
  })
}`,
  'Guide API must not be changed in phase 3C-2.1',
)

assert(existsSync(join(src, 'api/tasks.js')), 'phase 4C-1 should provide Tasks API while preserving Chinese UI checks')

console.log('phase3c2 chinese ui checks passed')
