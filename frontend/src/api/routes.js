import request from '../utils/request.js'

function routesPath(params = {}) {
  const query = []
  if (params.limit !== undefined && params.limit !== null) {
    query.push(`limit=${encodeURIComponent(params.limit)}`)
  }
  if (params.offset !== undefined && params.offset !== null) {
    query.push(`offset=${encodeURIComponent(params.offset)}`)
  }
  return query.length ? `/routes?${query.join('&')}` : '/routes'
}

export function getRoutes(params = {}) {
  return request({
    path: routesPath(params),
    method: 'GET',
    auth: true,
  })
}

export function createRoute(payload) {
  return request({ path: '/routes', method: 'POST', data: payload, auth: true })
}

export function getRoute(routeId) {
  return request({ path: `/routes/${routeId}`, method: 'GET', auth: true })
}

export function updateRoute(routeId, payload) {
  return request({ path: `/routes/${routeId}`, method: 'PATCH', data: payload, auth: true })
}

export function deleteRoute(routeId) {
  return request({ path: `/routes/${routeId}`, method: 'DELETE', auth: true })
}

export function createRouteDay(routeId, payload) {
  return request({ path: `/routes/${routeId}/days`, method: 'POST', data: payload, auth: true })
}

export function updateRouteDay(routeId, dayId, payload) {
  return request({ path: `/routes/${routeId}/days/${dayId}`, method: 'PATCH', data: payload, auth: true })
}

export function deleteRouteDay(routeId, dayId) {
  return request({ path: `/routes/${routeId}/days/${dayId}`, method: 'DELETE', auth: true })
}

export function reorderRouteDays(routeId, dayIds) {
  return request({ path: `/routes/${routeId}/days/reorder`, method: 'PATCH', data: { dayIds }, auth: true })
}

export function createRouteStop(routeId, dayId, payload) {
  return request({ path: `/routes/${routeId}/days/${dayId}/stops`, method: 'POST', data: payload, auth: true })
}

export function updateRouteStop(routeId, dayId, stopId, payload) {
  return request({ path: `/routes/${routeId}/days/${dayId}/stops/${stopId}`, method: 'PATCH', data: payload, auth: true })
}

export function deleteRouteStop(routeId, dayId, stopId) {
  return request({ path: `/routes/${routeId}/days/${dayId}/stops/${stopId}`, method: 'DELETE', auth: true })
}

export function reorderRouteStops(routeId, dayId, stopIds) {
  return request({ path: `/routes/${routeId}/days/${dayId}/stops/reorder`, method: 'PATCH', data: { stopIds }, auth: true })
}
