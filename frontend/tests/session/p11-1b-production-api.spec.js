import { describe, expect, test } from 'vitest'
import { validateApiBaseUrl } from '../../src/config/apiBaseUrl.js'

const production = { DEV: false, PROD: true }
const development = { DEV: true, PROD: false }

describe('P11.1b production API configuration', () => {
  test.each([undefined, '', '   '])('rejects a missing production API URL: %j', (baseUrl) => {
    expect(() => validateApiBaseUrl(baseUrl, production)).toThrow('Missing VITE_API_BASE_URL for production.')
  })

  test.each([
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://api.example.test',
    '/api/v1',
  ])('rejects an invalid production API URL: %s', (baseUrl) => {
    expect(() => validateApiBaseUrl(baseUrl, production)).toThrow(
      'Production VITE_API_BASE_URL must be an absolute HTTPS URL.',
    )
  })

  test('accepts an HTTPS production API URL and removes trailing slashes', () => {
    expect(validateApiBaseUrl('https://api.example.test/api/v1///', production)).toBe(
      'https://api.example.test/api/v1',
    )
  })

  test('keeps a development localhost API URL available', () => {
    expect(validateApiBaseUrl('http://127.0.0.1:5000/api/v1', development)).toBe(
      'http://127.0.0.1:5000/api/v1',
    )
  })
})
