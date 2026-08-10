import { defineStore } from 'pinia'
import * as guidesApi from '../api/guides.js'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

let ensurePromise = null
let ensurePromisePlanId = null
let ensurePromiseSession = null

function samePlanId(left, right) {
  return String(left) === String(right)
}

function normalizeGuide(guide) {
  if (!guide) {
    return null
  }

  return {
    ...guide,
    childIntro: Array.isArray(guide.childIntro) ? guide.childIntro : [],
    questions: Array.isArray(guide.questions) ? guide.questions : [],
    focusItems: Array.isArray(guide.focusItems) ? guide.focusItems : [],
    audioUrl: guide.audioUrl || null,
  }
}

export const useGuideStore = defineStore('guide', {
  state: () => ({
    currentGuide: null,
    isLoading: false,
    isGenerating: false,
    error: null,
    loadedForPlanId: null,
  }),
  actions: {
    clearGuideForPlanChange(planId = null) {
      if (planId && samePlanId(this.loadedForPlanId, planId) && this.currentGuide) {
        return
      }
      this.currentGuide = null
      this.error = null
      this.loadedForPlanId = null
    },
    resetSessionState() {
      this.currentGuide = null
      this.isLoading = false
      this.isGenerating = false
      this.error = null
      this.loadedForPlanId = null
      ensurePromise = null
      ensurePromisePlanId = null
      ensurePromiseSession = null
    },
    applyGuide(guide, planId) {
      const normalizedGuide = normalizeGuide(guide)
      this.currentGuide = normalizedGuide
      this.loadedForPlanId = normalizedGuide?.planId || planId
      this.error = null
      return normalizedGuide
    },
    async fetchGuide(planId, requestSession = getCurrentSession()) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }
      if (!isCurrentSession(requestSession)) {
        return null
      }

      this.isLoading = true
      this.error = null
      try {
        const data = await guidesApi.getGuide(planId)
        if (!isCurrentSession(requestSession)) {
          return null
        }
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        if (isCurrentSession(requestSession)) {
          this.currentGuide = null
          if (error?.code !== 'GUIDE_NOT_FOUND') {
            this.error = error
          }
        } else {
          return null
        }
        throw error
      } finally {
        if (isCurrentSession(requestSession)) {
          this.isLoading = false
        }
      }
    },
    async generateGuide(planId, requestSession = getCurrentSession()) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }
      if (!isCurrentSession(requestSession)) {
        return null
      }

      this.isGenerating = true
      this.error = null
      try {
        const data = await guidesApi.generateGuide(planId)
        if (!isCurrentSession(requestSession)) {
          return null
        }
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        if (isCurrentSession(requestSession)) {
          this.currentGuide = null
          this.error = error
        } else {
          return null
        }
        throw error
      } finally {
        if (isCurrentSession(requestSession)) {
          this.isGenerating = false
        }
      }
    },
    async ensureGuide(planId) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }

      const requestSession = getCurrentSession()
      if (!isCurrentSession(requestSession)) {
        return null
      }

      if (this.currentGuide && samePlanId(this.loadedForPlanId, planId)) {
        return this.currentGuide
      }

      if (
        ensurePromise
        && samePlanId(ensurePromisePlanId, planId)
        && ensurePromiseSession?.epoch === requestSession.epoch
        && String(ensurePromiseSession?.userId) === String(requestSession.userId)
      ) {
        return ensurePromise
      }

      this.clearGuideForPlanChange(planId)
      ensurePromisePlanId = planId
      ensurePromiseSession = requestSession
      ensurePromise = (async () => {
        try {
          const guide = await this.fetchGuide(planId, requestSession)
          if (!isCurrentSession(requestSession) || guide) {
            return guide
          }
          return null
        } catch (error) {
          if (error?.code === 'GUIDE_NOT_FOUND' && isCurrentSession(requestSession)) {
            return this.generateGuide(planId, requestSession)
          }
          throw error
        }
      })().finally(() => {
        if (isCurrentSession(requestSession) && ensurePromiseSession === requestSession) {
          ensurePromise = null
          ensurePromisePlanId = null
          ensurePromiseSession = null
        }
      })

      return ensurePromise
    },
  },
})
