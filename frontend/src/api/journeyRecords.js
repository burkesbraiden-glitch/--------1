import request from '../utils/request.js'

export function fetchJourneyRecords(params = {}) {
  return request({
    path: '/journey-records',
    method: 'GET',
    data: params,
    auth: true,
  })
}

export function fetchJourneyRecord(planId) {
  return request({
    path: `/plans/${planId}/journey-record`,
    method: 'GET',
    auth: true,
  })
}

export function createJourneyRecord(planId) {
  return request({
    path: `/plans/${planId}/journey-record`,
    method: 'POST',
    auth: true,
  })
}

export function updateJourneyRecord(planId, payload) {
  return request({
    path: `/plans/${planId}/journey-record`,
    method: 'PATCH',
    data: payload,
    auth: true,
  })
}

export function finalizeJourneyRecord(planId) {
  return request({
    path: `/plans/${planId}/journey-record/finalize`,
    method: 'POST',
    auth: true,
  })
}
