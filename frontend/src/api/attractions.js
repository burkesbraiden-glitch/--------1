import request from '../utils/request.js'

function attractionsPath(params = {}) {
  const query = []
  for (const field of ['city', 'keyword', 'limit', 'offset']) {
    const value = params[field]
    if (value !== undefined && value !== null && value !== '') {
      query.push(`${field}=${encodeURIComponent(value)}`)
    }
  }
  return query.length ? `/attractions?${query.join('&')}` : '/attractions'
}

export function getAttractions(params = {}) {
  return request({
    path: attractionsPath(params),
    method: 'GET',
    auth: true,
  })
}

export function getAttractionDetail(id) {
  return request({
    path: `/attractions/${encodeURIComponent(String(id))}`,
    method: 'GET',
    auth: true,
  })
}

export function getAttractionGuide(id) {
  return request({
    path: `/attractions/${encodeURIComponent(String(id))}/guide`,
    method: 'GET',
    auth: true,
  })
}
