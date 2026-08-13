<template>
  <view class="record-page">
    <view class="record-page__paper">
      <view class="record-header">
        <view class="record-header__title-wrap">
          <view class="record-header__spark" aria-hidden="true"></view>
          <text class="record-header__title">记录</text>
          <view class="record-header__star" aria-hidden="true"></view>
        </view>
      </view>

      <view class="record-intro">
        <view class="record-intro__tape" aria-hidden="true"></view>
        <text class="record-intro__title">探索相册</text>
        <text class="record-intro__desc">每一次观察和发现，都会慢慢收藏在这里。</text>
      </view>

      <view v-if="isInitialLoading" class="record-state">
        <view class="record-state__spinner"></view>
        <text class="record-state__title">正在整理旅行记录……</text>
        <text class="record-state__desc">正在整理这次探索的珍贵回忆</text>
      </view>

      <view v-else-if="showFullError" class="record-state record-state--error">
        <view class="record-state__icon" aria-hidden="true"></view>
        <text class="record-state__title">旅行记录暂时加载失败</text>
        <text class="record-state__desc">{{ errorMessage }}</text>
        <button class="record-state__retry" @click="retryRecords">重新加载</button>
      </view>

      <view v-else-if="isEmpty" class="record-state record-state--empty">
        <view class="record-state__album"></view>
        <text class="record-state__title">还没有旅行记录</text>
        <text class="record-state__desc">完成观察任务后，旅途中的发现会慢慢收藏在这里。</text>
      </view>

      <template v-else>
        <view v-if="error" class="record-refresh-error">
          <text>{{ errorMessage }}</text>
          <text class="record-refresh-error__retry" @click="retryRecords">重试</text>
        </view>

        <view class="section-title">
          <view class="section-title__camera"></view>
          <text>旅行记录</text>
          <view class="section-title__line"></view>
          <view class="section-title__star" aria-hidden="true"></view>
        </view>

        <view class="record-list">
          <view
            v-for="(record, index) in records"
            :key="record.id"
            class="record-card"
            :class="{ 'record-card--reverse': index % 2 === 1 }"
            hover-class="record-card--pressed"
            @click="openRecordDetail(record)"
          >
            <PolaroidCard
              class="record-card__photo"
              :image-path="record.displayCoverImage || recordWatercolorFallback"
              :title="record.displayTitle"
              :description="record.destination"
              :date-label="record.displayUpdatedAt"
              :rotation="index % 2 === 0 ? -2 : 2"
              :placeholder-theme="index % 2 === 0 ? 'roof' : 'gate'"
              :tape-theme="tapeTheme(index)"
            />

            <view class="record-card__note">
              <view class="record-card__head">
                <text class="record-card__title">{{ record.displayTitle }}</text>
                <text class="record-card__status" :class="`record-card__status--${record.status}`">
                  {{ recordStatusText(record) }}
                </text>
              </view>
              <text class="record-card__destination">{{ record.destination || '目的地待补充' }}</text>
              <view class="record-card__dash"></view>
              <view class="record-card__stats">
                <text>完成任务：{{ record.completedTaskCount }} / {{ record.taskCount }}</text>
                <text>照片：{{ record.photoCount }}</text>
                <text>笔记：{{ record.noteCount }}</text>
              </view>
              <text v-if="record.displayUpdatedAt" class="record-card__updated">更新于 {{ record.displayUpdatedAt }}</text>
            </view>
          </view>
        </view>
      </template>
    </view>

    <AppTabbar active="record" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import PolaroidCard from '../../components/PolaroidCard.vue'
import recordWatercolorFallback from '../../assets/record/record-watercolor-fallback.webp'
import { useChildStore } from '../../stores/child'
import { useRecordStore } from '../../stores/record'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401
}

export default {
  components: {
    AppTabbar,
    PolaroidCard,
  },
  computed: {
    childStore() {
      return useChildStore()
    },
    error() {
      return this.recordStore.error
    },
    errorMessage() {
      return this.error?.message || '请检查网络后再试一次'
    },
    hasLoaded() {
      return this.recordStore.hasLoaded
    },
    isEmpty() {
      return this.hasLoaded && !this.loading && !this.error && this.records.length === 0
    },
    isInitialLoading() {
      return this.loading && this.records.length === 0 && !this.hasLoaded
    },
    loading() {
      return this.recordStore.loading
    },
    records() {
      return this.recordStore.records
    },
    recordStore() {
      return useRecordStore()
    },
    showFullError() {
      return Boolean(this.error) && this.records.length === 0
    },
    userStore() {
      return useUserStore()
    },
  },
  async onShow() {
    await this.loadRecords()
  },
  methods: {
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadRecords() {
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
        await this.childStore.fetchChildren(this.userStore.userInfo.id)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
      }

      const params = { limit: 20, offset: 0 }
      const childId = this.childStore.currentChild?.id
      if (Number.isInteger(childId) && childId > 0) {
        params.childId = childId
      }

      try {
        await this.recordStore.loadJourneyRecords(params)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
        }
      }
    },
    openRecordDetail(record) {
      const planId = Number(record?.planId)
      if (!(Number.isInteger(planId) && planId > 0)) {
        return
      }
      uni.navigateTo({
        url: `/pages/record-detail/index?planId=${planId}`,
      })
    },
    recordStatusText(record) {
      if (record.status === 'finalized') {
        return '已封存'
      }
      if (record.status === 'draft') {
        return '整理中'
      }
      return '整理中'
    },
    async retryRecords() {
      try {
        await this.recordStore.retryJourneyRecords()
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
.record-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.44) 0, rgba(255, 240, 189, 0) 126rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.record-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  padding: calc(30rpx + env(safe-area-inset-top)) 30rpx calc(190rpx + env(safe-area-inset-bottom));
  margin: 0 auto;
}

.record-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  margin-bottom: 22rpx;
}

.record-header__title-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.record-header__title {
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1;
}

.record-header__spark,
.record-header__star {
  position: absolute;
  width: 19rpx;
  height: 19rpx;
  color: #f4aa23;
}

.record-header__spark::after,
.record-header__star::after {
  position: absolute;
  inset: 0;
  content: '';
  background: currentColor;
  border-radius: 5rpx;
  transform: rotate(45deg);
}

.record-header__spark {
  left: -44rpx;
  transform: rotate(-22deg);
}

.record-header__star {
  right: -48rpx;
  transform: rotate(16deg);
}

.record-intro,
.record-state,
.record-card__note {
  position: relative;
  background: rgba(255, 247, 232, 0.9);
  border: 3rpx solid rgba(223, 189, 131, 0.72);
  box-shadow: 8rpx 10rpx 0 rgba(223, 189, 131, 0.14);
}

.record-intro {
  padding: 40rpx 30rpx 28rpx;
  margin-bottom: 32rpx;
  border-radius: 28rpx;
}

.record-intro__tape {
  position: absolute;
  top: 12rpx;
  left: 18rpx;
  width: 48rpx;
  height: 18rpx;
  pointer-events: none;
  background: rgba(225, 171, 94, 0.48);
  border: 1rpx solid rgba(190, 142, 78, 0.2);
  border-radius: 5rpx;
  transform: rotate(10deg);
}

.record-intro__title,
.record-state__title,
.record-card__title {
  display: block;
  font-size: 38rpx;
  font-weight: 900;
}

.record-intro__desc,
.record-state__desc {
  display: block;
  margin-top: 14rpx;
  font-size: 25rpx;
  line-height: 1.55;
  color: #6b482d;
}

.record-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 76rpx 42rpx;
  text-align: center;
  border-radius: 30rpx;
}

.record-state--error {
  border-color: rgba(217, 75, 18, 0.45);
}

.record-state__spinner,
.record-state__album,
.record-state__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 86rpx;
  height: 86rpx;
  margin-bottom: 24rpx;
  border-radius: 50%;
}

.record-state__spinner {
  border: 8rpx solid #fff0bd;
  border-top-color: #f26a21;
}

.record-state__album {
  background: #dfeff8;
  border: 5rpx solid #73acd3;
  border-radius: 18rpx;
  transform: rotate(-7deg);
}

.record-state__icon {
  position: relative;
  box-sizing: border-box;
  color: #fff;
  background: #f26a21;
  border: 4rpx solid currentColor;
}

.record-state__icon::before,
.record-state__icon::after {
  position: absolute;
  right: 0;
  left: 0;
  margin: auto;
  content: '';
  background: currentColor;
  border-radius: 999rpx;
}

.record-state__icon::before {
  top: 15rpx;
  width: 4rpx;
  height: 19rpx;
}

.record-state__icon::after {
  bottom: 11rpx;
  width: 5rpx;
  height: 5rpx;
}

.record-state__retry {
  min-width: 180rpx;
  margin-top: 30rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.record-refresh-error {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  padding: 16rpx 22rpx;
  margin-bottom: 22rpx;
  font-size: 23rpx;
  color: #9a421b;
  background: #fff1d8;
  border: 2rpx dashed rgba(217, 75, 18, 0.42);
  border-radius: 18rpx;
}

.record-refresh-error__retry {
  flex-shrink: 0;
  font-weight: 900;
  text-decoration: underline;
}

.section-title {
  position: relative;
  display: flex;
  align-items: center;
  margin: 28rpx 0 24rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.section-title__camera {
  width: 54rpx;
  height: 38rpx;
  margin-right: 14rpx;
  background: #8a6d54;
  border: 4rpx solid #fff0bd;
  border-radius: 10rpx;
  box-shadow: 0 -8rpx 0 -2rpx #8a6d54;
}

.section-title__line {
  flex: 1;
  height: 2rpx;
  margin: 0 18rpx;
  border-top: 3rpx dashed rgba(244, 170, 35, 0.52);
}

.section-title__star {
  flex: 0 0 auto;
  width: 12rpx;
  height: 12rpx;
  color: #f4aa23;
  pointer-events: none;
  background: currentColor;
  border-radius: 3rpx;
  transform: rotate(45deg);
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.record-card {
  display: grid;
  grid-template-columns: minmax(0, 0.98fr) minmax(0, 1fr);
  gap: 22rpx;
  align-items: center;
}

.record-card--pressed {
  opacity: 0.78;
  transform: scale(0.985);
}

.record-card--reverse {
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.98fr);
}

.record-card--reverse .record-card__photo {
  order: 2;
}

.record-card--reverse .record-card__note {
  order: 1;
}

.record-card__note {
  min-width: 0;
  min-height: 238rpx;
  padding: 28rpx 22rpx 22rpx;
  border-width: 2rpx;
  border-radius: 18rpx;
}

.record-card__head {
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
  justify-content: space-between;
}

.record-card__title {
  min-width: 0;
  font-size: 31rpx;
  line-height: 1.26;
}

.record-card__status {
  flex-shrink: 0;
  padding: 6rpx 12rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #8a4a21;
  background: #fff0bd;
  border-radius: 999rpx;
}

.record-card__status--finalized {
  color: #55753c;
  background: #dceecb;
}

.record-card__destination,
.record-card__updated {
  display: block;
  margin-top: 14rpx;
  font-size: 23rpx;
  color: #6b482d;
}

.record-card__dash {
  height: 2rpx;
  margin: 16rpx 0;
  border-top: 3rpx dashed rgba(223, 189, 131, 0.55);
}

.record-card__stats {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  font-size: 22rpx;
  line-height: 1.25;
  color: #5e3c22;
}

@media (min-width: 431px) {
  .record-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(116px + env(safe-area-inset-bottom));
  }

  .record-header__title {
    font-size: 28px;
  }

  .record-intro__title {
    font-size: 25px;
  }

  .record-card__title,
  .section-title {
    font-size: 19px;
  }

  .record-card__stats,
  .record-card__destination,
  .record-card__updated {
    font-size: 13px;
  }
}

.record-page__paper {
  max-width: var(--tl-content-max-width, 430px);
}

.record-intro,
.record-card__note {
  overflow: hidden;
  background:
    linear-gradient(90deg, transparent 0 24rpx, rgba(216, 171, 105, 0.13) 24rpx 26rpx, transparent 26rpx),
    rgba(255, 250, 238, 0.94);
}

.record-intro::after,
.record-card__note::after {
  position: absolute;
  top: 14rpx;
  right: 14rpx;
  width: 32rpx;
  height: 32rpx;
  content: '';
  pointer-events: none;
  border-top: 3rpx solid rgba(244, 170, 35, 0.34);
  border-right: 3rpx solid rgba(244, 170, 35, 0.34);
  border-radius: 0 8rpx 0 0;
}

.record-card {
  padding: 12rpx 4rpx;
  border-bottom: 2rpx dashed rgba(190, 142, 78, 0.24);
}

.record-card__note {
  box-shadow: 10rpx 12rpx 0 rgba(190, 142, 78, 0.12);
}

.record-card__photo {
  filter: saturate(0.96);
}

@media (max-width: 370px) {
  .record-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .record-card,
  .record-card--reverse {
    grid-template-columns: 1fr;
  }

  .record-card--reverse .record-card__photo,
  .record-card--reverse .record-card__note {
    order: initial;
  }
}
</style>
