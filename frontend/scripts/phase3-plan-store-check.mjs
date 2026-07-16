import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

const plansMock = readFileSync(join(src, 'mock/plans.js'), 'utf8')
const planStore = readFileSync(join(src, 'stores/plan.js'), 'utf8')

const requiredPlanFields = ['id', 'title', 'destination', 'ageGroup', 'duration', 'taskCount', 'interests', 'status']
for (const field of requiredPlanFields) {
  if (!plansMock.includes(`${field}:`)) {
    throw new Error(`mockPlans must include standard field: ${field}`)
  }
}

if (plansMock.includes('place:')) {
  throw new Error('mockPlans must use destination instead of place')
}

if (!planStore.includes('startExploration()')) {
  throw new Error('planStore must expose startExploration()')
}

for (const token of ['this.status = updatedPlan.status', 'this.currentPlan = updatedPlan', 'this.plans = this.plans.map']) {
  if (!planStore.includes(token)) {
    throw new Error(`startExploration must synchronize status with ${token}`)
  }
}

console.log('phase3 plan store checks passed')
