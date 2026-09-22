import { defineStore } from 'pinia'
import * as plansApi from '../api/plans.js'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

export const CURRENT_PLAN_SELECTION_KEY = 'tonglvji_current_plan_selection'

let fetchPromise = null
let fetchPromiseUserId = null
let fetchPromiseEpoch = null
let fetchPromiseSelectionPolicy = null
let completionPromise = null
let completionPlanId = null
let completionUserId = null
let completionEpoch = null

function getUniStorage() {
  if (typeof uni === 'undefined') {
    return null
  }
  return uni
}

function normalizeProgress(progress) {
  return {
    total: Math.max(0, Number(progress?.total) || 0),
    completed: Math.max(0, Number(progress?.completed) || 0),
  }
}

function normalizePlan(plan) {
  if (!plan) {
    return null
  }

  return {
    ...plan,
    interests: Array.isArray(plan.interests) ? plan.interests : [],
    taskCount: Number(plan.taskCount) || 0,
    routeStopId: plan.routeStopId ?? null,
    sourceSnapshot: plan.sourceSnapshot ?? null,
    progress: normalizeProgress(plan.progress),
  }
}

function hasProjectionField(plan, field) {
  return Object.prototype.hasOwnProperty.call(plan || {}, field) && plan[field] !== undefined
}

function mergePlanProjection(existingPlan, returnedPlan) {
  if (!existingPlan) {
    return returnedPlan
  }

  return {
    ...returnedPlan,
    ...(!hasProjectionField(returnedPlan, 'routeStopId') ? { routeStopId: existingPlan.routeStopId } : {}),
    ...(!hasProjectionField(returnedPlan, 'sourceSnapshot') ? { sourceSnapshot: existingPlan.sourceSnapshot } : {}),
    ...(!hasProjectionField(returnedPlan, 'progress') ? { progress: existingPlan.progress } : {}),
  }
}

function samePlanId(left, right) {
  return String(left) === String(right)
}

function sameUserId(left, right) {
  return String(left) === String(right)
}

function hasPlanId(value) {
  return value !== null && value !== undefined && String(value).trim() !== ''
}

function sameChildId(left, right) {
  return hasPlanId(left) && hasPlanId(right) && String(left) === String(right)
}

function readStoredSelection() {
  const storage = getUniStorage()
  if (!storage?.getStorageSync) {
    return null
  }

  const saved = storage.getStorageSync(CURRENT_PLAN_SELECTION_KEY)
  if (!saved || typeof saved !== 'object') {
    return null
  }
  return saved
}

function saveStoredSelection(userId, planId) {
  const storage = getUniStorage()
  if (storage?.setStorageSync) {
    storage.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId, planId })
  }
}

function clearStoredSelection() {
  const storage = getUniStorage()
  if (storage?.removeStorageSync) {
    storage.removeStorageSync(CURRENT_PLAN_SELECTION_KEY)
  }
}

export const usePlanStore = defineStore('plan', {
  state: () => ({
    plans: [],
    currentPlan: null,
    status: 'draft',
    isLoading: false,
    isLoaded: false,
    error: null,
    loadedForUserId: null,
    isCompleting: false,
    completionError: null,
  }),
  actions: {
    syncStatus() {
      this.status = this.currentPlan?.status || 'draft'
    },
    clearRemoteStateForUser(userId = null) {
      this.plans = []
      this.currentPlan = null
      this.status = 'draft'
      this.error = null
      this.isLoaded = false
      this.loadedForUserId = userId
    },
    resetSessionState() {
      this.plans = []
      this.currentPlan = null
      this.status = 'draft'
      this.isLoading = false
      this.isLoaded = false
      this.error = null
      this.loadedForUserId = null
      fetchPromise = null
      fetchPromiseUserId = null
      fetchPromiseEpoch = null
      fetchPromiseSelectionPolicy = null
      completionPromise = null
      completionPlanId = null
      completionUserId = null
      completionEpoch = null
      this.isCompleting = false
      this.completionError = null
      clearStoredSelection()
    },
    storedSelectionForUser(userId) {
      const saved = readStoredSelection()
      if (!saved) {
        return null
      }
      if (!sameUserId(saved.userId, userId)) {
        clearStoredSelection()
        return null
      }
      return saved
    },
    resolvePlanForContext({ explicitPlanId = null, activeChildId = null, userId = this.loadedForUserId } = {}) {
      if (!sameUserId(this.loadedForUserId, userId)) {
        return null
      }

      if (hasPlanId(explicitPlanId)) {
        return this.plans.find((plan) => samePlanId(plan.id, explicitPlanId)) || null
      }

      const scopedPlans = hasPlanId(activeChildId)
        ? this.plans.filter((plan) => sameChildId(plan.childId, activeChildId))
        : this.plans
      const saved = this.storedSelectionForUser(userId)

      return (saved && scopedPlans.find((plan) => samePlanId(plan.id, saved.planId))) || scopedPlans[0] || null
    },
    selectPlanForContext(context) {
      const plan = this.resolvePlanForContext(context)
      this.currentPlan = plan
      this.syncStatus()
      return plan
    },
    applyPlanList(plans, userId, { selectionPolicy = 'default' } = {}) {
      const normalizedPlans = Array.isArray(plans) ? plans.map(normalizePlan).filter(Boolean) : []
      this.plans = normalizedPlans
      this.loadedForUserId = userId
      this.isLoaded = true
      this.error = null

      if (!normalizedPlans.length) {
        this.currentPlan = null
        this.syncStatus()
        if (selectionPolicy !== 'none') {
          clearStoredSelection()
        }
        return null
      }

      if (selectionPolicy === 'none') {
        this.currentPlan = null
        this.syncStatus()
        return null
      }

      const saved = this.storedSelectionForUser(userId)
      const selectedPlan =
        (saved && normalizedPlans.find((plan) => samePlanId(plan.id, saved.planId))) ||
        normalizedPlans[0]

      this.currentPlan = selectedPlan
      this.syncStatus()
      saveStoredSelection(userId, selectedPlan.id)
      return selectedPlan
    },
    upsertPlan(plan) {
      const index = this.plans.findIndex((item) => samePlanId(item.id, plan?.id))
      const normalizedPlan = normalizePlan(mergePlanProjection(this.plans[index], plan))
      if (!normalizedPlan) {
        return null
      }

      if (index >= 0) {
        this.plans.splice(index, 1, normalizedPlan)
      } else {
        this.plans = [normalizedPlan, ...this.plans]
      }
      return normalizedPlan
    },
    syncTaskCount(planId, taskCount) {
      const count = Number(taskCount) || 0
      const index = this.plans.findIndex((item) => samePlanId(item.id, planId))
      if (index >= 0) {
        this.plans.splice(index, 1, {
          ...this.plans[index],
          taskCount: count,
        })
      }

      if (this.currentPlan && samePlanId(this.currentPlan.id, planId)) {
        this.currentPlan = {
          ...this.currentPlan,
          taskCount: count,
        }
        this.syncStatus()
      }
    },
    selectPlan(plan, userId = this.loadedForUserId) {
      const normalizedPlan = this.upsertPlan(plan)
      if (!normalizedPlan) {
        return null
      }

      this.currentPlan = normalizedPlan
      this.syncStatus()
      if (userId) {
        saveStoredSelection(userId, normalizedPlan.id)
      }
      return normalizedPlan
    },
    selectPlanById(id, userId = this.loadedForUserId) {
      const plan = this.plans.find((item) => samePlanId(item.id, id))
      if (!plan) {
        return null
      }

      this.currentPlan = plan
      this.syncStatus()
      if (userId) {
        saveStoredSelection(userId, plan.id)
      }
      return plan
    },
    clearInMemoryState(userId = null) {
      this.plans = []
      this.currentPlan = null
      this.status = 'draft'
      this.isLoading = false
      this.isLoaded = false
      this.error = null
      this.loadedForUserId = userId
      fetchPromise = null
      fetchPromiseUserId = null
      fetchPromiseEpoch = null
      fetchPromiseSelectionPolicy = null
    },
    async fetchPlans(userId, { force = false, selectionPolicy = 'default' } = {}) {
      if (!userId) {
        this.clearInMemoryState()
        return { plans: [], currentPlan: null }
      }

      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn || !sameUserId(requestSession.userId, userId)) {
        return { plans: [], currentPlan: null }
      }

      if (!sameUserId(this.loadedForUserId, userId)) {
        this.clearRemoteStateForUser(userId)
      }

      if (selectionPolicy === 'none') {
        this.currentPlan = null
        this.syncStatus()
      }

      if (!force && this.isLoaded && sameUserId(this.loadedForUserId, userId)) {
        if (selectionPolicy === 'none') {
          this.currentPlan = null
          this.syncStatus()
        }
        return { plans: this.plans, currentPlan: this.currentPlan }
      }

      if (
        fetchPromise
        && sameUserId(fetchPromiseUserId, userId)
        && fetchPromiseEpoch === requestSession.epoch
        && fetchPromiseSelectionPolicy === selectionPolicy
      ) {
        return fetchPromise
      }

      this.isLoading = true
      this.error = null
      fetchPromiseUserId = userId
      fetchPromiseEpoch = requestSession.epoch
      fetchPromiseSelectionPolicy = selectionPolicy
      const promise = plansApi.getPlans()
        .then((data) => {
          if (!isCurrentSession(requestSession)) {
            return { plans: this.plans, currentPlan: this.currentPlan }
          }
          const selectedPlan = this.applyPlanList(data.plans, userId, { selectionPolicy })
          return { plans: this.plans, currentPlan: selectedPlan }
        })
        .catch((error) => {
          if (isCurrentSession(requestSession)) {
            this.error = error
            this.isLoaded = false
          }
          throw error
        })
        .finally(() => {
          if (isCurrentSession(requestSession) && fetchPromise === promise) {
            this.isLoading = false
            fetchPromise = null
            fetchPromiseUserId = null
            fetchPromiseEpoch = null
            fetchPromiseSelectionPolicy = null
          }
        })

      fetchPromise = promise
      return promise
    },
    async createPlan(payload, userId = this.loadedForUserId) {
      const requestSession = getCurrentSession()
      const data = await plansApi.createPlan(payload)
      if (!isCurrentSession(requestSession)) {
        return data.plan
      }
      const plan = this.selectPlan(data.plan, userId)
      this.isLoaded = true
      this.error = null
      return plan
    },
    async updatePlan(id, payload, userId = this.loadedForUserId) {
      const requestSession = getCurrentSession()
      const data = await plansApi.updatePlan(id, payload)
      if (!isCurrentSession(requestSession)) {
        return data.plan
      }
      const plan = this.upsertPlan(data.plan)
      if (this.currentPlan && samePlanId(this.currentPlan.id, id)) {
        this.currentPlan = plan
        this.syncStatus()
      }
      if (userId && this.currentPlan && samePlanId(this.currentPlan.id, id)) {
        saveStoredSelection(userId, plan.id)
      }
      this.error = null
      return plan
    },
    async getPlan(id) {
      const data = await plansApi.getPlan(id)
      return normalizePlan(data.plan)
    },
    async startExploration(id = this.currentPlan?.id, userId = this.loadedForUserId) {
      if (!id) {
        throw { code: 'PLAN_REQUIRED', message: '请先创建探索计划' }
      }

      const requestSession = getCurrentSession()
      const data = await plansApi.startPlan(id)
      if (!isCurrentSession(requestSession)) {
        return data.plan
      }
      const plan = this.selectPlan(data.plan, userId)
      this.error = null
      return plan
    },
    async completeExploration(id = this.currentPlan?.id, userId = this.loadedForUserId) {
      if (!id) {
        throw { code: 'PLAN_REQUIRED', message: '请先创建探索计划' }
      }

      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn || !sameUserId(requestSession.userId, userId)) {
        return null
      }
      if (
        completionPromise
        && samePlanId(completionPlanId, id)
        && sameUserId(completionUserId, requestSession.userId)
        && completionEpoch === requestSession.epoch
      ) {
        return completionPromise
      }

      this.isCompleting = true
      this.completionError = null
      completionPlanId = id
      completionUserId = requestSession.userId
      completionEpoch = requestSession.epoch

      const promise = plansApi.completePlan(id)
        .then((data) => {
          const returnedPlan = data?.plan
          if (!returnedPlan || !samePlanId(returnedPlan.id, id)) {
            throw { code: 'INVALID_RESPONSE', message: '探索计划完成结果异常' }
          }

          if (!isCurrentSession(requestSession)) {
            return normalizePlan(returnedPlan)
          }

          const plan = this.upsertPlan(returnedPlan)
          if (this.currentPlan && samePlanId(this.currentPlan.id, plan.id)) {
            this.currentPlan = plan
            this.syncStatus()
            if (userId) {
              saveStoredSelection(userId, plan.id)
            }
          }
          this.completionError = null
          return plan
        })
        .catch((error) => {
          if (isCurrentSession(requestSession)) {
            this.completionError = error
          }
          throw error
        })
        .finally(() => {
          if (isCurrentSession(requestSession) && completionPromise === promise) {
            this.isCompleting = false
            completionPromise = null
            completionPlanId = null
            completionUserId = null
            completionEpoch = null
          }
        })

      completionPromise = promise
      return promise
    },
  },
})
