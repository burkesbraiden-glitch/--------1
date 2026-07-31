import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

const plansMock = readFileSync(join(src, 'mock/plans.js'), 'utf8')
const planStore = readFileSync(join(src, 'stores/plan.js'), 'utf8')

function methodSource(source, name) {
  const match = source.match(new RegExp(`^\\s*(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  if (!match) {
    throw new Error(`planStore must expose ${name}()`)
  }

  let depth = 1
  const start = match.index + match[0].length
  for (let index = start; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(match.index, index + 1)
  }

  throw new Error(`${name} method must close correctly`)
}

const requiredPlanFields = ['id', 'title', 'destination', 'ageGroup', 'duration', 'taskCount', 'interests', 'status']
for (const field of requiredPlanFields) {
  if (!plansMock.includes(`${field}:`)) {
    throw new Error(`mockPlans must include standard field: ${field}`)
  }
}

if (plansMock.includes('place:')) {
  throw new Error('mockPlans must use destination instead of place')
}

const startExploration = methodSource(planStore, 'startExploration')
const selectPlan = methodSource(planStore, 'selectPlan')

if (!/^\s*const\s+data\s*=\s*await\s+plansApi\.startPlan\(\s*id\s*\)\s*;?\s*$/m.test(startExploration)) {
  throw new Error('startExploration must await the real startPlan response')
}

if (!/^\s*(?:const\s+\w+\s*=\s*)?this\.selectPlan\(\s*data\.plan\s*,\s*userId\s*\)\s*;?\s*$/m.test(startExploration)) {
  throw new Error('startExploration must synchronize the server plan with selectPlan(data.plan, userId)')
}

if (!/^\s*this\.currentPlan\s*=\s*normalizedPlan\s*;?\s*$/m.test(selectPlan) || !/^\s*this\.syncStatus\(\)\s*;?\s*$/m.test(selectPlan)) {
  throw new Error('selectPlan must synchronize currentPlan and status')
}

console.log('phase3 plan store checks passed')
