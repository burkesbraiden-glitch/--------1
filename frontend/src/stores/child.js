import { defineStore } from 'pinia'
import * as childrenApi from '../api/children'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

let fetchPromise = null
let fetchPromiseUserId = null
let fetchPromiseEpoch = null

function normalizeChild(child) {
  if (!child) {
    return null
  }

  return {
    ...child,
    city: child.city || '',
    interests: Array.isArray(child.interests) ? child.interests : [],
  }
}

function normalizeChildId(value) {
  if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
    return null
  }
  return value
}

function sameUserId(left, right) {
  return left !== null
    && left !== undefined
    && right !== null
    && right !== undefined
    && String(left) === String(right)
}

function findChildById(children, childId) {
  const normalizedChildId = normalizeChildId(childId)
  if (!normalizedChildId || !Array.isArray(children)) {
    return null
  }

  return children.find((child) => normalizeChildId(child?.id) === normalizedChildId) || null
}

export const useChildStore = defineStore('child', {
  state: () => ({
    children: [],
    currentChild: null,
    activeChildId: null,
    isLoading: false,
    isLoaded: false,
    error: null,
    loadedForUserId: null,
    hasRemoteChild: false,
  }),
  getters: {
    activeChild(state) {
      return findChildById(state.children, state.activeChildId)
    },
  },
  actions: {
    syncCurrentChild(child) {
      this.currentChild = child
        ? {
            ...child,
            city: child.city || '',
          }
        : null
    },
    clearRemoteStateForUser(userId = null) {
      this.children = []
      this.activeChildId = null
      this.hasRemoteChild = false
      this.loadedForUserId = userId
      this.syncCurrentChild(null)
    },
    resolveActiveChildId(children, backendCurrentChild, userId, previousActiveChildId = this.activeChildId) {
      const currentSession = getCurrentSession()
      const belongsToCurrentSession = currentSession.isLoggedIn && sameUserId(currentSession.userId, userId)
      const previousActiveChild = belongsToCurrentSession
        ? findChildById(children, previousActiveChildId)
        : null

      if (previousActiveChild) {
        return previousActiveChild.id
      }

      return findChildById(children, backendCurrentChild?.id)?.id || null
    },
    applyChildrenPayload(data, userId) {
      const children = Array.isArray(data.children) ? data.children.map(normalizeChild) : []
      const backendCurrentChild = normalizeChild(data.currentChild)
      const activeChildId = this.resolveActiveChildId(children, backendCurrentChild, userId)

      this.children = children
      this.activeChildId = activeChildId
      this.hasRemoteChild = Boolean(backendCurrentChild)
      this.loadedForUserId = userId
      this.isLoaded = true
      this.error = null
      this.syncCurrentChild(backendCurrentChild)
    },
    async fetchChildren(userId) {
      if (!userId) {
        this.resetSessionState()
        return null
      }

      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn || String(requestSession.userId) !== String(userId)) {
        return null
      }

      if (this.loadedForUserId !== userId) {
        this.clearRemoteStateForUser(userId)
        this.isLoaded = false
      }

      if (
        fetchPromise
        && fetchPromiseUserId === userId
        && fetchPromiseEpoch === requestSession.epoch
      ) {
        return fetchPromise
      }

      this.isLoading = true
      this.error = null
      fetchPromiseUserId = userId
      fetchPromiseEpoch = requestSession.epoch
      const promise = childrenApi.getChildren()
        .then((data) => {
          if (isCurrentSession(requestSession)) {
            this.applyChildrenPayload(data, userId)
          }
          return data
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
          }
        })

      fetchPromise = promise
      return promise
    },
    applySavedChild(child, userId = this.loadedForUserId) {
      const savedChild = normalizeChild(child)
      const index = this.children.findIndex((item) => item.id === savedChild.id)

      if (index >= 0) {
        this.children.splice(index, 1, savedChild)
      } else {
        this.children = [...this.children, savedChild]
      }

      if (savedChild.isDefault || !this.hasRemoteChild || this.currentChild?.id === savedChild.id) {
        this.hasRemoteChild = true
        this.syncCurrentChild(savedChild)
      }

      this.activeChildId = this.resolveActiveChildId(this.children, this.currentChild, userId)
      this.loadedForUserId = userId
      this.error = null
      this.isLoaded = true
      return savedChild
    },
    async createChild(payload) {
      const requestSession = getCurrentSession()
      const data = await childrenApi.createChild(payload)
      return isCurrentSession(requestSession) ? this.applySavedChild(data.child, requestSession.userId) : data.child
    },
    async updateChild(id, payload) {
      const requestSession = getCurrentSession()
      const data = await childrenApi.updateChild(id, payload)
      return isCurrentSession(requestSession) ? this.applySavedChild(data.child, requestSession.userId) : data.child
    },
    setActiveChild(childId) {
      const currentSession = getCurrentSession()
      const child = findChildById(this.children, childId)
      if (
        !child
        || !this.isLoaded
        || !this.hasRemoteChild
        || !currentSession.isLoggedIn
        || !sameUserId(this.loadedForUserId, currentSession.userId)
      ) {
        return false
      }

      this.activeChildId = child.id
      return true
    },
    resetSessionState() {
      this.children = []
      this.currentChild = null
      this.activeChildId = null
      this.isLoading = false
      this.isLoaded = false
      this.error = null
      this.loadedForUserId = null
      this.hasRemoteChild = false
      fetchPromise = null
      fetchPromiseUserId = null
      fetchPromiseEpoch = null
    },
  },
})
