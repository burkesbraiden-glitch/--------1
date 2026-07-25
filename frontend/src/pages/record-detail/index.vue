<template>
  <view class="record-detail-page">
    <view class="record-detail-page__paper">
      <view class="record-detail-header">
        <button class="record-detail-header__back" @click="goBack">‹</button>
        <view class="record-detail-header__title-wrap">
          <text class="record-detail-header__spark">✦</text>
          <text class="record-detail-header__title">旅行记录</text>
        </view>
        <button class="record-detail-header__notice" @click="openPetChat">铃</button>
      </view>

      <view v-if="routeError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">这份旅行记录暂时无法打开</text>
        <button class="record-detail-state__button" @click="backToRecordList">返回记录页</button>
      </view>

      <view v-else-if="isInitialLoading" class="record-detail-state">
        <view class="record-detail-state__spinner"></view>
        <text class="record-detail-state__title">正在翻开旅行手账…</text>
      </view>

      <view v-else-if="showFullError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">旅行记录加载失败</text>
        <text class="record-detail-state__desc">{{ errorMessage }}</text>
        <button class="record-detail-state__button" @click="retryDetail">重新加载</button>
      </view>

      <template v-else-if="record">
        <view v-if="detailError" class="record-detail-refresh-error">
          <text>{{ errorMessage }}</text>
          <text @click="retryDetail">重试</text>
        </view>

        <view class="record-detail-title-card">
          <view class="record-detail-title-card__tape"></view>
          <text class="record-detail-title-card__title">{{ record.displayTitle }}</text>
          <text class="record-detail-title-card__destination">⌖ {{ record.destination || '目的地待补充' }}</text>
          <view class="record-detail-title-card__meta">
            <text class="record-detail-status" :class="`record-detail-status--${record.status}`">{{ statusText }}</text>
            <text v-if="record.displayUpdatedAt">更新于 {{ record.displayUpdatedAt }}</text>
          </view>
        </view>

        <view class="record-detail-overview">
          <PolaroidCard
            class="record-detail-overview__cover"
            :image-path="record.displayCoverImage"
            :title="record.displayTitle"
            :description="record.destination"
            :date-label="record.displayUpdatedAt"
            placeholder-theme="roof"
            tape-theme="green"
            :rotation="-2"
          />
          <view class="record-detail-overview__stats">
            <GrowthBadge label="完成任务" :value="`${record.completedTaskCount} / ${record.taskCount}`" icon="✓" theme="yellow" />
            <GrowthBadge label="照片" :value="record.photoCount" icon="●" theme="blue" />
            <GrowthBadge label="笔记" :value="record.noteCount" icon="✎" theme="green" />
          </view>
        </view>

        <view class="record-detail-summary">
          <view class="record-detail-summary__tape"></view>
          <text class="record-detail-section-title">旅途小结</text>
          <text class="record-detail-summary__text">{{ record.summary || '这份旅行记录还没有写下旅途小结。' }}</text>
        </view>

        <view v-if="record.status === 'draft'" class="record-detail-editor">
          <view class="record-detail-editor__tape"></view>
          <view class="record-detail-editor__heading">
            <text class="record-detail-section-title">整理这页手账</text>
            <text>✦</text>
          </view>

          <view v-if="saveError" class="record-detail-editor__error">
            <text>{{ saveErrorMessage }}</text>
          </view>

          <view class="record-detail-editor__field">
            <text class="record-detail-editor__label">旅行标题</text>
            <input
              v-model="customTitleDraft"
              class="record-detail-editor__input"
              maxlength="120"
              placeholder="给这次探索起个名字"
              @input="clearSaveError"
            />
            <text class="record-detail-editor__hint">清空后将恢复计划原始标题</text>
          </view>

          <view class="record-detail-editor__field">
            <view class="record-detail-editor__label-row">
              <text class="record-detail-editor__label">旅途小结</text>
              <text class="record-detail-editor__count">{{ summaryDraft.length }} / 2000</text>
            </view>
            <textarea
              v-model="summaryDraft"
              class="record-detail-editor__textarea"
              maxlength="2000"
              placeholder="写下孩子今天观察到的新发现吧…"
              @input="clearSaveError"
            />
          </view>

          <view class="record-detail-editor__field">
            <view class="record-detail-editor__label-row">
              <text class="record-detail-editor__label">手账封面</text>
              <text class="record-detail-editor__hint">从有照片的任务中挑选</text>
            </view>
            <view v-if="coverCandidates.length" class="record-detail-cover-list">
              <view
                v-for="entry in coverCandidates"
                :key="entry.submissionId"
                class="record-detail-cover-option"
                :class="{ 'record-detail-cover-option--selected': selectedCoverSubmissionId === entry.submissionId }"
                @click="selectCover(entry.submissionId)"
              >
                <image v-if="entry.displayImage" class="record-detail-cover-option__image" :src="entry.displayImage" mode="aspectFill" />
                <view v-else class="record-detail-cover-option__placeholder">◉</view>
                <text class="record-detail-cover-option__title">{{ entry.title || '观察任务照片' }}</text>
                <text v-if="selectedCoverSubmissionId === entry.submissionId" class="record-detail-cover-option__mark">已选</text>
              </view>
            </view>
            <text v-else class="record-detail-editor__empty">完成带照片的观察任务后，就可以选择旅行记录封面。</text>
            <view class="record-detail-cover-list record-detail-cover-list--clear">
              <view
                class="record-detail-cover-option record-detail-cover-option--clear"
                :class="{ 'record-detail-cover-option--selected': selectedCoverSubmissionId === null }"
                @click="clearCover"
              >
                <view class="record-detail-cover-option__placeholder">×</view>
                <text class="record-detail-cover-option__title">清除封面</text>
                <text v-if="selectedCoverSubmissionId === null" class="record-detail-cover-option__mark">已选</text>
              </view>
            </view>
          </view>

          <button class="record-detail-editor__save" :disabled="!hasDraftChanges || saving" @click="saveDraftChanges">
            {{ saving ? '正在保存…' : '保存修改' }}
          </button>
        </view>

        <view class="record-detail-section-head">
          <text class="record-detail-section-head__camera">◉</text>
          <text>探索相册</text>
          <view></view>
          <text>✦</text>
        </view>

        <view v-if="record.entries.length" class="record-detail-entry-list">
          <view v-for="(entry, index) in record.entries" :key="entry.submissionId || entry.taskId" class="record-detail-entry">
            <PolaroidCard
              class="record-detail-entry__photo"
              :image-path="entry.displayImage"
              :title="entry.title"
              :description="entry.subtitle"
              :date-label="entry.displayCompletedAt"
              :placeholder-theme="index % 2 === 0 ? 'roof' : 'gate'"
              :tape-theme="tapeTheme(index)"
              :rotation="index % 2 === 0 ? -2 : 2"
            />
            <view class="record-detail-entry__note">
              <view class="record-detail-entry__head">
                <text class="record-detail-entry__title">{{ entry.title }}</text>
                <text class="record-detail-entry__status">{{ entryStatusText(entry.status) }}</text>
              </view>
              <text v-if="entry.subtitle" class="record-detail-entry__subtitle">{{ entry.subtitle }}</text>
              <view class="record-detail-entry__dash"></view>
              <text v-if="entry.note" class="record-detail-entry__text">{{ entry.note }}</text>
              <text v-else class="record-detail-entry__text record-detail-entry__text--empty">这一站还没有留下文字发现。</text>
              <text v-if="entry.completedAt" class="record-detail-entry__date">{{ entry.displayCompletedAt }}</text>
            </view>
          </view>
        </view>
        <view v-else class="record-detail-empty-entries">
          <text>这份旅行记录里还没有可展示的任务内容。</text>
        </view>

        <view v-if="record.status === 'finalized'" class="record-detail-finalized">
          <text>这份旅行记录已经封存。</text>
        </view>
      </template>
    </view>

    <AiPet />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import GrowthBadge from '../../components/GrowthBadge.vue'
import PolaroidCard from '../../components/PolaroidCard.vue'
import { usePetStore } from '../../stores/pet'
import { useRecordStore } from '../../stores/record'
import { useUserStore } from '../../stores/user'

function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401
}

function normalizePlanId(value) {
  const planId = Number(value)
  return Number.isInteger(planId) && planId > 0 ? planId : null
}

function normalizeDraftText(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || null
}

function normalizeSubmissionId(value) {
  const submissionId = Number(value)
  return Number.isInteger(submissionId) && submissionId > 0 ? submissionId : null
}

export default {
  components: {
    AiPet,
    GrowthBadge,
    PolaroidCard,
  },
  data() {
    return {
      routePlanId: null,
      routeError: false,
      customTitleDraft: '',
      summaryDraft: '',
      selectedCoverSubmissionId: null,
      draftInitializedPlanId: null,
    }
  },
  computed: {
    detailError() {
      return this.recordStore.detailError
    },
    saveError() {
      return this.recordStore.saveError
    },
    saveErrorMessage() {
      return this.saveError?.message || '保存失败，请稍后重试'
    },
    errorMessage() {
      return this.detailError?.message || '请检查网络后再试一次。'
    },
    isInitialLoading() {
      return this.recordStore.detailLoading && !this.record
    },
    record() {
      return this.recordStore.currentRecord
    },
    recordStore() {
      return useRecordStore()
    },
    saving() {
      return this.recordStore.saving
    },
    showFullError() {
      return Boolean(this.detailError) && !this.record
    },
    statusText() {
      return this.record?.status === 'finalized' ? '已封存' : '整理中'
    },
    coverCandidates() {
      const entries = Array.isArray(this.record?.entries) ? this.record.entries : []
      return entries
        .filter((entry) => normalizeSubmissionId(entry?.submissionId) && typeof entry?.imageUrl === 'string' && entry.imageUrl.trim())
        .map((entry) => ({ ...entry, submissionId: normalizeSubmissionId(entry.submissionId) }))
    },
    hasDraftChanges() {
      return Object.keys(this.buildDraftChanges()).length > 0
    },
    userStore() {
      return useUserStore()
    },
  },
  onLoad(options) {
    usePetStore().setPageContext('record-detail')
    this.routePlanId = normalizePlanId(options?.planId)
    this.routeError = !this.routePlanId
    if (!this.routeError) {
      this.loadDetail()
    }
  },
  onUnload() {
    this.recordStore.clearJourneyRecordDetail()
  },
  watch: {
    record: {
      immediate: true,
      handler(record) {
        if (record && record.planId !== this.draftInitializedPlanId) {
          this.syncDraftFromRecord(record)
        }
      },
    },
  },
  methods: {
    syncDraftFromRecord(record) {
      this.customTitleDraft = record?.customTitle || ''
      this.summaryDraft = record?.summary || ''
      this.selectedCoverSubmissionId = normalizeSubmissionId(record?.coverSubmissionId)
      this.draftInitializedPlanId = record?.planId || null
    },
    buildDraftChanges() {
      if (!this.record) {
        return {}
      }

      const changes = {}
      const customTitle = normalizeDraftText(this.customTitleDraft)
      const summary = normalizeDraftText(this.summaryDraft)
      const coverSubmissionId = normalizeSubmissionId(this.selectedCoverSubmissionId)
      if (customTitle !== normalizeDraftText(this.record.customTitle)) {
        changes.customTitle = customTitle
      }
      if (summary !== normalizeDraftText(this.record.summary)) {
        changes.summary = summary
      }
      if (coverSubmissionId !== normalizeSubmissionId(this.record.coverSubmissionId)) {
        changes.coverSubmissionId = coverSubmissionId
      }
      return changes
    },
    clearCover() {
      this.selectedCoverSubmissionId = null
      this.clearSaveError()
    },
    clearSaveError() {
      if (this.recordStore.saveError) {
        this.recordStore.saveError = null
      }
    },
    selectCover(submissionId) {
      const normalizedSubmissionId = normalizeSubmissionId(submissionId)
      if (!normalizedSubmissionId) {
        return
      }
      this.selectedCoverSubmissionId = normalizedSubmissionId
      this.clearSaveError()
    },
    async saveDraftChanges() {
      if (!this.record || this.record.status !== 'draft' || this.saving) {
        return
      }

      const changes = this.buildDraftChanges()
      if (!Object.keys(changes).length) {
        uni.showToast({ title: '还没有需要保存的修改', icon: 'none' })
        return
      }

      this.clearSaveError()
      try {
        const result = await this.recordStore.saveJourneyRecordDraft(this.routePlanId, changes)
        if (!result?.saved || !result.journeyRecord) {
          uni.showToast({ title: '还没有需要保存的修改', icon: 'none' })
          return
        }
        this.syncDraftFromRecord(result.journeyRecord)
        uni.showToast({ title: '旅行记录已保存', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: this.saveErrorMessage, icon: 'none' })
      }
    },
    async handleAuthExpired() {
      this.recordStore.resetRecordState()
      await this.userStore.logout()
      uni.reLaunch({
        url: '/pages/login/index',
      })
    },
    async loadDetail() {
      if (!this.routePlanId) {
        return
      }
      if (!this.userStore.isAuthReady || this.userStore.isRestoring) {
        await this.userStore.restoreSession()
      }
      if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
        this.recordStore.resetRecordState()
        uni.reLaunch({
          url: '/pages/login/index',
        })
        return
      }
      try {
        await this.recordStore.loadJourneyRecordDetail(this.routePlanId)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
        }
      }
    },
    entryStatusText(status) {
      return status === 'completed' ? '已完成' : '记录中'
    },
    goBack() {
      const pages = getCurrentPages()
      if (Array.isArray(pages) && pages.length > 1) {
        uni.navigateBack({
          delta: 1,
          fail: () => this.backToRecordList(),
        })
        return
      }
      this.backToRecordList()
    },
    backToRecordList() {
      uni.switchTab({
        url: '/pages/record/index',
        fail: () => {
          uni.reLaunch({
            url: '/pages/record/index',
          })
        },
      })
    },
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('record-detail')
      petStore.openChat()
    },
    async retryDetail() {
      try {
        await this.recordStore.retryJourneyRecordDetail()
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
        }
      }
    },
    tapeTheme(index) {
      return ['green', 'pink', 'blue'][index % 3]
    },
  },
}
</script>

<style scoped>
.record-detail-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.48) 0, rgba(255, 240, 189, 0) 112rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.record-detail-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  padding: calc(28rpx + env(safe-area-inset-top)) 30rpx calc(110rpx + env(safe-area-inset-bottom));
  margin: 0 auto;
}

.record-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
}

.record-detail-header__back,
.record-detail-header__notice {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.record-detail-header__back {
  font-size: 64rpx;
}

.record-detail-header__notice {
  font-size: 25rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.record-detail-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.record-detail-header__title {
  font-size: 46rpx;
  font-weight: 900;
}

.record-detail-header__spark {
  position: absolute;
  top: -16rpx;
  margin-left: -28rpx;
  font-size: 22rpx;
  color: #f4aa23;
}

.record-detail-state,
.record-detail-title-card,
.record-detail-summary,
.record-detail-empty-entries,
.record-detail-finalized,
.record-detail-entry__note {
  position: relative;
  background: rgba(255, 247, 232, 0.92);
  border: 3rpx solid rgba(223, 189, 131, 0.68);
  box-shadow: 8rpx 10rpx 0 rgba(223, 189, 131, 0.13);
}

.record-detail-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22rpx;
  padding: 72rpx 40rpx;
  text-align: center;
  border-radius: 30rpx;
}

.record-detail-state--error {
  border-color: rgba(217, 75, 18, 0.42);
}

.record-detail-state__spinner {
  width: 72rpx;
  height: 72rpx;
  border: 8rpx solid #fff0bd;
  border-top-color: #f26a21;
  border-radius: 50%;
}

.record-detail-state__title,
.record-detail-title-card__title,
.record-detail-section-title,
.record-detail-entry__title {
  font-size: 34rpx;
  font-weight: 900;
}

.record-detail-state__desc,
.record-detail-summary__text,
.record-detail-entry__text {
  font-size: 26rpx;
  line-height: 1.6;
  color: #5e3c22;
}

.record-detail-state__button {
  min-width: 190rpx;
  font-size: 27rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.record-detail-title-card {
  padding: 42rpx 30rpx 28rpx;
  margin-bottom: 28rpx;
  border-radius: 30rpx;
}

.record-detail-title-card__tape,
.record-detail-summary__tape {
  position: absolute;
  top: -16rpx;
  left: 42rpx;
  width: 88rpx;
  height: 38rpx;
  background: rgba(255, 208, 119, 0.74);
  border-radius: 8rpx;
  transform: rotate(9deg);
}

.record-detail-title-card__title,
.record-detail-title-card__destination,
.record-detail-summary__text,
.record-detail-entry__subtitle,
.record-detail-entry__date {
  display: block;
}

.record-detail-title-card__title {
  font-size: 42rpx;
}

.record-detail-title-card__destination {
  margin-top: 16rpx;
  font-size: 26rpx;
  color: #6b482d;
}

.record-detail-title-card__meta {
  display: flex;
  gap: 16rpx;
  align-items: center;
  margin-top: 22rpx;
  font-size: 22rpx;
  color: #8a6d54;
}

.record-detail-status,
.record-detail-entry__status {
  padding: 7rpx 14rpx;
  font-size: 21rpx;
  font-weight: 900;
  color: #d94b12;
  background: #fff1d8;
  border-radius: 999rpx;
}

.record-detail-status--finalized {
  color: #55753c;
  background: #dceecb;
}

.record-detail-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 24rpx;
  align-items: center;
  margin-bottom: 28rpx;
}

.record-detail-overview__stats {
  display: grid;
  gap: 14rpx;
}

.record-detail-summary {
  padding: 38rpx 28rpx 28rpx;
  margin-bottom: 34rpx;
  border-radius: 26rpx;
}

.record-detail-summary__text {
  display: block;
  margin-top: 16rpx;
}

.record-detail-editor {
  position: relative;
  padding: 42rpx 28rpx 30rpx;
  margin-bottom: 34rpx;
  background: rgba(238, 246, 220, 0.78);
  border: 3rpx solid rgba(123, 154, 80, 0.42);
  border-radius: 26rpx;
  box-shadow: 8rpx 10rpx 0 rgba(123, 154, 80, 0.1);
}

.record-detail-editor__tape {
  position: absolute;
  top: -16rpx;
  right: 46rpx;
  width: 86rpx;
  height: 36rpx;
  background: rgba(164, 208, 157, 0.72);
  border-radius: 8rpx;
  transform: rotate(-8deg);
}

.record-detail-editor__heading,
.record-detail-editor__label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.record-detail-editor__heading {
  margin-bottom: 28rpx;
  color: #55753c;
}

.record-detail-editor__field + .record-detail-editor__field {
  margin-top: 26rpx;
}

.record-detail-editor__label {
  font-size: 27rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.record-detail-editor__hint,
.record-detail-editor__count {
  font-size: 21rpx;
  color: #6b765a;
}

.record-detail-editor__input,
.record-detail-editor__textarea {
  box-sizing: border-box;
  width: 100%;
  margin-top: 12rpx;
  font-size: 26rpx;
  line-height: 1.5;
  color: #4a2f1b;
  background: rgba(255, 253, 244, 0.88);
  border: 2rpx dashed rgba(123, 154, 80, 0.5);
  border-radius: 16rpx;
}

.record-detail-editor__input {
  height: 76rpx;
  padding: 0 20rpx;
}

.record-detail-editor__input + .record-detail-editor__hint {
  display: block;
  margin-top: 10rpx;
}

.record-detail-editor__textarea {
  min-height: 176rpx;
  padding: 16rpx 20rpx;
}

.record-detail-editor__error {
  padding: 14rpx 18rpx;
  margin-bottom: 22rpx;
  font-size: 23rpx;
  color: #9a421b;
  background: #fff1d8;
  border: 2rpx dashed rgba(217, 75, 18, 0.42);
  border-radius: 14rpx;
}

.record-detail-cover-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 14rpx;
}

.record-detail-cover-list--clear {
  grid-template-columns: minmax(0, 1fr);
}

.record-detail-cover-option {
  position: relative;
  min-width: 0;
  padding: 12rpx;
  background: rgba(255, 253, 244, 0.82);
  border: 2rpx solid rgba(223, 189, 131, 0.62);
  border-radius: 16rpx;
}

.record-detail-cover-option--selected {
  background: #e0f0d5;
  border-color: #719b58;
  box-shadow: 0 0 0 3rpx rgba(113, 155, 88, 0.16);
}

.record-detail-cover-option__image,
.record-detail-cover-option__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 112rpx;
  color: #8a6d54;
  background: #fff0bd;
  border-radius: 10rpx;
}

.record-detail-cover-option__image {
  display: block;
}

.record-detail-cover-option--clear .record-detail-cover-option__placeholder {
  font-size: 46rpx;
  color: #a3623e;
  background: #fff7e8;
  border: 2rpx dashed rgba(163, 98, 62, 0.38);
}

.record-detail-cover-option__title {
  display: block;
  overflow: hidden;
  margin-top: 10rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #5e3c22;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-detail-cover-option__mark {
  position: absolute;
  top: 18rpx;
  right: 18rpx;
  padding: 3rpx 10rpx;
  font-size: 19rpx;
  font-weight: 900;
  color: #fff;
  background: #719b58;
  border-radius: 999rpx;
}

.record-detail-editor__empty {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: #6b765a;
}

.record-detail-editor__save {
  width: 100%;
  margin-top: 32rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.record-detail-editor__save[disabled] {
  color: #9b8068;
  background: #ead8b8;
}

.record-detail-section-head {
  display: flex;
  gap: 14rpx;
  align-items: center;
  margin: 18rpx 0 24rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.record-detail-section-head view {
  flex: 1;
  border-top: 3rpx dashed rgba(244, 170, 35, 0.5);
}

.record-detail-section-head__camera {
  color: #8a6d54;
}

.record-detail-entry-list {
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.record-detail-entry {
  display: grid;
  grid-template-columns: minmax(0, 0.98fr) minmax(0, 1fr);
  gap: 22rpx;
  align-items: center;
}

.record-detail-entry:nth-child(even) .record-detail-entry__photo {
  order: 2;
}

.record-detail-entry:nth-child(even) .record-detail-entry__note {
  order: 1;
}

.record-detail-entry__note {
  min-width: 0;
  min-height: 230rpx;
  padding: 26rpx 22rpx;
  border-width: 2rpx;
  border-radius: 18rpx;
}

.record-detail-entry__head {
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
  justify-content: space-between;
}

.record-detail-entry__title {
  min-width: 0;
  font-size: 30rpx;
  line-height: 1.28;
}

.record-detail-entry__status {
  flex-shrink: 0;
  color: #55753c;
  background: #dceecb;
}

.record-detail-entry__subtitle,
.record-detail-entry__date {
  margin-top: 12rpx;
  font-size: 23rpx;
  color: #6b482d;
}

.record-detail-entry__dash {
  height: 2rpx;
  margin: 16rpx 0;
  border-top: 3rpx dashed rgba(223, 189, 131, 0.55);
}

.record-detail-entry__text {
  display: block;
  font-size: 24rpx;
}

.record-detail-entry__text--empty {
  color: #8a6d54;
}

.record-detail-empty-entries,
.record-detail-finalized {
  padding: 34rpx 28rpx;
  margin-bottom: 28rpx;
  font-size: 27rpx;
  line-height: 1.55;
  color: #6b482d;
  border-radius: 24rpx;
}

.record-detail-finalized {
  color: #55753c;
  background: #eef6dc;
  border-color: rgba(123, 154, 80, 0.42);
}

.record-detail-refresh-error {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  padding: 16rpx 22rpx;
  margin-bottom: 20rpx;
  font-size: 23rpx;
  color: #9a421b;
  background: #fff1d8;
  border: 2rpx dashed rgba(217, 75, 18, 0.42);
  border-radius: 18rpx;
}

.record-detail-refresh-error text:last-child {
  font-weight: 900;
  text-decoration: underline;
}

@media (min-width: 431px) {
  .record-detail-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(70px + env(safe-area-inset-bottom));
  }

  .record-detail-header__title {
    font-size: 28px;
  }

  .record-detail-title-card__title {
    font-size: 25px;
  }

  .record-detail-entry__title,
  .record-detail-section-title {
    font-size: 18px;
  }

  .record-detail-summary__text,
  .record-detail-entry__text {
    font-size: 15px;
  }
}
</style>
