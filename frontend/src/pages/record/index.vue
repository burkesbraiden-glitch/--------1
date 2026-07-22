<template>
  <view class="record-page">
    <view class="record-page__paper">
      <view class="record-header">
        <view class="record-header__title-wrap">
          <text class="record-header__spark">记</text>
          <text class="record-header__title">记录</text>
          <text class="record-header__star">星</text>
        </view>
        <button class="record-header__notice" @click="openPetChat">
          <text>铃</text>
          <view class="record-header__dot"></view>
        </button>
      </view>

      <view class="record-intro">
        <view class="record-intro__tape"></view>
        <text class="record-intro__title">探索相册</text>
        <text class="record-intro__desc">每一次观察和发现，都会慢慢收藏在这里。</text>
      </view>

      <view v-if="isInitialLoading" class="record-state">
        <view class="record-state__spinner"></view>
        <text class="record-state__title">正在整理旅行记录……</text>
        <text class="record-state__desc">小旅正在翻看这次探索的珍贵回忆</text>
      </view>

      <view v-else-if="showFullError" class="record-state record-state--error">
        <text class="record-state__icon">！</text>
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
          <text class="section-title__star">星</text>
        </view>

        <view class="record-list">
          <view
            v-for="(record, index) in records"
            :key="record.id"
            class="record-card"
            :class="{ 'record-card--reverse': index % 2 === 1 }"
          >
            <PolaroidCard
              class="record-card__photo"
              :image-path="record.displayCoverImage"
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

    <AiPet />
    <AppTabbar active="record" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import PolaroidCard from '../../components/PolaroidCard.vue'
import { useChildStore } from '../../stores/child'
import { usePetStore } from '../../stores/pet'
import { useRecordStore } from '../../stores/record'
import { useUserStore } from '../../stores/user'

function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401
}

export default {
  components: {
    AiPet,
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
    usePetStore().setPageContext('record')
    await this.loadRecords()
  },
  methods: {
    async handleAuthExpired() {
      this.recordStore.resetRecordState()
      await this.userStore.logout()
      uni.reLaunch({
        url: '/pages/login/index',
      })
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
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('record')
      petStore.openChat()
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
.record-header__star,
.section-title__star {
  position: absolute;
  font-size: 24rpx;
  font-weight: 900;
  color: #f4aa23;
}

.record-header__spark {
  left: -44rpx;
  transform: rotate(-22deg);
}

.record-header__star {
  right: -48rpx;
  transform: rotate(16deg);
}

.record-header__notice {
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62rpx;
  height: 62rpx;
  font-size: 24rpx;
  font-weight: 900;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.record-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
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
  top: -16rpx;
  left: 36rpx;
  width: 74rpx;
  height: 38rpx;
  background: rgba(255, 208, 119, 0.72);
  border-radius: 8rpx;
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
  font-size: 48rpx;
  color: #fff;
  background: #f26a21;
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
  position: static;
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
</style>
