import { usePlanStore } from '../stores/plan.js'
import { useTaskStore } from '../stores/task.js'
import { useUserStore } from '../stores/user.js'

export async function ensureCurrentPlanReady({ withTasks = false, force = false, planId = null } = {}) {
  const userStore = useUserStore()
  const planStore = usePlanStore()
  const taskStore = withTasks ? useTaskStore() : null
  const hasRequestedPlan = planId !== null && planId !== undefined && String(planId).trim() !== ''

  if (!userStore.isAuthReady || userStore.isRestoring) {
    await userStore.restoreSession()
  }

  const userId = userStore.userInfo?.id
  if (!userStore.isLoggedIn || !userId) {
    planStore.clearInMemoryState()
    if (taskStore) {
      taskStore.resetSessionState()
    }
    return {
      user: null,
      currentPlan: null,
      plans: [],
      unavailable: hasRequestedPlan,
    }
  }

  const result = await planStore.fetchPlans(userId, {
    force,
    selectionPolicy: hasRequestedPlan ? 'none' : 'default',
  })
  const currentPlan = hasRequestedPlan
    ? planStore.selectPlanById(planId, userId)
    : planStore.currentPlan

  if (taskStore && currentPlan) {
    await taskStore.ensureTasks(currentPlan.id, currentPlan.status)
  }

  return {
    user: userStore.userInfo,
    plans: result.plans,
    currentPlan,
    unavailable: hasRequestedPlan && !currentPlan,
  }
}
