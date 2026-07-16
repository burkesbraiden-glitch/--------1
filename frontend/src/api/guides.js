import request from '../utils/request.js'

export function getGuide(planId) {
  return request({
    path: `/plans/${planId}/guide`,
    method: 'GET',
    auth: true,
  })
}

export function generateGuide(planId) {
  return request({
    path: `/plans/${planId}/guide/generate`,
    method: 'POST',
    auth: true,
  })
}
