import { defineStore } from 'pinia'
import * as routesApi from '../api/routes.js'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

const DEFAULT_LIMIT = 20
let fetchPromise = null
let fetchPromiseUserId = null
let fetchPromiseEpoch = null

function sameRouteId(left, right) {
  return String(left) === String(right)
}

function sameUserId(left, right) {
  return String(left) === String(right)
}

function comparePosition(field) {
  return (left, right) => {
    const leftPosition = Number(left?.[field]) || 0
    const rightPosition = Number(right?.[field]) || 0
    if (leftPosition !== rightPosition) return leftPosition - rightPosition
    return (Number(left?.id) || 0) - (Number(right?.id) || 0)
  }
}

function normalizeRoute(route) {
  if (!route) return null

  const days = (Array.isArray(route.days) ? route.days : [])
    .map((day) => ({
      ...day,
      stops: (Array.isArray(day?.stops) ? day.stops : [])
        .map((stop) => ({ ...stop }))
        .sort(comparePosition('sortOrder')),
    }))
    .sort(comparePosition('dayNumber'))

  return { ...route, days }
}

function normalizeRouteList(items) {
  return Array.isArray(items) ? items.map(normalizeRoute).filter(Boolean) : []
}

export const useRouteStore = defineStore('route', {
  state: () => ({
    routes: [],
    currentRoute: null,
    isLoading: false,
    error: null,
    isLoaded: false,
    loadedForUserId: null,
    total: 0,
    limit: DEFAULT_LIMIT,
    offset: 0,
  }),
  actions: {
    clearRemoteStateForUser(userId = null) {
      this.routes = []
      this.currentRoute = null
      this.isLoading = false
      this.error = null
      this.isLoaded = false
      this.loadedForUserId = userId
      this.total = 0
      this.limit = DEFAULT_LIMIT
      this.offset = 0
    },
    resetSessionState() {
      this.clearRemoteStateForUser()
      fetchPromise = null
      fetchPromiseUserId = null
      fetchPromiseEpoch = null
    },
    upsertRoute(route) {
      const normalizedRoute = normalizeRoute(route)
      if (!normalizedRoute) return null

      const index = this.routes.findIndex((item) => sameRouteId(item.id, normalizedRoute.id))
      if (index >= 0) {
        this.routes.splice(index, 1, normalizedRoute)
      } else {
        this.routes = [normalizedRoute, ...this.routes]
      }
      return normalizedRoute
    },
    applyRouteList(items, userId, { total = 0, limit = DEFAULT_LIMIT, offset = 0 } = {}) {
      this.routes = normalizeRouteList(items)
      this.loadedForUserId = userId
      this.isLoaded = true
      this.error = null
      this.total = Number(total) || 0
      this.limit = Number(limit) || DEFAULT_LIMIT
      this.offset = Number(offset) || 0

      if (this.currentRoute) {
        const matchingRoute = this.routes.find((route) => sameRouteId(route.id, this.currentRoute.id))
        this.currentRoute = matchingRoute || null
      }
      return this.routes
    },
    applyReturnedRoute(route) {
      const normalizedRoute = this.upsertRoute(route)
      if (!normalizedRoute) return null
      this.currentRoute = normalizedRoute
      this.error = null
      return normalizedRoute
    },
    async fetchRoutes(userId, { force = false, limit = DEFAULT_LIMIT, offset = 0 } = {}) {
      if (!userId) {
        this.clearRemoteStateForUser()
        return { routes: [], total: 0, limit, offset }
      }

      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn || !sameUserId(requestSession.userId, userId)) {
        return { routes: [], total: 0, limit, offset }
      }

      if (!sameUserId(this.loadedForUserId, userId)) {
        this.clearRemoteStateForUser(userId)
      }

      if (!force && this.isLoaded && sameUserId(this.loadedForUserId, userId)) {
        return { routes: this.routes, total: this.total, limit: this.limit, offset: this.offset }
      }

      if (
        fetchPromise
        && sameUserId(fetchPromiseUserId, userId)
        && fetchPromiseEpoch === requestSession.epoch
      ) {
        return fetchPromise
      }

      this.isLoading = true
      this.error = null
      fetchPromiseUserId = userId
      fetchPromiseEpoch = requestSession.epoch
      const promise = routesApi.getRoutes({ limit, offset })
        .then((data) => {
          const result = {
            routes: normalizeRouteList(data?.items),
            total: Number(data?.total) || 0,
            limit: Number(data?.limit) || limit,
            offset: Number(data?.offset) || offset,
          }
          if (!isCurrentSession(requestSession)) return result
          this.applyRouteList(result.routes, userId, result)
          return { routes: this.routes, total: this.total, limit: this.limit, offset: this.offset }
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
    async fetchRoute(routeId) {
      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn) return null

      this.isLoading = true
      this.error = null
      try {
        const data = await routesApi.getRoute(routeId)
        const route = normalizeRoute(data?.route)
        if (isCurrentSession(requestSession)) this.applyReturnedRoute(route)
        return route
      } catch (error) {
        if (isCurrentSession(requestSession)) this.error = error
        throw error
      } finally {
        if (isCurrentSession(requestSession)) this.isLoading = false
      }
    },
    async createRoute(payload) {
      const requestSession = getCurrentSession()
      try {
        const data = await routesApi.createRoute(payload)
        const route = normalizeRoute(data?.route)
        if (isCurrentSession(requestSession)) {
          this.applyReturnedRoute(route)
          this.isLoaded = true
          this.loadedForUserId = requestSession.userId
        }
        return route
      } catch (error) {
        if (isCurrentSession(requestSession)) this.error = error
        throw error
      }
    },
    async updateRoute(routeId, payload) {
      return this.applyRouteMutation(() => routesApi.updateRoute(routeId, payload))
    },
    async deleteRoute(routeId) {
      const requestSession = getCurrentSession()
      try {
        await routesApi.deleteRoute(routeId)
        if (isCurrentSession(requestSession)) {
          this.routes = this.routes.filter((route) => !sameRouteId(route.id, routeId))
          if (this.currentRoute && sameRouteId(this.currentRoute.id, routeId)) this.currentRoute = null
          this.total = Math.max(0, this.total - 1)
          this.error = null
        }
      } catch (error) {
        if (isCurrentSession(requestSession)) this.error = error
        throw error
      }
    },
    async createDay(routeId, payload) {
      return this.applyRouteMutation(() => routesApi.createRouteDay(routeId, payload))
    },
    async updateDay(routeId, dayId, payload) {
      return this.applyRouteMutation(() => routesApi.updateRouteDay(routeId, dayId, payload))
    },
    async deleteDay(routeId, dayId) {
      return this.applyRouteMutation(() => routesApi.deleteRouteDay(routeId, dayId))
    },
    async reorderDays(routeId, dayIds) {
      return this.applyRouteMutation(() => routesApi.reorderRouteDays(routeId, dayIds))
    },
    async createStop(routeId, dayId, payload) {
      return this.applyRouteMutation(() => routesApi.createRouteStop(routeId, dayId, payload))
    },
    async updateStop(routeId, dayId, stopId, payload) {
      return this.applyRouteMutation(() => routesApi.updateRouteStop(routeId, dayId, stopId, payload))
    },
    async deleteStop(routeId, dayId, stopId) {
      return this.applyRouteMutation(() => routesApi.deleteRouteStop(routeId, dayId, stopId))
    },
    async reorderStops(routeId, dayId, stopIds) {
      return this.applyRouteMutation(() => routesApi.reorderRouteStops(routeId, dayId, stopIds))
    },
    async applyRouteMutation(requestAction) {
      const requestSession = getCurrentSession()
      try {
        const data = await requestAction()
        const route = normalizeRoute(data?.route)
        if (isCurrentSession(requestSession)) this.applyReturnedRoute(route)
        return route
      } catch (error) {
        if (isCurrentSession(requestSession)) this.error = error
        throw error
      }
    },
  },
})
