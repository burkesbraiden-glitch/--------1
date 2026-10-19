<template>
  <view class="home-page">
    <view class="home-page__paper">
      <view class="home-header">
        <view v-if="brandLogoPath" class="home-header__brand">
          <image class="home-header__logo" :src="brandLogoPath" mode="heightFix" />
        </view>
        <view class="home-header__tools">
          <button class="home-tool tl-pressable" aria-label="搜索" @click="showToast('搜索功能正在准备中')"><view class="home-tool__search" aria-hidden="true"></view></button>
          <button class="home-tool tl-pressable" aria-label="消息" @click="showToast('暂无消息功能')"><view class="home-tool__notice" aria-hidden="true"></view></button>
        </view>
      </view>

      <view v-if="isHomeLoading" class="home-state"><text class="home-state__title">正在整理这次旅程…</text></view>
      <view v-else-if="homeError" class="home-state home-state--error">
        <text class="home-state__title">首页暂时无法加载</text>
        <text class="home-state__copy">{{ homeError }}</text>
        <button class="home-state__action tl-pressable" @click="loadHome(true)">重新加载</button>
      </view>

      <template v-else>
        <view class="home-section-heading home-section-heading--first"><text class="home-section-heading__title">继续探索</text></view>
        <view class="current-exploration" :class="{ 'current-exploration--with-image': Boolean(heroImage) }">
          <image v-if="heroImage" class="current-exploration__image" :src="heroImage" mode="aspectFill" />
          <view v-if="heroImage" class="current-exploration__shade"></view>
          <view class="current-exploration__content">
            <text class="current-exploration__route">{{ heroRouteTitle }}</text>
            <text class="current-exploration__stop">{{ heroStopLabel }}</text>
            <text v-if="heroProgressLabel" class="current-exploration__progress">{{ heroProgressLabel }}</text>
            <text v-else class="current-exploration__description">{{ heroDescription }}</text>
            <button class="current-exploration__action tl-pressable" @click="openCurrentExploration"><text>{{ heroActionLabel }}</text><text aria-hidden="true">›</text></button>
          </view>
        </view>

        <view v-if="destinationCities.length" class="home-section">
          <view class="home-section-heading"><text class="home-section-heading__title">推荐目的地</text></view>
          <scroll-view class="destination-list" scroll-x :show-scrollbar="false">
            <view class="destination-list__inner">
              <view v-for="destination in destinationCities" :key="destination.city" class="destination-item">
                <image v-if="destination.image" class="destination-item__image" :src="destination.image" mode="aspectFill" />
                <view v-else class="destination-item__image destination-item__image--blank"></view>
                <text class="destination-item__name">{{ destination.city }}</text>
              </view>
            </view>
          </scroll-view>
        </view>

        <view v-if="featuredAttraction" class="home-section">
          <view class="home-section-heading"><text class="home-section-heading__title">本期推荐</text></view>
          <button class="featured-attraction tl-pressable" @click="openAttraction(featuredAttraction)">
            <image v-if="attractionImage(featuredAttraction)" class="featured-attraction__image" :src="attractionImage(featuredAttraction)" mode="aspectFill" />
            <view v-else class="featured-attraction__image featured-attraction__image--blank"></view>
            <view class="featured-attraction__copy">
              <text class="featured-attraction__name">{{ featuredAttraction.name }}</text>
              <text v-if="featuredAttraction.summary" class="featured-attraction__summary">{{ featuredAttraction.summary }}</text>
              <text v-if="durationLabel(featuredAttraction)" class="featured-attraction__meta">{{ durationLabel(featuredAttraction) }}</text>
            </view>
            <text class="featured-attraction__arrow" aria-hidden="true">›</text>
          </button>
        </view>

        <view v-if="inspirationAttractions.length" class="home-section home-section--last">
          <view class="home-section-heading"><text class="home-section-heading__title">更多探索灵感</text></view>
          <view class="inspiration-list">
            <button v-for="attraction in inspirationAttractions" :key="attraction.id" class="inspiration-item tl-pressable" @click="openAttraction(attraction)">
              <image v-if="attractionImage(attraction)" class="inspiration-item__image" :src="attractionImage(attraction)" mode="aspectFill" />
              <view v-else class="inspiration-item__image inspiration-item__image--blank"></view>
              <view class="inspiration-item__copy">
                <text class="inspiration-item__name">{{ attraction.name }}</text>
                <text class="inspiration-item__meta">{{ attraction.city }}<template v-if="durationLabel(attraction)"> · {{ durationLabel(attraction) }}</template></text>
              </view>
              <text class="inspiration-item__arrow" aria-hidden="true">›</text>
            </button>
          </view>
        </view>
      </template>
    </view>
    <AppTabbar active="home" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { getAttractions } from '../../api/attractions.js'
import { useChildStore } from '../../stores/child'
import { usePlanStore } from '../../stores/plan'
import { useRouteStore } from '../../stores/route'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request.js'
import { resolveBackendResourceUrl } from '../../utils/authenticatedFile.js'
import { endUserSession } from '../../utils/sessionBoundary.js'

const brandLogoModules = import.meta.glob('../../assets/brand/tonglvji-logo.png', { eager: true, import: 'default' })
const brandLogoPath = Object.values(brandLogoModules)[0] || ''

function hasId(value) {
  return value !== null && value !== undefined && String(value).trim() !== ''
}

function sameId(left, right) {
  return hasId(left) && hasId(right) && String(left) === String(right)
}

function planRouteId(plan) {
  return plan?.sourceSnapshot?.route?.id || null
}

function firstRouteStop(route, plans) {
  for (const day of route?.days || []) {
    for (const stop of day?.stops || []) {
      const plan = plans.find((item) => sameId(item.routeStopId, stop.id)) || null
      if (plan?.status !== 'completed') return { day, stop, plan }
    }
  }
  return null
}

export default {
  components: { AppTabbar },
  data() {
    return { brandLogoPath, homeRoute: null, attractions: [], homeError: '', isHomeLoading: true }
  },
  computed: {
    childStore() { return useChildStore() },
    planStore() { return usePlanStore() },
    routeStore() { return useRouteStore() },
    userStore() { return useUserStore() },
    hasAuthenticatedUser() { return Boolean(this.userStore.isLoggedIn && this.userStore.userInfo?.id) },
    activeChild() { return this.hasAuthenticatedUser ? this.childStore.activeChild : null },
    activeChildPlans() {
      if (!this.activeChild?.id) return []
      return this.planStore.plans.filter((plan) => sameId(plan.childId, this.activeChild.id))
    },
    inProgressPlan() {
      return this.activeChildPlans.find(
        (plan) => plan.status === 'in-progress' && hasId(plan.routeStopId) && hasId(planRouteId(plan)),
      ) || null
    },
    currentExploration() {
      if (this.inProgressPlan) return this.contextFromPlan(this.inProgressPlan, 'in-progress')
      const nextStop = firstRouteStop(this.homeRoute, this.activeChildPlans)
      if (nextStop?.plan?.status === 'ready') return this.contextFromPlan(nextStop.plan, 'ready', nextStop.day, nextStop.stop)
      if (nextStop?.stop) return this.contextFromRouteStop(nextStop.day, nextStop.stop)
      if (this.homeRoute) return { kind: 'route', route: this.homeRoute, routeId: this.homeRoute.id }
      return { kind: 'empty' }
    },
    heroImage() { return this.attractionImage(this.currentExploration.attraction) },
    heroRouteTitle() {
      if (this.currentExploration.kind === 'empty') return '开始一次新的亲子旅程'
      return this.currentExploration.route?.title || '这次亲子旅程'
    },
    heroStopLabel() {
      const context = this.currentExploration
      if (context.kind === 'empty') return '从路线开始，和孩子一起边走边发现'
      if (context.kind === 'route') return '路线已经准备好'
      const dayNumber = context.day?.dayNumber ? `第${context.day.dayNumber}天` : '今日行程'
      return context.attraction?.name ? `${dayNumber} · ${context.attraction.name}` : dayNumber
    },
    heroProgressLabel() {
      const plan = this.currentExploration.plan
      if (!plan) return ''
      const total = Number(plan.progress?.total) || Number(plan.taskCount) || 0
      const completed = Number(plan.progress?.completed) || 0
      return total > 0 ? `已完成 ${completed} / ${total} 个任务` : ''
    },
    heroDescription() {
      const context = this.currentExploration
      if (context.kind === 'route') return '前往探索页，为今天的景点准备探索内容'
      if (context.kind === 'empty') return '先安排想去的地方，再为每一站准备探索内容'
      if (context.kind === 'ready') return '探索内容已准备'
      return context.attraction?.summary || '继续完成这次探索'
    },
    heroActionLabel() {
      return { 'in-progress': '继续探索', ready: '开始探索', route: '查看今日行程', empty: '规划第一条路线' }[this.currentExploration.kind] || '前往探索'
    },
    destinationCities() {
      const cities = new Map()
      for (const attraction of this.attractions) {
        const city = String(attraction?.city || '').trim()
        if (city && !cities.has(city)) cities.set(city, { city, image: this.attractionImage(attraction) })
      }
      return [...cities.values()].slice(0, 3)
    },
    featuredAttraction() { return this.attractions[0] || null },
    inspirationAttractions() {
      return this.attractions.filter((attraction) => !sameId(attraction.id, this.featuredAttraction?.id)).slice(0, 3)
    },
  },
  async onShow() {
    await this.loadHome()
  },
  methods: {
    contextFromPlan(plan, kind, fallbackDay = null, fallbackStop = null) {
      const snapshot = plan.sourceSnapshot || {}
      const route = snapshot.route || this.homeRoute || null
      const day = snapshot.day || fallbackDay || null
      const stop = snapshot.stop || fallbackStop || null
      return {
        kind,
        plan,
        route,
        day,
        stop,
        attraction: snapshot.attraction || stop?.attraction || null,
        routeId: planRouteId(plan) || route?.id || null,
        dayId: day?.id || null,
        stopId: plan.routeStopId || stop?.id || null,
        planId: plan.id,
      }
    },
    contextFromRouteStop(day, stop) {
      return {
        kind: 'route',
        route: this.homeRoute,
        day,
        stop,
        attraction: stop.attraction || null,
        routeId: this.homeRoute?.id || null,
        dayId: day?.id || null,
        stopId: stop?.id || null,
      }
    },
    routeIdForHome() {
      return planRouteId(this.inProgressPlan) || this.routeStore.routes[0]?.id || null
    },
    async loadHome(force = false) {
      this.homeError = ''
      this.isHomeLoading = true
      this.homeRoute = null
      this.attractions = []
      try {
        if (!this.userStore.isAuthReady || this.userStore.isRestoring) await this.userStore.restoreSession()
        if (!this.hasAuthenticatedUser) {
          uni.reLaunch({ url: '/pages/login/index' })
          return
        }
        const userId = this.userStore.userInfo.id
        await this.childStore.fetchChildren(userId)
        await Promise.all([
          this.routeStore.fetchRoutes(userId, { force }),
          this.planStore.fetchPlans(userId, { selectionPolicy: 'none' }),
          this.loadAttractions(),
        ])
        const routeId = this.routeIdForHome()
        if (hasId(routeId)) this.homeRoute = await this.routeStore.fetchRoute(routeId)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.homeError = '请检查网络后再试一次。'
      } finally {
        this.isHomeLoading = false
      }
    },
    async loadAttractions() {
      try {
        const data = await getAttractions({ limit: 20 })
        this.attractions = Array.isArray(data?.items) ? data.items : []
      } catch (error) {
        if (isAuthenticationError(error)) throw error
        this.attractions = []
      }
    },
    attractionImage(attraction) {
      return attraction?.coverImage ? resolveBackendResourceUrl(attraction.coverImage) : ''
    },
    durationLabel(attraction) {
      const minutes = Number(attraction?.recommendedDurationMinutes)
      return Number.isFinite(minutes) && minutes > 0 ? `约${minutes}分钟` : ''
    },
    buildExploreUrl(context = this.currentExploration) {
      const params = [
        ['routeId', context?.routeId], ['dayId', context?.dayId],
        ['stopId', context?.stopId], ['planId', context?.planId],
      ].filter(([, value]) => hasId(value))
      if (!params.length) return '/pages/explore/index'
      return `/pages/explore/index?${params.map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`).join('&')}`
    },
    openCurrentExploration() {
      uni.reLaunch({ url: this.buildExploreUrl() })
    },
    openAttraction(attraction) {
      if (!hasId(attraction?.id)) return
      uni.navigateTo({ url: `/pages/attraction-detail/index?attractionId=${encodeURIComponent(String(attraction.id))}` })
    },
    showToast(title) { uni.showToast({ title, icon: 'none' }) },
  },
}
</script>

<style scoped>
.home-page { min-height: 100vh; overflow-x: hidden; color: var(--tl-text-main); background: var(--tl-bg); }
.home-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; margin: 0 auto; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 42rpx); }
  .home-header { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; margin-bottom: 38rpx; }.home-header__brand { display: flex; min-width: 0; align-items: center; }.home-header__logo { display: block; width: auto; height: 72rpx; max-width: 264rpx; }.home-header__tools { display: flex; flex-shrink: 0; gap: 12rpx; align-items: center; }
  .home-tool { display: flex; align-items: center; justify-content: center; width: var(--tl-touch-target); min-width: var(--tl-touch-target); height: var(--tl-touch-target); min-height: var(--tl-touch-target); padding: 0; background: transparent; }.home-tool__search { position: relative; width: 29rpx; height: 29rpx; border: 3rpx solid var(--tl-text-main); border-radius: 50%; }.home-tool__search::after { position: absolute; right: -9rpx; bottom: -6rpx; width: 12rpx; height: 3rpx; content: ''; background: var(--tl-text-main); border-radius: 3rpx; transform: rotate(48deg); transform-origin: left center; }.home-tool__notice { position: relative; width: 28rpx; height: 32rpx; border: 3rpx solid var(--tl-text-main); border-radius: 15rpx 15rpx 10rpx 10rpx; }.home-tool__notice::before { position: absolute; bottom: -7rpx; left: 8rpx; width: 7rpx; height: 7rpx; content: ''; background: var(--tl-text-main); border-radius: 50%; }.home-tool__notice::after { position: absolute; bottom: -10rpx; left: 4rpx; width: 15rpx; height: 3rpx; content: ''; background: var(--tl-text-main); border-radius: 3rpx; }
  .home-state { padding: 74rpx 32rpx; margin-top: 54rpx; text-align: center; background: rgba(255, 253, 247, .62); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-sheet); }.home-state__title,.home-state__copy { display: block; }.home-state__title { font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }.home-state__copy { margin-top: 15rpx; font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); }.home-state__action { min-height: var(--tl-touch-target); margin-top: 24rpx; padding: 0 26rpx; font-size: var(--tl-type-body); color: #1f7b47; background: transparent; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-control); }
.home-section-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }.home-section-heading--first { margin-bottom: 18rpx; }.home-section-heading__title { display: block; font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }
  .current-exploration { position: relative; min-height: 286rpx; overflow: hidden; background: linear-gradient(135deg, #347551, #205b3c); border-radius: var(--tl-radius-media); }.current-exploration--with-image { background: #285f43; }.current-exploration__image,.current-exploration__shade { position: absolute; inset: 0; width: 100%; height: 100%; }.current-exploration__image { z-index: 0; }.current-exploration__shade { z-index: 1; background: linear-gradient(180deg, rgba(18, 43, 29, .08), rgba(18, 43, 29, .76)); }.current-exploration__content { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-end; min-height: 286rpx; padding: 28rpx; color: #fff; }.current-exploration__route,.current-exploration__stop,.current-exploration__progress,.current-exploration__description { display: block; }.current-exploration__route { font-size: 38rpx; font-weight: 700; line-height: 1.28; }.current-exploration__stop { margin-top: 8rpx; font-size: 26rpx; line-height: 1.45; color: rgba(255,255,255,.88); }.current-exploration__progress,.current-exploration__description { margin-top: 14rpx; font-size: 23rpx; line-height: 1.45; color: rgba(255,255,255,.84); }.current-exploration__action { display: flex; gap: 11rpx; align-items: center; min-height: var(--tl-touch-target); margin: 20rpx -14rpx -10rpx; padding: 0 14rpx; font-size: 27rpx; font-weight: 600; line-height: 1; color: #fff; background: transparent; border: 1rpx solid rgba(255,255,255,.64); border-radius: var(--tl-radius-control); }.current-exploration__action text:last-child { font-size: 34rpx; font-weight: 400; }
.home-section { margin-top: 52rpx; }.home-section--last { padding-bottom: 18rpx; }.destination-list { width: calc(100% + var(--tl-page-padding)); white-space: nowrap; }.destination-list__inner { display: flex; gap: 16rpx; width: max-content; padding-right: var(--tl-page-padding); }.destination-item { width: 182rpx; }.destination-item__image { display: block; width: 182rpx; height: 128rpx; background: var(--tl-blue); border-radius: var(--tl-radius-media); }.destination-item__image--blank { background: linear-gradient(135deg, #e7eddd, #cce0d2); }.destination-item__name { display: block; margin-top: 12rpx; font-size: 26rpx; font-weight: 600; }
.featured-attraction { display: flex; gap: 18rpx; align-items: center; width: 100%; padding: 0 0 22rpx; color: var(--tl-text-main); text-align: left; background: transparent; border-bottom: 1rpx solid var(--tl-divider); }.featured-attraction__image { flex: 0 0 196rpx; width: 196rpx; height: 148rpx; background: var(--tl-blue); border-radius: var(--tl-radius-media); }.featured-attraction__image--blank { background: linear-gradient(135deg, #e7eddd, #cce0d2); }.featured-attraction__copy { flex: 1; min-width: 0; }.featured-attraction__name,.featured-attraction__summary,.featured-attraction__meta { display: block; }.featured-attraction__name { font-size: 30rpx; font-weight: 700; line-height: 1.35; }.featured-attraction__summary { display: -webkit-box; margin-top: 7rpx; overflow: hidden; font-size: 23rpx; line-height: 1.45; color: var(--tl-text-secondary); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }.featured-attraction__meta { margin-top: 10rpx; font-size: 22rpx; color: #1f7b47; }.featured-attraction__arrow,.inspiration-item__arrow { flex: 0 0 auto; font-size: 34rpx; color: var(--tl-text-secondary); }
.inspiration-list { border-top: 1rpx solid var(--tl-divider); }.inspiration-item { display: flex; gap: 16rpx; align-items: center; width: 100%; min-height: 116rpx; padding: 16rpx 0; color: var(--tl-text-main); text-align: left; background: transparent; border-bottom: 1rpx solid var(--tl-divider); }.inspiration-item__image { flex: 0 0 98rpx; width: 98rpx; height: 82rpx; background: var(--tl-blue); border-radius: var(--tl-radius-small); }.inspiration-item__image--blank { background: linear-gradient(135deg, #e7eddd, #cce0d2); }.inspiration-item__copy { flex: 1; min-width: 0; }.inspiration-item__name,.inspiration-item__meta { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.inspiration-item__name { font-size: 27rpx; font-weight: 600; }.inspiration-item__meta { margin-top: 7rpx; font-size: 22rpx; color: var(--tl-text-secondary); }
@media (max-width: 360px) { .home-page__paper { padding-right: 24rpx; padding-left: 24rpx; }.destination-list { width: calc(100% + 24rpx); }.destination-list__inner { padding-right: 24rpx; }.featured-attraction__image { flex-basis: 166rpx; width: 166rpx; height: 132rpx; }.current-exploration__route { font-size: 35rpx; } }
  @media (min-width: 431px) { .home-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 26px); }.home-header { min-height: 44px; margin-bottom: 22px; }.home-header__logo { height: 36px; max-width: 132px; }.home-header__tools { gap: 6px; }.home-tool { width: 44px; min-width: 44px; height: 44px; min-height: 44px; }.home-tool__search { width: 15px; height: 15px; border-width: 2px; }.home-tool__search::after { right: -5px; bottom: -3px; width: 6px; height: 2px; }.home-tool__notice { width: 14px; height: 16px; border-width: 2px; }.home-tool__notice::before { bottom: -4px; left: 4px; width: 4px; height: 4px; }.home-tool__notice::after { bottom: -5px; left: 2px; width: 8px; height: 2px; }.home-state { padding: 37px 16px; margin-top: 27px; }.home-state__action { min-height: 44px; margin-top: 12px; padding: 0 13px; }.home-section-heading { margin-bottom: 10px; }.home-section-heading--first { margin-bottom: 9px; }.current-exploration,.current-exploration__content { min-height: 164px; }.current-exploration__content { padding: 16px; }.current-exploration__route { font-size: 25px; }.current-exploration__stop { margin-top: 4px; font-size: 16px; }.current-exploration__progress,.current-exploration__description { margin-top: 7px; font-size: 14px; }.current-exploration__action { min-height: 44px; margin: 10px -7px -5px; padding: 0 7px; font-size: 16px; }.current-exploration__action text:last-child { font-size: 20px; }.home-section { margin-top: 29px; }.destination-list { width: calc(100% + 18px); }.destination-list__inner { gap: 8px; padding-right: 18px; }.destination-item { width: 91px; }.destination-item__image { width: 91px; height: 64px; }.destination-item__name { margin-top: 6px; font-size: 15px; }.featured-attraction { gap: 9px; padding-bottom: 11px; }.featured-attraction__image { flex-basis: 98px; width: 98px; height: 74px; }.featured-attraction__name { font-size: 18px; }.featured-attraction__summary { margin-top: 4px; font-size: 14px; }.featured-attraction__meta { margin-top: 5px; font-size: 13px; }.featured-attraction__arrow,.inspiration-item__arrow { font-size: 20px; }.inspiration-item { gap: 8px; min-height: 58px; padding: 8px 0; }.inspiration-item__image { flex-basis: 49px; width: 49px; height: 41px; }.inspiration-item__name { font-size: 16px; }.inspiration-item__meta { margin-top: 4px; font-size: 13px; } }
</style>
