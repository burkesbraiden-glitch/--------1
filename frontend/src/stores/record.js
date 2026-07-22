import { defineStore } from 'pinia'
import { fetchJourneyRecords } from '../api/journeyRecords.js'
import { downloadAuthenticatedFile } from '../utils/authenticatedFile.js'

let activeLoadPromise = null

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeCount(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : 0
}

function displayDate(value) {
  const date = normalizeText(value)
  return /^\d{4}-\d{2}-\d{2}/.test(date) ? date.slice(0, 10) : ''
}

function coverResourceKey(record) {
  return record?.id && record?.coverImageUrl ? `${record.id}:${record.coverImageUrl}` : ''
}

function mapJourneyRecord(record, coverResources) {
  const coverKey = coverResourceKey(record)
  const coverResource = coverKey ? coverResources[coverKey] : null

  return {
    id: record?.id ?? null,
    planId: record?.planId ?? null,
    childId: record?.childId ?? null,
    title: normalizeText(record?.title),
    customTitle: normalizeText(record?.customTitle),
    displayTitle: normalizeText(record?.displayTitle) || normalizeText(record?.title),
    destination: normalizeText(record?.destination),
    planStatus: normalizeText(record?.planStatus),
    status: normalizeText(record?.status),
    summary: normalizeText(record?.summary),
    coverSubmissionId: record?.coverSubmissionId ?? null,
    coverImageUrl: normalizeText(record?.coverImageUrl),
    taskCount: normalizeCount(record?.taskCount),
    completedTaskCount: normalizeCount(record?.completedTaskCount),
    photoCount: normalizeCount(record?.photoCount),
    noteCount: normalizeCount(record?.noteCount),
    finalizedAt: record?.finalizedAt || null,
    createdAt: record?.createdAt || null,
    updatedAt: record?.updatedAt || null,
    displayCoverImage: coverResource?.displayPath || '',
    displayUpdatedAt: displayDate(record?.updatedAt),
  }
}

export const useRecordStore = defineStore('record', {
  state: () => ({
    records: [],
    total: 0,
    limit: 20,
    offset: 0,
    loading: false,
    error: null,
    hasLoaded: false,
    latestRequestId: 0,
    lastQuery: { limit: 20, offset: 0 },
    coverResources: {},
  }),
  getters: {
    learningRecordCount(state) {
      const total = Number(state.total)
      if (Number.isFinite(total) && total >= 0) {
        return total
      }
      return Array.isArray(state.records) ? state.records.length : 0
    },
  },
  actions: {
    cleanupCoverResource(key) {
      const resource = this.coverResources[key]
      if (resource?.cleanup) {
        resource.cleanup()
      }
      delete this.coverResources[key]
    },
    cleanupUnusedCoverResources(records) {
      const activeKeys = new Set(records.map(coverResourceKey).filter(Boolean))
      Object.keys(this.coverResources).forEach((key) => {
        if (!activeKeys.has(key)) {
          this.cleanupCoverResource(key)
        }
      })
    },
    async loadRecordCover(record, requestId) {
      const key = coverResourceKey(record)
      if (!key) {
        return mapJourneyRecord(record, this.coverResources)
      }

      if (!this.coverResources[key]) {
        try {
          const resource = await downloadAuthenticatedFile(record.coverImageUrl)
          if (this.latestRequestId !== requestId) {
            resource?.cleanup?.()
            return mapJourneyRecord(record, this.coverResources)
          }
          this.coverResources[key] = {
            sourceUrl: record.coverImageUrl,
            displayPath: resource?.displayPath || '',
            cleanup: resource?.cleanup || null,
          }
        } catch (error) {
          return mapJourneyRecord(record, this.coverResources)
        }
      }

      return mapJourneyRecord(record, this.coverResources)
    },
    loadJourneyRecords(params = {}) {
      if (activeLoadPromise) {
        return activeLoadPromise
      }

      const requestId = this.latestRequestId + 1
      const query = {
        limit: Number(params.limit) || 20,
        offset: Number(params.offset) || 0,
      }
      if (Number.isInteger(params.childId) && params.childId > 0) {
        query.childId = params.childId
      }
      if (params.status === 'draft' || params.status === 'finalized') {
        query.status = params.status
      }

      this.latestRequestId = requestId
      this.lastQuery = { ...query }
      this.loading = true
      this.error = null

      const promise = fetchJourneyRecords(query)
        .then(async (data) => {
          if (this.latestRequestId !== requestId) {
            return this.records
          }
          if (!Array.isArray(data?.items)) {
            throw { code: 'INVALID_RESPONSE', message: '旅行记录数据格式异常' }
          }

          const records = await Promise.all(data.items.map((record) => this.loadRecordCover(record, requestId)))
          if (this.latestRequestId !== requestId) {
            return this.records
          }

          this.cleanupUnusedCoverResources(data.items)
          this.records = records
          this.total = normalizeCount(data.total)
          this.limit = normalizeCount(data.limit) || query.limit
          this.offset = normalizeCount(data.offset)
          this.hasLoaded = true
          this.error = null
          return records
        })
        .catch((error) => {
          if (this.latestRequestId === requestId) {
            this.error = error
            this.hasLoaded = true
          }
          throw error
        })
        .finally(() => {
          if (this.latestRequestId === requestId) {
            this.loading = false
          }
          if (activeLoadPromise === promise) {
            activeLoadPromise = null
          }
        })

      activeLoadPromise = promise
      return promise
    },
    retryJourneyRecords() {
      return this.loadJourneyRecords(this.lastQuery)
    },
    resetRecordState() {
      this.latestRequestId += 1
      Object.keys(this.coverResources).forEach((key) => this.cleanupCoverResource(key))
      this.records = []
      this.total = 0
      this.limit = 20
      this.offset = 0
      this.loading = false
      this.error = null
      this.hasLoaded = false
      this.lastQuery = { limit: 20, offset: 0 }
      activeLoadPromise = null
    },
  },
})
