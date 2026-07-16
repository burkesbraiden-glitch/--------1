import { usePlanStore } from '../stores/plan.js'
import { useTaskStore } from '../stores/task.js'
import { useUserStore } from '../stores/user.js'

export async function ensureCurrentPlanReady({ withTasks = false, force = false } = {}) {
  const userStore = useUserStore()
  const planStore = usePlanStore()
  const taskStore = withTasks ? useTaskStore() : null

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
    }
  }

  const result = await planStore.fetchPlans(userId, { force })
  if (taskStore && planStore.currentPlan) {
    await taskStore.ensureTasks(planStore.currentPlan.id, planStore.currentPlan.status)
  }

  return {
    user: userStore.userInfo,
    plans: result.plans,
    currentPlan: planStore.currentPlan,
  }
}
