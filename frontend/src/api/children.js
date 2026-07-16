import request from '../utils/request'

export function getChildren() {
  return request({
    path: '/children',
    method: 'GET',
    auth: true,
  })
}

export function createChild(payload) {
  return request({
    path: '/children',
    method: 'POST',
    data: payload,
    auth: true,
  })
}

export function getChild(id) {
  return request({
    path: `/children/${id}`,
    method: 'GET',
    auth: true,
  })
}

export function updateChild(id, payload) {
  return request({
    path: `/children/${id}`,
    method: 'PATCH',
    data: payload,
    auth: true,
  })
}
