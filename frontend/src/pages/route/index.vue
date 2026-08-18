<template>
  <view class="route-page">
    <view class="route-page__paper">
      <view class="route-header">
        <view class="route-header__copy">
          <text class="route-header__eyebrow">TRAVEL ROUTES</text>
          <text class="route-header__title">我的路线</text>
          <text class="route-header__subtitle">把想去的地方，一天一天排进旅程里。</text>
        </view>
        <button class="route-header__create" @click="openCreateSheet">+ 新建路线</button>
      </view>

      <view v-if="isPageLoading" class="route-state-card">
        <text class="route-state-card__stamp">正在整理</text>
        <text class="route-state-card__title">正在加载旅行路线...</text>
      </view>

      <view v-else-if="routeStore.error && !showCreateSheet" class="route-state-card">
        <text class="route-state-card__stamp">小小提醒</text>
        <text class="route-state-card__title">路线加载失败</text>
        <text class="route-state-card__action" @click="loadRoutes(true)">重新试一次</text>
      </view>

      <view v-else-if="!routeStore.routes.length" class="route-state-card route-state-card--empty">
        <text class="route-state-card__stamp">旅行手账</text>
        <text class="route-state-card__title">还没有旅行路线</text>
        <text class="route-state-card__desc">先创建一条路线，把想去的景点慢慢安排进去。</text>
        <button class="route-state-card__button" @click="openCreateSheet">创建第一条路线</button>
      </view>

      <view v-else class="route-list">
        <view
          v-for="route in routeStore.routes"
          :key="route.id"
          class="route-card"
          @click="openRouteDetail(route.id)"
        >
          <view class="route-card__tape"></view>
          <view class="route-card__topline">
            <text class="route-card__status">{{ formatRouteStatus(route.status) }}</text>
            <text class="route-card__arrow">›</text>
          </view>
          <text class="route-card__title">{{ route.title }}</text>
          <view class="route-card__meta">
            <text class="route-card__city">{{ route.city }}</text>
            <text class="route-card__date">{{ formatRouteDates(route.startDate, route.endDate) }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="showCreateSheet" class="route-sheet-mask" @click="closeCreateSheet">
      <view class="route-create-sheet" @click.stop>
        <view class="route-create-sheet__handle"></view>
        <view class="route-create-sheet__heading">
          <view>
            <text class="route-create-sheet__eyebrow">NEW TRAVEL ROUTE</text>
            <text class="route-create-sheet__title">写下这次想去的地方</text>
          </view>
          <button class="route-create-sheet__close" @click="closeCreateSheet">×</button>
        </view>

        <view class="route-form-field">
          <text class="route-form-field__label">路线名称</text>
          <input v-model="createForm.title" class="route-form-field__input" placeholder="例如：北京周末文化游" maxlength="60" />
        </view>
        <view class="route-form-field">
          <text class="route-form-field__label">城市</text>
          <input v-model="createForm.city" class="route-form-field__input" placeholder="例如：北京" maxlength="40" />
        </view>
        <view class="route-form-field">
          <text class="route-form-field__label">出发日期（可选）</text>
          <view class="route-form-field__date-row">
            <picker mode="date" :value="createForm.startDate" @change="setDate('startDate', $event)">
              <view class="route-form-field__date">{{ createForm.startDate || '选择出发日期' }}</view>
            </picker>
            <text v-if="createForm.startDate" class="route-form-field__clear" @click="clearDate('startDate')">清除</text>
          </view>
        </view>
        <view class="route-form-field">
          <text class="route-form-field__label">结束日期（可选）</text>
          <view class="route-form-field__date-row">
            <picker mode="date" :value="createForm.endDate" @change="setDate('endDate', $event)">
              <view class="route-form-field__date">{{ createForm.endDate || '选择结束日期' }}</view>
            </picker>
            <text v-if="createForm.endDate" class="route-form-field__clear" @click="clearDate('endDate')">清除</text>
          </view>
        </view>

        <text v-if="formError" class="route-create-sheet__error">{{ formError }}</text>
        <button class="route-create-sheet__submit" :disabled="isCreating" @click="submitCreateRoute">
          {{ isCreating ? '正在保存…' : '创建路线' }}
        </button>
      </view>
    </view>

    <AppTabbar active="route" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useRouteStore } from '../../stores/route'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request'
import { endUserSession } from '../../utils/sessionBoundary'

function emptyCreateForm() {
  return {
    title: '',
    city: '',
    startDate: '',
    endDate: '',
  }
}

export default {
  components: {
    AppTabbar,
  },
  data() {
    return {
      showCreateSheet: false,
      isCreating: false,
      createForm: emptyCreateForm(),
      formError: '',
    }
  },
  computed: {
    routeStore() {
      return useRouteStore()
    },
    userStore() {
      return useUserStore()
    },
    isPageLoading() {
      return this.userStore.isRestoring || this.routeStore.isLoading
    },
  },
  async onShow() {
    await this.loadRoutes()
  },
  methods: {
    async loadRoutes(force = false) {
      try {
        if (!this.userStore.isAuthReady || this.userStore.isRestoring) {
          await this.userStore.restoreSession()
        }
        if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
          uni.reLaunch({ url: '/pages/login/index' })
          return
        }
        await this.routeStore.fetchRoutes(this.userStore.userInfo.id, { force })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
        }
      }
    },
    formatRouteDates(startDate, endDate) {
      const formatDate = (value) => String(value || '').replace(/-/g, '.')
      if (startDate && endDate) return `${formatDate(startDate)} - ${formatDate(endDate)}`
      if (startDate) return `${formatDate(startDate)} 出发`
      return '日期待定'
    },
    formatRouteStatus(status) {
      return {
        draft: '草稿',
        ready: '已准备',
      }[status] || ''
    },
    openRouteDetail(routeId) {
      uni.navigateTo({
        url: `/pages/route-detail/index?id=${encodeURIComponent(String(routeId))}`,
      })
    },
    openCreateSheet() {
      this.showCreateSheet = true
      this.formError = ''
    },
    closeCreateSheet() {
      if (this.isCreating) return
      this.showCreateSheet = false
      this.createForm = emptyCreateForm()
      this.formError = ''
    },
    setDate(field, event) {
      this.createForm[field] = event?.detail?.value || ''
    },
    clearDate(field) {
      this.createForm[field] = ''
    },
    createPayload() {
      const title = this.createForm.title.trim()
      const city = this.createForm.city.trim()
      if (!title || !city) {
        this.formError = '请填写路线名称和城市'
        return null
      }
      if (this.createForm.startDate && this.createForm.endDate && this.createForm.endDate < this.createForm.startDate) {
        this.formError = '结束日期不能早于开始日期'
        return null
      }

      const payload = { title, city }
      if (this.createForm.startDate) payload.startDate = this.createForm.startDate
      if (this.createForm.endDate) payload.endDate = this.createForm.endDate
      return payload
    },
    async submitCreateRoute() {
      if (this.isCreating) return

      const payload = this.createPayload()
      if (!payload) return

      this.isCreating = true
      this.formError = ''
      try {
        const createdRoute = await this.routeStore.createRoute(payload)
        if (!createdRoute?.id) {
          throw new Error('路线创建失败，请稍后重试')
        }
        const detailUrl = `/pages/route-detail/index?id=${encodeURIComponent(String(createdRoute.id))}`
        this.isCreating = false
        this.closeCreateSheet()
        uni.navigateTo({ url: detailUrl })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.formError = error?.message || '路线创建失败，请稍后重试'
      } finally {
        this.isCreating = false
      }
    },
  },
}
</script>

<style scoped>
.route-page {
  min-height: 100vh;
  color: var(--tl-text-main);
  background:
    radial-gradient(circle at 12% 7%, rgba(255, 230, 163, 0.62) 0, rgba(255, 230, 163, 0) 190rpx),
    linear-gradient(135deg, rgba(141, 101, 49, 0.04) 0 1rpx, transparent 1rpx 24rpx),
    var(--tl-bg);
}

.route-page__paper {
  width: 100%;
  max-width: var(--tl-content-max-width);
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 64rpx);
}

.route-header { display: flex; gap: 22rpx; align-items: flex-start; justify-content: space-between; margin-bottom: 36rpx; }
.route-header__copy { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.route-header__eyebrow { margin-bottom: 9rpx; font-size: 18rpx; font-weight: 900; color: var(--tl-primary); letter-spacing: 3rpx; }
.route-header__title { margin-bottom: 9rpx; font-size: 52rpx; font-weight: 900; line-height: 1.08; }
.route-header__subtitle { font-size: 25rpx; line-height: 1.5; color: var(--tl-text-secondary); }
.route-header__create { flex: 0 0 auto; margin: 28rpx 0 0; padding: 15rpx 18rpx; font-size: 23rpx; font-weight: 900; line-height: 1.2; color: var(--tl-paper); background: var(--tl-primary); border: 2rpx solid var(--tl-primary-deep); border-radius: 999rpx; box-shadow: 0 6rpx 0 var(--tl-primary-deep); }

.route-state-card { padding: 56rpx 34rpx; text-align: center; background: var(--tl-paper); border: 3rpx dashed var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }
.route-state-card__stamp { display: inline-flex; margin-bottom: 18rpx; padding: 8rpx 17rpx; font-size: 21rpx; font-weight: 900; color: var(--tl-primary-deep); background: var(--tl-yellow); border: 2rpx solid var(--tl-primary); border-radius: var(--tl-radius-sm); transform: rotate(-3deg); }
.route-state-card__title { display: block; font-size: 34rpx; font-weight: 900; }
.route-state-card__desc { display: block; margin: 16rpx auto 26rpx; font-size: 25rpx; line-height: 1.65; color: var(--tl-text-secondary); }
.route-state-card__action { display: inline-block; margin-top: 20rpx; padding-bottom: 4rpx; font-size: 26rpx; font-weight: 900; color: var(--tl-primary-deep); border-bottom: 2rpx solid currentColor; }
.route-state-card__button { margin-top: 4rpx; padding: 18rpx 28rpx; font-size: 28rpx; font-weight: 900; color: var(--tl-paper); background: var(--tl-primary); border: 2rpx solid var(--tl-primary-deep); border-radius: var(--tl-radius-md); box-shadow: 0 7rpx 0 var(--tl-primary-deep); }

.route-list { display: flex; flex-direction: column; gap: 20rpx; }
.route-card { position: relative; min-height: 196rpx; padding: 30rpx; overflow: hidden; background: var(--tl-paper); border: 2rpx solid var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }
.route-card::after { position: absolute; right: -34rpx; bottom: -40rpx; width: 138rpx; height: 138rpx; content: ''; background: rgba(210, 232, 242, 0.48); border-radius: 50%; }
.route-card__tape { position: absolute; top: 14rpx; left: 42rpx; width: 112rpx; height: 24rpx; background: rgba(243, 205, 114, 0.64); transform: rotate(-5deg); }
.route-card__topline { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }
.route-card__status { position: relative; z-index: 1; padding: 7rpx 13rpx; font-size: 20rpx; font-weight: 900; color: var(--tl-green-deep); background: var(--tl-green); border-radius: 999rpx; }
.route-card__arrow { position: relative; z-index: 1; font-size: 46rpx; color: var(--tl-primary-deep); }
.route-card__title { position: relative; z-index: 1; display: block; overflow: hidden; font-size: 36rpx; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }
.route-card__meta { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 12rpx 20rpx; margin-top: 19rpx; font-size: 23rpx; color: var(--tl-text-secondary); }
.route-card__city::before { margin-right: 7rpx; content: '●'; color: var(--tl-primary); }

.route-sheet-mask { position: fixed; inset: 0; z-index: 60; display: flex; align-items: flex-end; background: rgba(70, 43, 20, 0.36); }
.route-create-sheet { width: 100%; max-width: var(--tl-content-max-width); margin: 0 auto; padding: 20rpx var(--tl-page-padding) calc(var(--tl-safe-bottom) + 34rpx); background: var(--tl-paper); border-radius: 36rpx 36rpx 0 0; }
.route-create-sheet__handle { width: 70rpx; height: 8rpx; margin: 0 auto 25rpx; background: var(--tl-line); border-radius: 99rpx; }
.route-create-sheet__heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 26rpx; }
.route-create-sheet__eyebrow { display: block; margin-bottom: 7rpx; font-size: 17rpx; font-weight: 900; color: var(--tl-primary); letter-spacing: 2rpx; }
.route-create-sheet__title { display: block; font-size: 34rpx; font-weight: 900; }
.route-create-sheet__close { width: 58rpx; height: 58rpx; padding: 0; font-size: 44rpx; line-height: 50rpx; color: var(--tl-text-secondary); background: var(--tl-paper-deep); border-radius: 50%; }
.route-form-field { margin-bottom: 18rpx; }
.route-form-field__label { display: block; margin: 0 0 9rpx 4rpx; font-size: 23rpx; font-weight: 800; color: var(--tl-text-secondary); }
.route-form-field__input, .route-form-field__date { min-height: 78rpx; padding: 0 21rpx; font-size: 27rpx; line-height: 78rpx; background: var(--tl-paper-deep); border: 2rpx solid var(--tl-line); border-radius: var(--tl-radius-md); }
.route-form-field__date-row { display: flex; gap: 16rpx; align-items: center; }
.route-form-field__date-row picker { flex: 1; }
.route-form-field__clear { flex: 0 0 auto; font-size: 23rpx; font-weight: 800; color: var(--tl-primary-deep); }
.route-create-sheet__error { display: block; margin: 8rpx 4rpx 16rpx; font-size: 23rpx; color: #b84a2f; }
.route-create-sheet__submit { width: 100%; min-height: 92rpx; margin-top: 10rpx; font-size: 30rpx; font-weight: 900; color: var(--tl-paper); background: var(--tl-primary); border: 3rpx solid var(--tl-primary-deep); border-radius: var(--tl-radius-md); box-shadow: 0 8rpx 0 var(--tl-primary-deep); }
.route-create-sheet__submit[disabled] { opacity: 0.7; }

@media (min-width: 431px) {
  .route-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 32px); }
  .route-header__eyebrow { font-size: 10px; }
  .route-header__title { font-size: 30px; }
  .route-header__subtitle { font-size: 14px; }
  .route-header__create { margin-top: 18px; padding: 9px 12px; font-size: 13px; }
  .route-card { min-height: 112px; padding: 17px; border-width: 2px; }
  .route-card__title { font-size: 21px; }
  .route-card__meta { margin-top: 11px; font-size: 13px; }
  .route-create-sheet { max-width: 430px; padding-right: 18px; padding-left: 18px; }
}
</style>
