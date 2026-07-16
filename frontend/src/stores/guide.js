import { defineStore } from 'pinia'
import * as guidesApi from '../api/guides.js'

let ensurePromise = null
let ensurePromisePlanId = null

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
    },
    applyGuide(guide, planId) {
      const normalizedGuide = normalizeGuide(guide)
      this.currentGuide = normalizedGuide
      this.loadedForPlanId = normalizedGuide?.planId || planId
      this.error = null
      return normalizedGuide
    },
    async fetchGuide(planId) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }

      this.isLoading = true
      this.error = null
      try {
        const data = await guidesApi.getGuide(planId)
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        this.currentGuide = null
        if (error?.code !== 'GUIDE_NOT_FOUND') {
          this.error = error
        }
        throw error
      } finally {
        this.isLoading = false
      }
    },
    async generateGuide(planId) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }

      this.isGenerating = true
      this.error = null
      try {
        const data = await guidesApi.generateGuide(planId)
        return this.applyGuide(data.guide, planId)
      } catch (error) {
        this.currentGuide = null
        this.error = error
        throw error
      } finally {
        this.isGenerating = false
      }
    },
    async ensureGuide(planId) {
      if (!planId) {
        this.clearGuideForPlanChange()
        return null
      }

      if (this.currentGuide && samePlanId(this.loadedForPlanId, planId)) {
        return this.currentGuide
      }

      if (ensurePromise && samePlanId(ensurePromisePlanId, planId)) {
        return ensurePromise
      }

      this.clearGuideForPlanChange(planId)
      ensurePromisePlanId = planId
      ensurePromise = (async () => {
        try {
          return await this.fetchGuide(planId)
        } catch (error) {
          if (error?.code === 'GUIDE_NOT_FOUND') {
            return this.generateGuide(planId)
          }
          throw error
        }
      })().finally(() => {
        ensurePromise = null
        ensurePromisePlanId = null
      })

      return ensurePromise
    },
  },
})
