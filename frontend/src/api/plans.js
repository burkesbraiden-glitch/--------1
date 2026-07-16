import request from '../utils/request.js'

export function createPlan(payload) {
  return request({
    path: '/plans',
    method: 'POST',
    data: payload,
    auth: true,
  })
}

export function getPlans() {
  return request({
    path: '/plans',
    method: 'GET',
    auth: true,
  })
}

export function getPlan(id) {
  return request({
    path: `/plans/${id}`,
    method: 'GET',
    auth: true,
  })
}

export function updatePlan(id, payload) {
  return request({
    path: `/plans/${id}`,
    method: 'PATCH',
    data: payload,
    auth: true,
  })
}

export function startPlan(id) {
  return request({
    path: `/plans/${id}/start`,
    method: 'POST',
    auth: true,
  })
}
