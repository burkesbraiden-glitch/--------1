import request from '../utils/request.js'

export function sendCode(phone) {
  return request({
    path: '/auth/send-code',
    method: 'POST',
    data: { phone },
  })
}

export function login(phone, code) {
  return request({
    path: '/auth/login',
    method: 'POST',
    data: { phone, code },
  })
}

export function mockWechatLogin(mockCode) {
  return request({
    path: '/auth/mock-wechat-login',
    method: 'POST',
    data: { mockCode },
  })
}

export function getMe() {
  return request({
    path: '/auth/me',
    method: 'GET',
    auth: true,
  })
}

export function logout() {
  return request({
    path: '/auth/logout',
    method: 'POST',
    auth: true,
  })
}
