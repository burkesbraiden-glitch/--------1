import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const homePath = join(root, 'src/pages/home/index.vue')
const planStorePath = join(root, 'src/stores/plan.js')
const plansApiPath = join(root, 'src/api/plans.js')

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
  console.log(`PASS: ${message}`)
}

function read(path) {
  assert(existsSync(path), `${path} exists`)
  return readFileSync(path, 'utf8')
}

function codeMask(source) {
  let result = ''
  let state = 'code'

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]
    const next = source[index + 1]

    if (state === 'code') {
      if (character === '/' && next === '/') {
        result += '  '
        index += 1
        state = 'line-comment'
      } else if (character === '/' && next === '*') {
        result += '  '
        index += 1
        state = 'block-comment'
      } else if (character === '\'' || character === '"') {
        result += character
        state = character
      } else if (character === '`') {
        result += character
        state = 'template'
      } else {
        result += character
      }
      continue
    }

    if (state === 'line-comment') {
      result += character === '\n' ? '\n' : ' '
      if (character === '\n') state = 'code'
      continue
    }

    if (state === 'block-comment') {
      if (character === '*' && next === '/') {
        result += '  '
        index += 1
        state = 'code'
      } else {
        result += character === '\n' ? '\n' : ' '
      }
      continue
    }

    if (state === 'template') {
      result += character === '\n' || character === '`' ? character : ' '
      if (character === '`') state = 'code'
      continue
    }

    if (character === '\\') {
      result += ' '
      if (next) {
        result += next === '\n' ? '\n' : ' '
        index += 1
      }
      continue
    }

    result += character === '\n' || character === state ? character : ' '
    if (character === state) state = 'code'
  }

  return result
}

function commentMask(source) {
  let result = ''
  let state = 'code'

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]
    const next = source[index + 1]

    if (state === 'code') {
      if (character === '/' && next === '/') {
        result += '  '
        index += 1
        state = 'line-comment'
      } else if (character === '/' && next === '*') {
        result += '  '
        index += 1
        state = 'block-comment'
      } else if (character === '\'' || character === '"' || character === '`') {
        result += character
        state = character
      } else {
        result += character
      }
      continue
    }

    if (state === 'line-comment') {
      result += character === '\n' ? '\n' : ' '
      if (character === '\n') state = 'code'
      continue
    }

    if (state === 'block-comment') {
      if (character === '*' && next === '/') {
        result += '  '
        index += 1
        state = 'code'
      } else {
        result += character === '\n' ? '\n' : ' '
      }
      continue
    }

    result += character
    if (character === '\\' && state !== '`' && next) {
      result += next
      index += 1
    } else if (character === state) {
      state = 'code'
    }
  }

  return result
}

function methodSource(source, name) {
  const masked = codeMask(source)
  const match = masked.match(new RegExp(`(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `${name} method exists`)

  const openBraceIndex = match.index + match[0].length - 1
  let depth = 0
  for (let index = openBraceIndex; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') depth -= 1
    if (depth === 0 && index > openBraceIndex) return source.slice(match.index, index + 1)
  }

  throw new Error(`${name} method must close correctly`)
}

function templateSource(source) {
  const match = source.match(/<template>([\s\S]*?)<\/template>/)
  assert(match, 'home page template exists')
  return match[1].replace(/<!--[\s\S]*?-->/g, '')
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function titleInputBinding(template) {
  const inputs = [...template.matchAll(/<input\b([\s\S]*?)\/?\s*>/gi)]
  for (const input of inputs) {
    const attributes = input[1]
    const binding = /\bv-model\s*=\s*["']([^"']+)["']/.exec(attributes)?.[1]?.trim()
    const maxlength = /\bmaxlength\s*=\s*["']?(\d+)["']?/.exec(attributes)?.[1]
    const required = /(?:^|\s)required(?:\s|=|$)/.test(attributes)
    const precedingField = template.slice(Math.max(0, input.index - 360), input.index).replace(/<[^>]+>/g, ' ')
    const isTitleField = /(?:title|标题|名称|名字)/i.test(binding || '') || /(?:标题|名称|名字)/.test(precedingField)
    if (binding && isTitleField) {
      return { binding, maxlength, required }
    }
  }
  return null
}

function bindingExpression(binding) {
  return new RegExp(`(?:this\\.)?${escapeRegExp(binding)}`)
}

function supportsOptionalTitlePayload(submitSource, binding) {
  const executable = codeMask(submitSource)
  const bindingPattern = bindingExpression(binding).source
  const normalizedMatch = executable.match(new RegExp(`(?:const|let)\\s+(\\w+)\\s*=\\s*${bindingPattern}\\s*\\.trim\\s*\\(\\s*\\)`))
  if (!normalizedMatch) return false

  const normalizedTitle = normalizedMatch[1]
  const createPayloadVariable = executable.match(/\.createPlan\s*\(\s*(\w+)\s*(?:,|\))/)?.[1]
  const conditionalAssignment = new RegExp(`if\\s*\\(\\s*${escapeRegExp(normalizedTitle)}\\s*\\)\\s*\\{?[\\s\\S]*?${escapeRegExp(createPayloadVariable || 'payload')}\\.title\\s*=\\s*${escapeRegExp(normalizedTitle)}`).test(executable)
  const conditionalSpread = new RegExp(`\\.createPlan\\s*\\(\\s*\\{[\\s\\S]*?\\.\\.\\.\\s*\\(\\s*${escapeRegExp(normalizedTitle)}\\s*\\?\\s*\\{\\s*title\\s*(?::\\s*${escapeRegExp(normalizedTitle)})?\\s*\\}\\s*:\\s*\\{\\s*\\}\\s*\\)`).test(executable)
  return Boolean(createPayloadVariable && conditionalAssignment) || conditionalSpread
}

function hasClientDefaultTitle(submitSource) {
  const visibleCode = commentMask(submitSource)
  return /title\s*:\s*(?:['"]故宫亲子探索['"]|[\s\S]{0,180}?亲子探索)/.test(visibleCode)
}

function assertRuleExamples() {
  const conditionalAssignment = `
    async submitPlan() {
      const normalizedTitle = this.planTitle.trim()
      const payload = { destination: this.destination }
      if (normalizedTitle) { payload.title = normalizedTitle }
      await this.planStore.createPlan(payload)
    }
  `
  const conditionalSpread = `
    async submitPlan() {
      const title = form.title.trim()
      await planStore.createPlan({ destination: form.destination, ...(title ? { title } : {}) })
    }
  `
  assert(supportsOptionalTitlePayload(conditionalAssignment, 'planTitle'), 'title rule accepts conditional title assignment')
  assert(supportsOptionalTitlePayload(conditionalSpread, 'form.title'), 'title rule accepts conditional title spread')
  assert(hasClientDefaultTitle(`async submitPlan() { await this.planStore.createPlan({ title: '故宫亲子探索' }) }`), 'title rule rejects fixed title')
  assert(hasClientDefaultTitle(`async submitPlan() { await this.planStore.createPlan({ title: title || \`${'${form.destination}'}亲子探索\` }) }`), 'title rule rejects a client default title')
  assert(!supportsOptionalTitlePayload(`async submitPlan() { await this.planStore.createPlan({ title: form.title.trim() }) }`, 'form.title'), 'title rule rejects sending blank trimmed titles')
  assert(!supportsOptionalTitlePayload(`async submitPlan() { const payload = {}; if (form.title) payload.title = form.title; await this.planStore.createPlan(payload) }`, 'form.title'), 'title rule rejects an untrimmed title')
  assert(!supportsOptionalTitlePayload(`function buildOptionalTitle() { return form.title.trim() } async submitPlan() { await this.planStore.createPlan({ title: '故宫亲子探索' }) }`, 'form.title'), 'title rule rejects an unused title helper')
  assert(!supportsOptionalTitlePayload(`// form.title.trim()\nconst example = 'optional title'\nasync submitPlan() { await this.planStore.createPlan({ destination: form.destination }) }`, 'form.title'), 'title rule ignores comments and strings')
}

const home = read(homePath)
const planStore = read(planStorePath)
const plansApi = read(plansApiPath)
const template = templateSource(home)
const submitTag = [...template.matchAll(/<[^>]+>/g)].find((match) => /plan-sheet__submit/.test(match[0]) && /@click\s*=/.test(match[0]))?.[0] || ''
const submitBinding = /@click\s*=\s*["']([A-Za-z_$][\w$]*)(?:\s*\(\s*\))?["']/.exec(submitTag)
assert(submitBinding, 'home plan form has a real template-bound submit handler')
const submitPlan = methodSource(home, submitBinding[1])
const planCreate = methodSource(planStore, 'createPlan')
const executableSubmit = codeMask(submitPlan)

assertRuleExamples()
assert(/\.createPlan\s*\(/.test(executableSubmit), 'real submit handler calls the Plan Store create action')
assert(/plansApi\.createPlan\s*\(\s*payload\s*\)/.test(codeMask(planCreate)), 'Plan Store forwards the original payload to the formal plans API')
assert(/this\.selectPlan\s*\(\s*data\.plan/.test(codeMask(planCreate)), 'Plan Store uses the backend-returned plan as the selected plan')
assert(/path:\s*['"]\/plans['"]/.test(plansApi) && /method:\s*['"]POST['"]/.test(plansApi), 'formal plan creation uses POST /plans')
assert(!/(?:createdPlan|this\.plan\.currentPlan)\.title\s*=/.test(executableSubmit), 'submit handler does not overwrite the backend title after creation')

const titleInput = titleInputBinding(template)
const failures = []
if (!titleInput) {
  failures.push('missing optional title input')
} else {
  if (titleInput.maxlength !== '120') failures.push('title input must set maxlength=120')
  if (titleInput.required) failures.push('title input must remain optional')
  if (!supportsOptionalTitlePayload(submitPlan, titleInput.binding)) failures.push('trimmed nonblank title must be conditionally added to the create payload')
}
if (hasClientDefaultTitle(submitPlan)) {
  failures.push('submit handler still supplies a client default title')
}

assert(
  failures.length === 0,
  `plan creation supports an optional server-authoritative custom title: ${failures.join('; ')}`,
)

console.log('phase6a1 plan title checks passed')
