import { defineStore } from 'pinia'
import * as guidesApi from '../api/guides.js'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

let ensurePromise = null
let ensurePromisePlanId = null
let ensurePromiseSession = null
let ensurePromiseRequest = null
let guideRequestSequence = 0
let activeGuideRequest = null

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
      activeGuideRequest = null
      this.isLoading = false
      this.isGenerating = false
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
      ensurePromiseRequest = null
      activeGuideRequest = null
    },
    beginGuideRequest(planId, requestSession) {
      const request = {
        id: ++guideRequestSequence,
        planId,
        session: requestSession,
      }
      activeGuideRequest = request

      if (!samePlanId(this.loadedForPlanId, planId) || !this.currentGuide) {
        this.currentGuide = null
        this.error = null
        this.loadedForPlanId = null
      }

      return request
    },
    isCurrentGuideRequest(request) {
      return Boolean(
        request
        && activeGuideRequest?.id === request.id
        && samePlanId(activeGuideRequest.planId, request.planId)
        && activeGuideRequest.session === request.session
        && isCurrentSession(request.session),
      )
    },
    applyGuide(guide, planId) {
      const normalizedGuide = normalizeGuide(guide)
      this.currentGuide = normalizedGuide
      this.loadedForPlanId = normalizedGuide?.planId || planId
      this.error = null
      return normalizedGuide
    },
    async fetchGuide(planId, requestSession = getCurrentSession(), request = null) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }
      if (!isCurrentSession(requestSession)) {
        return null
      }

      const guideRequest = request || this.beginGuideRequest(planId, requestSession)
      if (!this.isCurrentGuideRequest(guideRequest)) {
        return null
      }

      this.isLoading = true
      this.isGenerating = false
      this.error = null
      try {
        const data = await guidesApi.getGuide(planId)
        if (!this.isCurrentGuideRequest(guideRequest)) {
          return null
        }
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        if (this.isCurrentGuideRequest(guideRequest)) {
          this.currentGuide = null
          if (error?.code !== 'GUIDE_NOT_FOUND') {
            this.error = error
          }
        } else {
          return null
        }
        throw error
      } finally {
        if (this.isCurrentGuideRequest(guideRequest)) {
          this.isLoading = false
        }
      }
    },
    async generateGuide(planId, requestSession = getCurrentSession(), request = null) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }
      if (!isCurrentSession(requestSession)) {
        return null
      }

      const guideRequest = request || this.beginGuideRequest(planId, requestSession)
      if (!this.isCurrentGuideRequest(guideRequest)) {
        return null
      }

      this.isLoading = false
      this.isGenerating = true
      this.error = null
      try {
        const data = await guidesApi.generateGuide(planId)
        if (!this.isCurrentGuideRequest(guideRequest)) {
          return null
        }
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        if (this.isCurrentGuideRequest(guideRequest)) {
          this.currentGuide = null
          this.error = error
        } else {
          return null
        }
        throw error
      } finally {
        if (this.isCurrentGuideRequest(guideRequest)) {
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
      const guideRequest = this.beginGuideRequest(planId, requestSession)
      ensurePromisePlanId = planId
      ensurePromiseSession = requestSession
      ensurePromiseRequest = guideRequest
      ensurePromise = (async () => {
        try {
          const guide = await this.fetchGuide(planId, requestSession, guideRequest)
          if (!this.isCurrentGuideRequest(guideRequest) || guide) {
            return guide
          }
          return null
        } catch (error) {
          if (error?.code === 'GUIDE_NOT_FOUND' && this.isCurrentGuideRequest(guideRequest)) {
            return this.generateGuide(planId, requestSession, guideRequest)
          }
          if (!this.isCurrentGuideRequest(guideRequest)) {
            return null
          }
          throw error
        }
      })().finally(() => {
        if (ensurePromiseRequest === guideRequest) {
          ensurePromise = null
          ensurePromisePlanId = null
          ensurePromiseSession = null
          ensurePromiseRequest = null
        }
      })

      return ensurePromise
    },
  },
})
