import request from '../utils/request.js'
import { downloadAuthenticatedFile, uploadAuthenticatedFile } from '../utils/authenticatedFile.js'

export function getTasks(planId) {
  return request({
    path: `/plans/${planId}/tasks`,
    method: 'GET',
    auth: true,
  })
}

export function generateTasks(planId) {
  return request({
    path: `/plans/${planId}/tasks/generate`,
    method: 'POST',
    auth: true,
  })
}

export function getTask(planId, taskId) {
  return request({
    path: `/plans/${planId}/tasks/${taskId}`,
    method: 'GET',
    auth: true,
  })
}

export function startTaskSubmission(planId, taskId) {
  return request({
    path: `/plans/${planId}/tasks/${taskId}/submission/start`,
    method: 'POST',
    auth: true,
  })
}

export function updateTaskSubmission(planId, taskId, payload) {
  return request({
    path: `/plans/${planId}/tasks/${taskId}/submission`,
    method: 'PATCH',
    data: payload,
    auth: true,
  })
}

export function completeTaskSubmission(planId, taskId, payload) {
  return request({
    path: `/plans/${planId}/tasks/${taskId}/submission/complete`,
    method: 'POST',
    data: payload,
    auth: true,
  })
}

export function uploadTaskImage(planId, taskId, filePath) {
  return uploadAuthenticatedFile(`/plans/${planId}/tasks/${taskId}/submission/image`, filePath)
}

export function downloadTaskImage(planId, taskId, imageUrl) {
  const path = imageUrl || `/plans/${planId}/tasks/${taskId}/submission/image`
  return downloadAuthenticatedFile(path)
}
