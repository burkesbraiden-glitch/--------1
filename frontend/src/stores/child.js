import { defineStore } from 'pinia'
import * as childrenApi from '../api/children'

const FALLBACK_CHILD = {
  name: '小小探索家',
  age: 7,
  city: '北京',
  ageGroup: '7-12',
  interests: ['历史故事', '古建筑', '观察探索'],
}

let fetchPromise = null
let fetchPromiseUserId = null

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

function ageGroupForAge(age) {
  return age >= 3 && age <= 6 ? '3-6' : '7-12'
}

export const useChildStore = defineStore('child', {
  state: () => ({
    children: [],
    currentChild: { ...FALLBACK_CHILD },
    ageGroup: FALLBACK_CHILD.ageGroup,
    interests: [...FALLBACK_CHILD.interests],
    isLoading: false,
    isLoaded: false,
    error: null,
    loadedForUserId: null,
    hasRemoteChild: false,
  }),
  actions: {
    syncCompatibleFields(child) {
      const displayChild = child || FALLBACK_CHILD
      this.currentChild = {
        ...displayChild,
        city: displayChild.city || '',
      }
      this.ageGroup = displayChild.ageGroup || ageGroupForAge(displayChild.age)
      this.interests = Array.isArray(displayChild.interests) ? [...displayChild.interests] : []
    },
    clearRemoteStateForUser(userId = null) {
      this.children = []
      this.hasRemoteChild = false
      this.loadedForUserId = userId
      this.syncCompatibleFields(null)
    },
    applyChildrenPayload(data, userId) {
      const children = Array.isArray(data.children) ? data.children.map(normalizeChild) : []
      const currentChild = normalizeChild(data.currentChild)

      this.children = children
      this.hasRemoteChild = Boolean(currentChild)
      this.loadedForUserId = userId
      this.isLoaded = true
      this.error = null
      this.syncCompatibleFields(currentChild)
    },
    async fetchChildren(userId) {
      if (!userId) {
        this.resetSessionState()
        return null
      }

      if (this.loadedForUserId !== userId) {
        this.clearRemoteStateForUser(userId)
        this.isLoaded = false
      }

      if (fetchPromise && fetchPromiseUserId === userId) {
        return fetchPromise
      }

      this.isLoading = true
      this.error = null
      fetchPromiseUserId = userId
      fetchPromise = childrenApi.getChildren()
        .then((data) => {
          this.applyChildrenPayload(data, userId)
          return data
        })
        .catch((error) => {
          this.error = error
          this.isLoaded = false
          throw error
        })
        .finally(() => {
          this.isLoading = false
          fetchPromise = null
          fetchPromiseUserId = null
        })

      return fetchPromise
    },
    applySavedChild(child) {
      const savedChild = normalizeChild(child)
      const index = this.children.findIndex((item) => item.id === savedChild.id)

      if (index >= 0) {
        this.children.splice(index, 1, savedChild)
      } else {
        this.children = [...this.children, savedChild]
      }

      if (savedChild.isDefault || !this.hasRemoteChild || this.currentChild.id === savedChild.id) {
        this.hasRemoteChild = true
        this.syncCompatibleFields(savedChild)
      }

      this.error = null
      this.isLoaded = true
      return savedChild
    },
    async createChild(payload) {
      const data = await childrenApi.createChild(payload)
      return this.applySavedChild(data.child)
    },
    async updateChild(id, payload) {
      const data = await childrenApi.updateChild(id, payload)
      return this.applySavedChild(data.child)
    },
    setAgeGroup(ageGroup) {
      if (['3-6', '7-12'].includes(ageGroup)) {
        this.ageGroup = ageGroup
      }
    },
    resetSessionState() {
      this.children = []
      this.currentChild = { ...FALLBACK_CHILD }
      this.ageGroup = FALLBACK_CHILD.ageGroup
      this.interests = [...FALLBACK_CHILD.interests]
      this.isLoading = false
      this.isLoaded = false
      this.error = null
      this.loadedForUserId = null
      this.hasRemoteChild = false
      fetchPromise = null
      fetchPromiseUserId = null
    },
  },
})
