<template>
  <view class="attraction-detail-page">
    <view class="attraction-detail-page__paper">
      <view class="attraction-detail-header">
        <button class="attraction-detail-header__back" @click="goBack" aria-label="返回">‹</button>
        <view class="attraction-detail-header__copy"><text class="attraction-detail-header__eyebrow">ATTRACTION NOTE</text><text class="attraction-detail-header__title">景点详情</text></view>
        <view class="attraction-detail-header__spacer"></view>
      </view>

      <view v-if="attractionState === 'loading'" class="attraction-state-card"><text>正在打开这个景点...</text></view>
      <view v-else-if="attractionState === 'unavailable'" class="attraction-state-card">
        <text class="attraction-state-card__title">这个景点暂时无法打开</text>
        <text class="attraction-state-card__text">它可能已经下架，或链接已失效。</text>
      </view>
      <view v-else-if="attractionState === 'error'" class="attraction-state-card">
        <text class="attraction-state-card__title">景点信息加载失败</text>
        <text class="attraction-state-card__text">{{ attractionError || '请稍后再试。' }}</text>
        <button class="attraction-retry" @click="reloadAttraction">重新加载</button>
      </view>

      <template v-else-if="attraction">
        <view class="attraction-hero">
          <view class="attraction-hero__tape" aria-hidden="true"></view>
          <image v-if="coverImageUrl" class="attraction-hero__cover" :src="coverImageUrl" mode="aspectFill" />
          <view class="attraction-hero__copy" :class="{ 'attraction-hero__copy--text-only': !coverImageUrl }">
            <text class="attraction-hero__eyebrow">CULTURAL EXPLORATION</text>
            <text class="attraction-hero__title">{{ attraction.name }}</text>
            <text class="attraction-hero__location">{{ locationLabel }}</text>
            <text v-if="attraction.recommendedDurationMinutes" class="attraction-hero__duration">推荐游览约 {{ attraction.recommendedDurationMinutes }} 分钟</text>
          </view>
        </view>

        <view class="attraction-info-card">
          <text class="attraction-section__eyebrow">ABOUT THIS PLACE</text>
          <text class="attraction-section__title">先认识这个地方</text>
          <text class="attraction-info-card__summary">{{ attraction.summary }}</text>
          <view v-if="attraction.tags.length" class="attraction-tag-list"><text v-for="tag in attraction.tags" :key="tag" class="attraction-tag">{{ tag }}</text></view>
          <text v-if="attraction.address" class="attraction-info-card__address">地址：{{ attraction.address }}</text>
        </view>

        <view class="attraction-guide-section">
          <view class="attraction-guide-section__heading"><view><text class="attraction-section__eyebrow">FIELD GUIDE</text><text class="attraction-section__title">带着好奇去看看</text></view></view>

          <view v-if="guideState === 'loading'" class="attraction-guide-state">正在准备景点攻略...</view>
          <view v-else-if="guideState === 'no-guide'" class="attraction-guide-state">这个景点暂时还没有详细攻略。</view>
          <view v-else-if="guideState === 'error'" class="attraction-guide-state">
            <text>景点攻略加载失败。</text><text class="attraction-guide-state__retry" @click="reloadGuide">重新加载</text>
          </view>

          <template v-else-if="guideState === 'normal' && guide">
            <view class="attraction-guide-card attraction-guide-card--overview"><text class="attraction-guide-card__label">景点概览</text><text class="attraction-guide-card__text">{{ guide.overview }}</text></view>
            <view class="attraction-guide-card attraction-guide-card--highlights"><text class="attraction-guide-card__label">现场重点</text><view class="attraction-guide-list"><text v-for="item in guide.highlights" :key="item">{{ item }}</text></view></view>
            <view class="attraction-guide-card attraction-guide-card--tips"><text class="attraction-guide-card__label">参观提示</text><view class="attraction-guide-list"><text v-for="item in guide.visitTips" :key="item">{{ item }}</text></view></view>
            <view class="attraction-guide-card attraction-guide-card--family"><text class="attraction-guide-card__label">亲子观察建议</text><view class="attraction-guide-list"><text v-for="item in guide.familyTips" :key="item">{{ item }}</text></view></view>
          </template>
        </view>
      </template>
    </view>

    <AppTabbar active="route" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { getAttractionDetail, getAttractionGuide } from '../../api/attractions.js'
import { resolveBackendResourceUrl } from '../../utils/authenticatedFile.js'
import { isAuthenticationError } from '../../utils/request.js'
import { endUserSession } from '../../utils/sessionBoundary.js'

function normalizeAttractionId(value) {
  const id = String(value ?? '').trim()
  return /^\d+$/.test(id) && Number(id) > 0 ? id : ''
}

export default {
  components: { AppTabbar },
  data() {
    return {
      attractionId: '',
      attraction: null,
      guide: null,
      attractionState: 'loading',
      guideState: 'idle',
      attractionError: '',
    }
  },
  computed: {
    coverImageUrl() {
      return this.attraction?.coverImage ? resolveBackendResourceUrl(this.attraction.coverImage) : ''
    },
    locationLabel() {
      return [this.attraction?.city, this.attraction?.district].filter(Boolean).join(' · ')
    },
  },
  async onLoad(options) {
    this.attractionId = normalizeAttractionId(options?.attractionId)
    if (!this.attractionId) {
      this.setUnavailable()
      return
    }
    await this.loadAttractionDetail()
  },
  methods: {
    setUnavailable() {
      this.attraction = null
      this.guide = null
      this.attractionState = 'unavailable'
      this.guideState = 'idle'
      this.attractionError = ''
    },
    async loadAttractionDetail() {
      if (!this.attractionId) {
        this.setUnavailable()
        return
      }

      this.attraction = null
      this.guide = null
      this.attractionState = 'loading'
      this.guideState = 'idle'
      this.attractionError = ''
      try {
        const data = await getAttractionDetail(this.attractionId)
        if (!data?.attraction) throw { code: 'HTTP_ERROR', message: '景点信息加载失败' }
        this.attraction = data.attraction
        this.attractionState = 'normal'
      } catch (error) {
        if (isAuthenticationError(error)) { await endUserSession(); return }
        if (error?.code === 'ATTRACTION_NOT_FOUND') {
          this.setUnavailable()
          return
        }
        this.attractionState = 'error'
        this.attractionError = error?.message || '请稍后再试。'
        return
      }

      await this.loadAttractionGuide()
    },
    async loadAttractionGuide() {
      if (!this.attraction?.id) return

      this.guide = null
      this.guideState = 'loading'
      try {
        const data = await getAttractionGuide(this.attraction.id)
        this.guide = data?.guide || null
        this.guideState = this.guide ? 'normal' : 'no-guide'
      } catch (error) {
        if (isAuthenticationError(error)) { await endUserSession(); return }
        this.guide = null
        this.guideState = error?.code === 'ATTRACTION_GUIDE_NOT_FOUND' ? 'no-guide' : 'error'
      }
    },
    async reloadAttraction() {
      await this.loadAttractionDetail()
    },
    async reloadGuide() {
      await this.loadAttractionGuide()
    },
    goBack() { uni.navigateBack({ delta: 1 }) },
  },
}
</script>

<style scoped>
.attraction-detail-page{min-height:100vh;color:var(--tl-text-main);background:radial-gradient(circle at 90% 8%,rgba(210,232,242,.64) 0,rgba(210,232,242,0) 190rpx),linear-gradient(135deg,rgba(148,104,48,.045) 0 1rpx,transparent 1rpx 24rpx),var(--tl-bg)}
.attraction-detail-page__paper{width:100%;max-width:var(--tl-content-max-width);min-height:100vh;margin:0 auto;padding:calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 58rpx)}
.attraction-detail-header{display:flex;align-items:center;justify-content:space-between;min-height:88rpx;margin-bottom:30rpx}.attraction-detail-header__back,.attraction-detail-header__spacer{flex:0 0 64rpx;width:64rpx;height:64rpx}.attraction-detail-header__back{padding:0 0 8rpx;font-size:64rpx;line-height:1;color:var(--tl-text-main);background:transparent}.attraction-detail-header__copy{display:flex;flex:1;flex-direction:column;align-items:center}.attraction-detail-header__eyebrow,.attraction-section__eyebrow{display:block;margin-bottom:5rpx;font-size:17rpx;font-weight:900;color:var(--tl-primary);letter-spacing:3rpx}.attraction-detail-header__title{font-size:45rpx;font-weight:900}.attraction-section__title{display:block;font-size:34rpx;font-weight:900}
.attraction-state-card{padding:58rpx 34rpx;text-align:center;background:var(--tl-paper);border:3rpx dashed var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.attraction-state-card__title{display:block;font-size:32rpx;font-weight:900}.attraction-state-card__text{display:block;margin-top:12rpx;font-size:25rpx;line-height:1.6;color:var(--tl-text-secondary)}.attraction-retry{display:inline-flex;min-height:62rpx;margin-top:22rpx;padding:0 28rpx;font-size:24rpx;font-weight:900;line-height:62rpx;color:var(--tl-paper);background:var(--tl-primary);border:2rpx solid var(--tl-primary-deep);border-radius:999rpx}
.attraction-hero{position:relative;display:flex;min-height:350rpx;overflow:hidden;background:var(--tl-paper);border:3rpx solid var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.attraction-hero__tape{position:absolute;top:16rpx;left:52%;z-index:3;width:110rpx;height:26rpx;background:rgba(243,205,114,.7);transform:translateX(-50%) rotate(-5deg)}.attraction-hero__cover{width:46%;min-height:350rpx;background:var(--tl-paper-deep)}.attraction-hero__copy{display:flex;flex:1;flex-direction:column;justify-content:center;padding:42rpx 32rpx;background:var(--tl-paper)}.attraction-hero__copy--text-only{padding-right:42rpx;padding-left:42rpx;background:linear-gradient(135deg,rgba(255,241,216,.86),rgba(239,247,226,.72))}.attraction-hero__eyebrow{display:block;margin-bottom:12rpx;font-size:19rpx;font-weight:900;color:var(--tl-primary-deep);letter-spacing:2rpx}.attraction-hero__title{display:block;font-size:48rpx;font-weight:900;line-height:1.2}.attraction-hero__location,.attraction-hero__duration{display:block;margin-top:15rpx;font-size:24rpx;line-height:1.5;color:var(--tl-text-secondary)}.attraction-hero__duration{font-weight:800;color:var(--tl-primary-deep)}
.attraction-info-card,.attraction-guide-card{margin-top:24rpx;padding:28rpx;background:var(--tl-paper);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.attraction-info-card__summary{display:block;margin-top:14rpx;font-size:26rpx;line-height:1.7;color:var(--tl-text-secondary)}.attraction-tag-list{display:flex;flex-wrap:wrap;gap:10rpx;margin-top:20rpx}.attraction-tag{padding:8rpx 15rpx;font-size:21rpx;font-weight:800;color:var(--tl-primary-deep);background:#fff0d2;border:2rpx solid rgba(242,106,33,.26);border-radius:999rpx}.attraction-info-card__address{display:block;margin-top:18rpx;padding-top:16rpx;font-size:23rpx;line-height:1.5;color:var(--tl-text-secondary);border-top:2rpx dashed var(--tl-line)}
.attraction-guide-section{margin-top:38rpx}.attraction-guide-section__heading{margin:0 6rpx 16rpx}.attraction-guide-state{padding:46rpx 26rpx;text-align:center;font-size:25rpx;line-height:1.6;color:var(--tl-text-secondary);background:var(--tl-paper);border:3rpx dashed var(--tl-line);border-radius:var(--tl-radius-lg)}.attraction-guide-state__retry{display:inline-block;margin-left:14rpx;font-weight:900;color:var(--tl-primary-deep);text-decoration:underline}.attraction-guide-card{position:relative;margin-top:16rpx;overflow:hidden}.attraction-guide-card__label{display:block;font-size:29rpx;font-weight:900}.attraction-guide-card__text{display:block;margin-top:12rpx;font-size:25rpx;line-height:1.65;color:var(--tl-text-secondary)}.attraction-guide-list{display:flex;flex-direction:column;gap:10rpx;margin-top:14rpx}.attraction-guide-list text{display:flex;gap:10rpx;align-items:flex-start;font-size:25rpx;line-height:1.5;color:var(--tl-text-secondary)}.attraction-guide-list text::before{flex:0 0 auto;width:12rpx;height:12rpx;margin-top:12rpx;content:'';background:var(--tl-primary);border-radius:50%}.attraction-guide-card--overview{border-color:rgba(242,106,33,.45)}.attraction-guide-card--highlights{background:#fff4dd}.attraction-guide-card--tips{background:var(--tl-blue)}.attraction-guide-card--family{background:var(--tl-green)}
@media (max-width:360px){.attraction-detail-page__paper{padding-right:24rpx;padding-left:24rpx}.attraction-hero{min-height:300rpx}.attraction-hero__cover{width:40%;min-height:300rpx}.attraction-hero__copy{padding:30rpx 22rpx}.attraction-hero__title{font-size:42rpx}}
@media (min-width:431px){.attraction-detail-page__paper{padding:calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 34px)}.attraction-detail-header{min-height:44px;margin-bottom:16px}.attraction-detail-header__back,.attraction-detail-header__spacer{flex-basis:36px;width:36px;height:36px}.attraction-detail-header__back{font-size:36px}.attraction-detail-header__eyebrow,.attraction-section__eyebrow{font-size:10px}.attraction-detail-header__title{font-size:28px}.attraction-section__title{font-size:21px}.attraction-hero{min-height:210px;border-width:2px}.attraction-hero__cover{min-height:210px}.attraction-hero__copy{padding:25px 20px}.attraction-hero__title{font-size:29px}.attraction-hero__location,.attraction-hero__duration{margin-top:8px;font-size:14px}.attraction-info-card,.attraction-guide-card{margin-top:14px;padding:18px}.attraction-info-card__summary,.attraction-guide-card__text,.attraction-guide-list text{font-size:14px}.attraction-guide-card__label{font-size:18px}.attraction-guide-section{margin-top:24px}.attraction-guide-state{padding:28px 18px;font-size:14px}}
</style>
