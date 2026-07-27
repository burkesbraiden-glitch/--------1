import { defineStore } from 'pinia'
import { fetchJourneyRecords, fetchJourneyRecord, updateJourneyRecord, finalizeJourneyRecord } from '../api/journeyRecords.js'
import { downloadAuthenticatedFile } from '../utils/authenticatedFile.js'

let activeLoadPromise = null
let activeDetailPromise = null
const DETAIL_IMAGE_CONCURRENCY = 3

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

function normalizePlanId(value) {
  const planId = Number(value)
  return Number.isInteger(planId) && planId > 0 ? planId : null
}

function normalizeDraftText(value) {
  const text = normalizeText(value)
  return text || null
}

function normalizeSubmissionId(value) {
  const submissionId = Number(value)
  return Number.isInteger(submissionId) && submissionId > 0 ? submissionId : null
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
    displayFinalizedAt: displayDate(record?.finalizedAt),
  }
}

function detailImagePath(resources, imageUrl) {
  return imageUrl ? resources.get(imageUrl)?.displayPath || '' : ''
}

function mapJourneyRecordDetail(record, resources) {
  const coverImageUrl = normalizeText(record?.coverImageUrl)
  const entries = Array.isArray(record?.entries) ? record.entries : []

  return {
    ...mapJourneyRecord(record, {}),
    coverImageUrl,
    displayCoverImage: detailImagePath(resources, coverImageUrl),
    entries: entries.map((entry) => {
      const imageUrl = normalizeText(entry?.imageUrl)
      return {
        taskId: entry?.taskId ?? null,
        submissionId: entry?.submissionId ?? null,
        title: normalizeText(entry?.title),
        subtitle: normalizeText(entry?.subtitle),
        sortOrder: normalizeCount(entry?.sortOrder),
        status: normalizeText(entry?.status),
        note: typeof entry?.note === 'string' ? entry.note : '',
        completedAt: entry?.completedAt || null,
        displayCompletedAt: displayDate(entry?.completedAt),
        imageUrl,
        displayImage: detailImagePath(resources, imageUrl),
      }
    }),
  }
}

function detailImageUrls(record) {
  const urls = [normalizeText(record?.coverImageUrl)]
  if (Array.isArray(record?.entries)) {
    record.entries.forEach((entry) => urls.push(normalizeText(entry?.imageUrl)))
  }
  return [...new Set(urls.filter(Boolean))]
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
    currentRecord: null,
    detailLoading: false,
    detailError: null,
    detailHasLoaded: false,
    detailRequestId: 0,
    detailPlanId: null,
    detailImageResources: new Map(),
    saving: false,
    saveError: null,
    saveRequestId: 0,
    finalizing: false,
    finalizeError: null,
    finalizeRequestId: 0,
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
    isDetailRequestActive(planId, requestId) {
      return this.detailPlanId === planId && this.detailRequestId === requestId
    },
    async loadJourneyRecordDetailImage(imageUrl, planId, requestId) {
      if (!imageUrl || this.detailImageResources.has(imageUrl)) {
        return
      }

      try {
        const resource = await downloadAuthenticatedFile(imageUrl)
        if (!this.isDetailRequestActive(planId, requestId)) {
          resource?.cleanup?.()
          return
        }
        this.detailImageResources.set(imageUrl, {
          displayPath: resource?.displayPath || '',
          cleanup: resource?.cleanup || null,
        })
      } catch (error) {
        // A missing image only falls back to the page placeholder.
      }
    },
    async loadJourneyRecordDetailImages(record, planId, requestId) {
      const urls = detailImageUrls(record)
      let cursor = 0
      const worker = async () => {
        while (cursor < urls.length) {
          const imageUrl = urls[cursor]
          cursor += 1
          await this.loadJourneyRecordDetailImage(imageUrl, planId, requestId)
        }
      }
      await Promise.all(Array.from({ length: Math.min(DETAIL_IMAGE_CONCURRENCY, urls.length) }, worker))
    },
    cleanupUnusedDetailImages(record) {
      const activeUrls = new Set(detailImageUrls(record))
      this.detailImageResources.forEach((resource, imageUrl) => {
        if (!activeUrls.has(imageUrl)) {
          resource?.cleanup?.()
          this.detailImageResources.delete(imageUrl)
        }
      })
    },
    async syncJourneyRecordListItem(record) {
      const planId = normalizePlanId(record?.planId)
      const recordIndex = this.records.findIndex((item) => normalizePlanId(item?.planId) === planId)
      if (recordIndex < 0) {
        return
      }

      const previousRecord = this.records[recordIndex]
      const previousKey = coverResourceKey(previousRecord)
      const nextKey = coverResourceKey(record)
      if (previousKey && previousKey !== nextKey) {
        this.cleanupCoverResource(previousKey)
      }

      const mappedRecord = await this.loadRecordCover(record, this.latestRequestId)
      const currentIndex = this.records.findIndex((item) => normalizePlanId(item?.planId) === planId)
      if (currentIndex >= 0) {
        this.records.splice(currentIndex, 1, mappedRecord)
      }
    },
    loadJourneyRecordDetail(planId) {
      const validPlanId = normalizePlanId(planId)
      if (!(Number.isInteger(validPlanId) && validPlanId > 0)) {
        return Promise.resolve(null)
      }
      if (this.detailLoading && this.detailPlanId === validPlanId && activeDetailPromise) {
        return activeDetailPromise
      }
      if (this.detailPlanId !== validPlanId) {
        this.clearJourneyRecordDetail()
      }

      const requestId = this.detailRequestId + 1
      this.detailRequestId = requestId
      this.detailPlanId = validPlanId
      this.detailLoading = true
      this.detailError = null

      const promise = fetchJourneyRecord(validPlanId)
        .then(async (data) => {
          if (this.detailPlanId !== validPlanId || this.detailRequestId !== requestId) {
            return this.currentRecord
          }
          if (!data?.journeyRecord || typeof data.journeyRecord !== 'object' || !Array.isArray(data?.journeyRecord?.entries)) {
            throw { code: 'INVALID_RESPONSE', message: '旅行记录详情数据格式异常' }
          }

          await this.loadJourneyRecordDetailImages(data.journeyRecord, validPlanId, requestId)
          if (this.detailPlanId !== validPlanId || this.detailRequestId !== requestId) {
            return this.currentRecord
          }

          this.currentRecord = mapJourneyRecordDetail(data.journeyRecord, this.detailImageResources)
          this.detailHasLoaded = true
          this.detailError = null
          return this.currentRecord
        })
        .catch((error) => {
          if (this.isDetailRequestActive(validPlanId, requestId)) {
            this.detailError = error
            this.detailHasLoaded = true
          }
          throw error
        })
        .finally(() => {
          if (this.isDetailRequestActive(validPlanId, requestId)) {
            this.detailLoading = false
          }
          if (activeDetailPromise === promise) {
            activeDetailPromise = null
          }
        })

      activeDetailPromise = promise
      return promise
    },
    retryJourneyRecordDetail() {
      const validPlanId = normalizePlanId(this.detailPlanId)
      if (!(Number.isInteger(validPlanId) && validPlanId > 0)) {
        return Promise.resolve(null)
      }
      return this.loadJourneyRecordDetail(validPlanId)
    },
    async saveJourneyRecordDraft(planId, changes = {}) {
      const validPlanId = normalizePlanId(planId)
      const currentRecord = this.currentRecord
      if (!validPlanId || normalizePlanId(currentRecord?.planId) !== validPlanId) {
        this.saveError = { code: 'INVALID_RECORD', message: '旅行记录已更新，请重新打开后再试。' }
        return { saved: false, journeyRecord: currentRecord }
      }
      if (currentRecord.status !== 'draft') {
        this.saveError = { code: 'RECORD_FINALIZED', message: '这份旅行记录已经封存，不能再修改。' }
        return { saved: false, journeyRecord: currentRecord }
      }
      if (this.finalizing) {
        return { saved: false, reason: 'finalizing', journeyRecord: currentRecord }
      }
      if (this.saving) {
        return { saved: false, journeyRecord: currentRecord }
      }

      const allowedFields = ['customTitle', 'summary', 'coverSubmissionId']
      const payload = {}
      for (const field of allowedFields) {
        if (!Object.prototype.hasOwnProperty.call(changes, field)) {
          continue
        }

        if (field === 'coverSubmissionId') {
          if (changes[field] !== null && !normalizeSubmissionId(changes[field])) {
            this.saveError = { code: 'INVALID_COVER', message: '封面选择无效，请重新选择。' }
            return { saved: false, journeyRecord: currentRecord }
          }
          const nextValue = changes[field] === null ? null : normalizeSubmissionId(changes[field])
          const currentValue = normalizeSubmissionId(currentRecord[field])
          if (nextValue !== currentValue) {
            payload[field] = nextValue
          }
          continue
        }

        const nextValue = normalizeDraftText(changes[field])
        const currentValue = normalizeDraftText(currentRecord[field])
        if (nextValue !== currentValue) {
          payload[field] = nextValue
        }
      }

      if (!Object.keys(payload).length) {
        this.saveError = null
        return { saved: false, journeyRecord: currentRecord }
      }

      const detailRequestId = this.detailRequestId
      const saveRequestId = this.saveRequestId + 1
      this.saveRequestId = saveRequestId
      this.saving = true
      this.saveError = null
      try {
        const data = await updateJourneyRecord(validPlanId, payload)
        const savedRecord = data?.journeyRecord
        if (!savedRecord || typeof savedRecord !== 'object' || !Array.isArray(savedRecord.entries)) {
          throw { code: 'INVALID_RESPONSE', message: '旅行记录保存结果异常' }
        }

        await this.syncJourneyRecordListItem(savedRecord)

        let mappedRecord = null
        if (this.isDetailRequestActive(validPlanId, detailRequestId)) {
          await this.loadJourneyRecordDetailImages(savedRecord, validPlanId, detailRequestId)
          if (this.isDetailRequestActive(validPlanId, detailRequestId)) {
            this.cleanupUnusedDetailImages(savedRecord)
            mappedRecord = mapJourneyRecordDetail(savedRecord, this.detailImageResources)
            this.currentRecord = mappedRecord
            this.detailError = null
          }
        }

        return { saved: true, journeyRecord: mappedRecord }
      } catch (error) {
        if (this.saveRequestId === saveRequestId) {
          this.saveError = error
        }
        throw error
      } finally {
        if (this.saveRequestId === saveRequestId) {
          this.saving = false
        }
      }
    },
    async finalizeJourneyRecordDraft(planId) {
      const validPlanId = normalizePlanId(planId)
      const currentRecord = this.currentRecord
      if (!validPlanId || normalizePlanId(currentRecord?.planId) !== validPlanId) {
        this.finalizeError = { code: 'INVALID_RECORD', message: '旅行记录已更新，请重新打开后再试。' }
        return { finalized: false, journeyRecord: currentRecord }
      }
      if (currentRecord.status === 'finalized') {
        this.finalizeError = null
        return { finalized: true, finalizedNow: false, journeyRecord: currentRecord }
      }
      if (currentRecord.status !== 'draft') {
        this.finalizeError = { code: 'INVALID_STATUS', message: '这份旅行记录当前不能封存。' }
        return { finalized: false, journeyRecord: currentRecord }
      }
      if (this.saving) {
        return { finalized: false, reason: 'saving', journeyRecord: currentRecord }
      }
      if (this.finalizing) {
        return { finalized: false, reason: 'finalizing', journeyRecord: currentRecord }
      }

      const detailRequestId = this.detailRequestId
      const finalizeRequestId = this.finalizeRequestId + 1
      this.finalizeRequestId = finalizeRequestId
      this.finalizing = true
      this.finalizeError = null
      try {
        const data = await finalizeJourneyRecord(validPlanId)
        const finalizedRecord = data?.journeyRecord
        const finalizedNow = data?.finalizedNow === true
        if (
          !finalizedRecord ||
          typeof finalizedRecord !== 'object' ||
          !Array.isArray(finalizedRecord.entries) ||
          normalizePlanId(finalizedRecord.planId) !== validPlanId ||
          finalizedRecord.status !== 'finalized'
        ) {
          throw { code: 'INVALID_RESPONSE', message: '旅行记录封存结果异常' }
        }

        await this.syncJourneyRecordListItem(finalizedRecord)

        let mappedRecord = null
        if (this.isDetailRequestActive(validPlanId, detailRequestId)) {
          await this.loadJourneyRecordDetailImages(finalizedRecord, validPlanId, detailRequestId)
          if (this.isDetailRequestActive(validPlanId, detailRequestId)) {
            this.cleanupUnusedDetailImages(finalizedRecord)
            mappedRecord = mapJourneyRecordDetail(finalizedRecord, this.detailImageResources)
            this.currentRecord = mappedRecord
            this.detailError = null
          }
        }

        return { finalized: true, finalizedNow, journeyRecord: mappedRecord }
      } catch (error) {
        if (this.finalizeRequestId === finalizeRequestId) {
          this.finalizeError = error
        }
        throw error
      } finally {
        if (this.finalizeRequestId === finalizeRequestId) {
          this.finalizing = false
        }
      }
    },
    clearJourneyRecordDetail() {
      this.detailRequestId += 1
      this.detailImageResources.forEach((resource) => resource?.cleanup?.())
      this.detailImageResources.clear()
      this.currentRecord = null
      this.detailLoading = false
      this.detailError = null
      this.detailHasLoaded = false
      this.detailPlanId = null
      this.saveRequestId += 1
      this.saving = false
      this.saveError = null
      this.finalizeRequestId += 1
      this.finalizing = false
      this.finalizeError = null
      activeDetailPromise = null
    },
    resetRecordState() {
      this.latestRequestId += 1
      this.clearJourneyRecordDetail()
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
