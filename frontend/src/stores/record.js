import { defineStore } from 'pinia'
import { fetchJourneyRecords, fetchJourneyRecord, createJourneyRecord, updateJourneyRecord, finalizeJourneyRecord } from '../api/journeyRecords.js'
import { downloadAuthenticatedFile } from '../utils/authenticatedFile.js'
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'

let activeLoadPromise = null
let activeDetailPromise = null
let activeEnsurePromise = null
let activeEnsurePlanId = null
let activeEnsureUserId = null
let activeEnsureEpoch = null
const correctionStatusPromises = new Map()
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

function correctionStatusIdentity(session, planId) {
  return `${session.epoch}:${session.userId}:${planId}`
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
    ensureLoading: false,
    ensureError: null,
    ensurePlanId: null,
    ensuredRecord: null,
    correctionRecordStatusByPlanId: {},
    correctionRecordStatusLoadingByPlanId: {},
    correctionRecordStatusErrorByPlanId: {},
    correctionRecordStatusRequestIdByPlanId: {},
  }),
  getters: {
    learningRecordCount(state) {
      const total = Number(state.total)
      if (Number.isFinite(total) && total >= 0) {
        return total
      }
      return Array.isArray(state.records) ? state.records.length : 0
    },
    loadJourneyRecordCorrectionStatus() {
      return (planId, { force = false } = {}) => {
        const validPlanId = normalizePlanId(planId)
        if (!validPlanId) {
          return Promise.resolve(null)
        }

        const requestSession = getCurrentSession()
        if (!requestSession.isLoggedIn || !requestSession.userId) {
          return Promise.resolve(null)
        }

        const identity = correctionStatusIdentity(requestSession, validPlanId)
        const activePromise = correctionStatusPromises.get(identity)
        if (activePromise && !force) {
          return activePromise
        }

        const key = String(validPlanId)
        const requestId = (this.correctionRecordStatusRequestIdByPlanId[key] || 0) + 1
        this.correctionRecordStatusRequestIdByPlanId[key] = requestId
        this.correctionRecordStatusLoadingByPlanId[key] = true
        this.correctionRecordStatusErrorByPlanId[key] = null

        const promise = fetchJourneyRecord(validPlanId)
          .then((data) => {
            const record = data?.journeyRecord
            if (
              !record
              || typeof record !== 'object'
              || Array.isArray(record)
              || normalizePlanId(record.planId) !== validPlanId
              || !['draft', 'finalized'].includes(record.status)
            ) {
              throw { code: 'INVALID_RESPONSE', message: '成长记录状态数据格式异常' }
            }

            if (this.isCorrectionStatusRequestActive(validPlanId, requestId, requestSession)) {
              this.correctionRecordStatusByPlanId[key] = record.status
              this.correctionRecordStatusErrorByPlanId[key] = null
            }
            return this.correctionRecordStatusForPlan(validPlanId)
          })
          .catch((error) => {
            if (error?.code === 'JOURNEY_RECORD_NOT_FOUND') {
              if (this.isCorrectionStatusRequestActive(validPlanId, requestId, requestSession)) {
                this.correctionRecordStatusByPlanId[key] = 'missing'
                this.correctionRecordStatusErrorByPlanId[key] = null
              }
              return this.correctionRecordStatusForPlan(validPlanId)
            }

            if (this.isCorrectionStatusRequestActive(validPlanId, requestId, requestSession)) {
              if (!Object.prototype.hasOwnProperty.call(this.correctionRecordStatusByPlanId, key)) {
                this.correctionRecordStatusByPlanId[key] = null
              }
              this.correctionRecordStatusErrorByPlanId[key] = error
            }
            throw error
          })
          .finally(() => {
            if (this.isCorrectionStatusRequestActive(validPlanId, requestId, requestSession)) {
              this.correctionRecordStatusLoadingByPlanId[key] = false
            }
            if (correctionStatusPromises.get(identity) === promise) {
              correctionStatusPromises.delete(identity)
            }
          })

        correctionStatusPromises.set(identity, promise)
        return promise
      }
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
    correctionRecordStatusForPlan(planId) {
      const validPlanId = normalizePlanId(planId)
      if (!validPlanId) {
        return null
      }

      const key = String(validPlanId)
      const status = this.correctionRecordStatusByPlanId[key] || null
      const loading = this.correctionRecordStatusLoadingByPlanId[key] === true
      const error = this.correctionRecordStatusErrorByPlanId[key] || null
      const hasStatus = Object.prototype.hasOwnProperty.call(this.correctionRecordStatusByPlanId, key)
      const hasLoading = Object.prototype.hasOwnProperty.call(this.correctionRecordStatusLoadingByPlanId, key)
      const hasError = Object.prototype.hasOwnProperty.call(this.correctionRecordStatusErrorByPlanId, key)
      if (!hasStatus && !hasLoading && !hasError) {
        return null
      }

      return {
        status,
        state: error ? 'error' : status,
        loading,
        error,
      }
    },
    isCorrectionStatusRequestActive(planId, requestId, requestSession) {
      return (
        isCurrentSession(requestSession)
        && this.correctionRecordStatusRequestIdByPlanId[String(planId)] === requestId
      )
    },
    retryJourneyRecordCorrectionStatus(planId) {
      return this.loadJourneyRecordCorrectionStatus(planId, { force: true })
    },
    markJourneyRecordCorrectionFinalized(planId) {
      const validPlanId = normalizePlanId(planId)
      if (!validPlanId) {
        return null
      }

      const key = String(validPlanId)
      this.correctionRecordStatusRequestIdByPlanId[key] = (this.correctionRecordStatusRequestIdByPlanId[key] || 0) + 1
      const requestSession = getCurrentSession()
      if (requestSession.isLoggedIn && requestSession.userId) {
        correctionStatusPromises.delete(correctionStatusIdentity(requestSession, validPlanId))
      }
      this.correctionRecordStatusByPlanId[key] = 'finalized'
      this.correctionRecordStatusLoadingByPlanId[key] = false
      this.correctionRecordStatusErrorByPlanId[key] = null
      return this.correctionRecordStatusForPlan(validPlanId)
    },
    ensureJourneyRecord(planId) {
      const validPlanId = normalizePlanId(planId)
      if (!validPlanId) {
        return Promise.resolve(null)
      }

      const requestSession = getCurrentSession()
      if (!requestSession.isLoggedIn || !requestSession.userId) {
        return Promise.resolve(null)
      }

      if (
        activeEnsurePromise
        && activeEnsurePlanId === validPlanId
        && String(activeEnsureUserId) === String(requestSession.userId)
        && activeEnsureEpoch === requestSession.epoch
      ) {
        return activeEnsurePromise
      }

      this.ensureLoading = true
      this.ensureError = null
      this.ensurePlanId = validPlanId
      activeEnsurePlanId = validPlanId
      activeEnsureUserId = requestSession.userId
      activeEnsureEpoch = requestSession.epoch

      const promise = createJourneyRecord(validPlanId)
        .then((data) => {
          if (
            !data?.journeyRecord
            || typeof data.journeyRecord !== 'object'
            || normalizePlanId(data.journeyRecord.planId) !== validPlanId
          ) {
            throw { code: 'INVALID_RESPONSE', message: '成长记录生成结果异常' }
          }

          const ensuredRecord = mapJourneyRecord(data.journeyRecord, this.coverResources)
          if (isCurrentSession(requestSession) && activeEnsurePromise === promise) {
            this.ensuredRecord = ensuredRecord
            this.ensurePlanId = validPlanId
            this.ensureError = null
          }
          return ensuredRecord
        })
        .catch((error) => {
          if (isCurrentSession(requestSession) && activeEnsurePromise === promise) {
            this.ensureError = error
          }
          throw error
        })
        .finally(() => {
          if (isCurrentSession(requestSession) && activeEnsurePromise === promise) {
            this.ensureLoading = false
            activeEnsurePromise = null
            activeEnsurePlanId = null
            activeEnsureUserId = null
            activeEnsureEpoch = null
          }
        })

      activeEnsurePromise = promise
      return promise
    },
    retryJourneyRecordEnsure() {
      const validPlanId = normalizePlanId(this.ensurePlanId)
      return validPlanId ? this.ensureJourneyRecord(validPlanId) : Promise.resolve(null)
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
      Object.keys(this.correctionRecordStatusRequestIdByPlanId).forEach((planId) => {
        this.correctionRecordStatusRequestIdByPlanId[planId] += 1
      })
      this.correctionRecordStatusByPlanId = {}
      this.correctionRecordStatusLoadingByPlanId = {}
      this.correctionRecordStatusErrorByPlanId = {}
      this.correctionRecordStatusRequestIdByPlanId = {}
      correctionStatusPromises.clear()
      this.ensureLoading = false
      this.ensureError = null
      this.ensurePlanId = null
      this.ensuredRecord = null
      activeEnsurePromise = null
      activeEnsurePlanId = null
      activeEnsureUserId = null
      activeEnsureEpoch = null
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
