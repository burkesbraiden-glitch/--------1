import request from '../utils/request.js'

export function exportAccountData() {
  return request({
    path: '/account/export',
    method: 'GET',
    auth: true,
  })
}

export function deleteAccount() {
  return request({
    path: '/account',
    method: 'DELETE',
    auth: true,
  })
}
