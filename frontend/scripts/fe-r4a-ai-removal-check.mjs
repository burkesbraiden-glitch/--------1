import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { extname, join, relative } from 'node:path'

const frontendRoot = process.cwd()
const srcRoot = join(frontendRoot, 'src')
const projectRoot = join(frontendRoot, '..')

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function collectSourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      return collectSourceFiles(path)
    }
    return ['.js', '.vue'].includes(extname(entry.name)) ? [path] : []
  })
}

function findMatches(pattern) {
  return collectSourceFiles(srcRoot).flatMap((file) => {
    const source = readFileSync(file, 'utf8')
    return pattern.test(source) ? [relative(frontendRoot, file)] : []
  })
}

const removedFiles = [
  'src/components/AiPet.vue',
  'src/components/AiChatSheet.vue',
  'src/stores/pet.js',
  'src/mock/ai.js',
]

const remainingFiles = removedFiles.filter((file) => existsSync(join(frontendRoot, file)))
assert(remainingFiles.length === 0, `AI-only files remain:\n${remainingFiles.join('\n')}`)

const runtimePatterns = [
  /\bAiPet\b/,
  /\bAiChatSheet\b/,
  /\busePetStore\b/,
  /stores\/pet/,
  /mock\/ai/,
  /\bopenPetChat\b/,
  /\bopenAiShortcut\b/,
  /\bpeekPet\b/,
  /\bhidePet\b/,
  /\bopenChat\b/,
  /\bcloseChat\b/,
  /\bchatOpen\b/,
  /小旅/,
  /AI建议/,
  /问问小旅/,
  /小旅陪伴/,
  /Mock AI/,
  /AI 宠物/,
]

const runtimeMatches = runtimePatterns.flatMap((pattern) => findMatches(pattern))
assert(runtimeMatches.length === 0, `AI runtime references remain:\n${[...new Set(runtimeMatches)].join('\n')}`)

const requiredRuntimeContracts = [
  ['src/stores/guide.js', /useGuideStore/],
  ['src/stores/task.js', /useTaskStore/],
  ['src/stores/record.js', /useRecordStore/],
  ['src/pages/guide/index.vue', /childIntro/],
  ['src/pages/tasks/index.vue', /ensureTasks/],
  ['src/pages/task-detail/index.vue', /noteDraft/],
  ['src/pages/record/index.vue', /JourneyRecord|journeyRecord/],
  ['src/pages/record-detail/index.vue', /finalizeJourneyRecordDraft/],
]

for (const [file, pattern] of requiredRuntimeContracts) {
  const source = readFileSync(join(frontendRoot, file), 'utf8')
  assert(pattern.test(source), `Required business contract is missing: ${file}`)
}

const agents = readFileSync(join(projectRoot, 'AGENTS.md'), 'utf8')
const product = readFileSync(join(projectRoot, 'docs/product.md'), 'utf8')
const implementationPlan = readFileSync(join(projectRoot, 'docs/implementation-plan.md'), 'utf8')
const historicalDesign = readFileSync(join(projectRoot, 'docs/2026-08-10-fe-r2-plan-completion-record-recovery-design.md'), 'utf8')
const historicalPlan = readFileSync(join(projectRoot, 'docs/2026-08-10-fe-r2-plan-completion-record-recovery-implementation-plan.md'), 'utf8')

assert(agents.includes('## 首版 AI 范围') && !agents.includes('## AI 宠物'), 'AGENTS.md has not adopted the FE-R4A first-version AI scope')
assert(!product.includes('AI 宠物小旅'), 'docs/product.md still lists 小旅 as a core feature')
assert(implementationPlan.includes('2026-08-11 产品范围更新'), 'docs/implementation-plan.md lacks the FE-R4A supersession notice')
assert(historicalDesign.includes('2026-08-11 FE-R4A supersession:'), 'historical FE-R2 design lacks a supersession notice')
assert(historicalPlan.includes('2026-08-11 FE-R4A supersession:'), 'historical FE-R2 implementation plan lacks a supersession notice')

console.log('FE-R4A AI removal check passed')
