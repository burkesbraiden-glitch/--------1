<template>
  <view class="explore-workbench">
    <view class="explore-workbench__paper">
      <view class="workbench-header">
        <image class="workbench-header__logo" :src="brandLogo" mode="widthFix" />
        <view class="workbench-header__tools">
          <button class="header-tool header-tool--search" aria-label="搜索" @click="showToast('搜索功能正在准备中')">
            <view class="header-tool__search"></view>
          </button>
          <button class="header-tool header-tool--notice" aria-label="消息提醒" @click="showToast('暂时没有新消息')">
            <view class="header-tool__bell"></view>
            <view class="header-tool__dot"></view>
          </button>
        </view>
      </view>

      <view v-if="isBootstrapping" class="workbench-state">
        <text class="workbench-state__title">正在整理这次行程…</text>
        <text class="workbench-state__copy">路线、景点和探索任务正在一起加载。</text>
      </view>

      <view v-else-if="pageError" class="workbench-state">
        <text class="workbench-state__title">探索工作台暂时打不开</text>
        <text class="workbench-state__copy">{{ pageError }}</text>
        <button class="workbench-state__button" @click="loadWorkbench(true)">重新加载</button>
      </view>

      <view v-else-if="!routeStore.routes.length">
        <view class="workbench-state workbench-state--empty">
          <text class="workbench-state__title">从第一条路线开始</text>
          <text class="workbench-state__copy">安排每天要去的景点，再为每个景点准备孩子的探索任务。</text>
          <button class="workbench-state__button" @click="openCreateRouteSheet">创建第一条路线</button>
        </view>

        <view v-if="freePlans.length" class="free-section">
          <view class="free-section__heading">
            <view>
              <text class="free-section__title">自由探索</text>
              <text class="free-section__copy">这些探索没有路线来源，仍然可以继续完成。</text>
            </view>
          </view>
          <button v-for="plan in freePlans" :key="plan.id" class="free-plan" @click="openFreePlan(plan)">
            <view>
              <text class="free-plan__title">{{ plan.title }}</text>
              <text class="free-plan__meta">{{ plan.destination }} · {{ planProgressText(plan) }}</text>
            </view>
            <text class="free-plan__arrow">›</text>
          </button>
        </view>
      </view>

      <template v-else-if="currentRoute">
        <view class="route-hero">
          <image class="route-hero__image" :src="routeCover" mode="aspectFill" />
          <view class="route-hero__veil"></view>
          <view class="route-hero__content">
            <button class="route-hero__switch" @click="showRouteSwitcher = true">切换路线</button>
            <text class="route-hero__title">{{ currentRoute.title }}</text>
            <text class="route-hero__meta">{{ currentRoute.city }} · {{ formatRouteDates(currentRoute.startDate, currentRoute.endDate) }}</text>
            <text v-if="activeChild" class="route-hero__child">{{ activeChild.name }} · {{ activeChild.age }}岁</text>
            <button class="route-hero__edit" @click="editRoute">编辑路线</button>
          </view>
          <view class="route-stats">
            <view class="route-stats__item">
              <text class="route-stats__value">{{ routeDayCount }}</text>
              <text class="route-stats__label">天行程</text>
            </view>
            <view class="route-stats__item">
              <text class="route-stats__value">{{ routeStopCount }}</text>
              <text class="route-stats__label">个景点</text>
            </view>
            <view class="route-stats__item">
              <text class="route-stats__value">{{ routePlanCount }}</text>
              <text class="route-stats__label">个探索计划</text>
            </view>
            <view class="route-stats__item">
              <text class="route-stats__value">{{ routeTaskCount }}</text>
              <text class="route-stats__label">个探索任务</text>
            </view>
          </view>
        </view>

        <view v-if="currentRoute.days.length" class="day-tabs">
          <button
            v-for="day in currentRoute.days"
            :key="day.id"
            class="day-tab"
            :class="{ 'day-tab--active': sameId(day.id, selectedDayId) }"
            @click="selectDay(day.id)"
          >
            <text class="day-tab__title">第{{ day.dayNumber }}天</text>
            <text class="day-tab__date">{{ formatDayDate(day.date) }}</text>
          </button>
        </view>

        <view v-if="!currentRoute.days.length" class="workbench-state workbench-state--inline">
          <text class="workbench-state__title">这条路线还没有每日安排</text>
          <text class="workbench-state__copy">先添加一天，再把景点排进行程。</text>
          <button class="workbench-state__button workbench-state__button--quiet" @click="editRoute">去编辑路线</button>
        </view>

        <template v-else-if="currentDay">
          <view class="day-heading">
            <view>
              <text class="day-heading__title">{{ currentDay.title || ('第' + currentDay.dayNumber + '天行程') }}</text>
              <text class="day-heading__meta">{{ formatDayDateLong(currentDay.date) }} · {{ currentDay.stops.length }} 个景点</text>
            </view>
            <button
              v-if="missingPlanStopIds.length"
              class="day-heading__action"
              :disabled="routeStore.isGeneratingPlans"
              @click="generateTodayPlans"
            >
              {{ routeStore.isGeneratingPlans ? '准备中…' : '准备今日探索' }}
            </button>
          </view>

          <view v-if="!currentDay.stops.length" class="workbench-state workbench-state--inline">
            <text class="workbench-state__title">今天还没有景点</text>
            <text class="workbench-state__copy">把要去的地方加入这一天，探索任务会跟着景点组织。</text>
            <button class="workbench-state__button workbench-state__button--quiet" @click="editRoute">添加景点</button>
          </view>

          <view v-else class="stop-list">
            <view
              v-for="(stop, index) in currentDay.stops"
              :key="stop.id"
              class="stop-block"
              :class="{ 'stop-block--focused': sameId(stop.id, selectedStopId) }"
            >
              <view class="stop-summary" @click="focusStop(stop, currentDay)">
                <view class="stop-summary__number">{{ index + 1 }}</view>
                <image
                  v-if="stop.attraction && stop.attraction.coverImage"
                  class="stop-summary__image"
                  :src="stop.attraction.coverImage"
                  mode="aspectFill"
                />
                <view v-else class="stop-summary__image stop-summary__image--placeholder"></view>

                <view class="stop-summary__copy">
                  <view class="stop-summary__topline">
                    <text class="stop-summary__name">{{ stop.attraction?.name || '未命名景点' }}</text>
                    <text
                      class="plan-status"
                      :class="'plan-status--' + planStatusKey(planForStop(stop.id))"
                    >
                      {{ planStatusText(planForStop(stop.id)) }}
                    </text>
                  </view>
                  <text class="stop-summary__meta">{{ stopMeta(stop) }}</text>
                  <text v-if="planForStop(stop.id)" class="stop-summary__progress">
                    {{ planProgressText(planForStop(stop.id)) }}
                  </text>
                </view>
                <text class="stop-summary__arrow">{{ sameId(stop.id, selectedStopId) ? '⌃' : '›' }}</text>
              </view>

              <view v-if="sameId(stop.id, selectedStopId)" class="stop-detail">
                <text v-if="stop.attraction?.summary" class="stop-detail__summary">{{ stop.attraction.summary }}</text>
                <text v-if="stop.note" class="stop-detail__note">行程备注：{{ stop.note }}</text>

                <view v-if="!planForStop(stop.id)" class="plan-empty">
                  <view>
                    <text class="plan-empty__title">这个景点还没有探索内容</text>
                    <text class="plan-empty__copy">
                      {{ currentRoute.status === 'ready' ? '为当前孩子生成讲解和观察任务。' : '先编辑路线并标记为“已准备”，再生成探索。' }}
                    </text>
                  </view>
                  <button
                    v-if="currentRoute.status === 'ready'"
                    class="plan-empty__button"
                    :disabled="routeStore.isGeneratingPlans"
                    @click.stop="generatePlanForStop(stop)"
                  >
                    {{ sameId(isGeneratingStopId, stop.id) ? '生成中…' : '生成探索' }}
                  </button>
                  <button v-else class="plan-empty__button plan-empty__button--quiet" @click.stop="editRoute">编辑路线</button>
                </view>

                <template v-else>
                  <view class="task-heading">
                    <view>
                      <text class="task-heading__title">探索任务</text>
                      <text class="task-heading__meta">{{ planForStop(stop.id).title }}</text>
                    </view>
                    <button class="task-heading__guide" @click.stop="openGuide(planForStop(stop.id))">听讲解</button>
                  </view>

                  <view v-if="isFocusedTaskLoading" class="task-loading">
                    {{ taskStore.isGenerating ? '正在准备探索任务…' : '正在加载任务…' }}
                  </view>

                  <view v-else-if="focusedTasks.length" class="task-list">
                    <button
                      v-for="task in focusedTasks"
                      :key="task.id"
                      class="task-row"
                      :class="{ 'task-row--done': task.status === 'completed' }"
                      @click.stop="openTask(task)"
                    >
                      <view class="task-row__check">{{ task.status === 'completed' ? '✓' : '' }}</view>
                      <view class="task-row__copy">
                        <text class="task-row__title">{{ task.title }}</text>
                        <text class="task-row__summary">{{ task.summary }}</text>
                      </view>
                      <text class="task-row__arrow">›</text>
                    </button>
                  </view>

                  <view v-else class="task-empty">
                    <text>探索任务还没有准备好。</text>
                  </view>
                </template>
              </view>
            </view>
          </view>

          <button class="add-stop-action" @click="editRoute">＋ 添加或调整景点</button>
        </template>

        <view v-if="freePlans.length" class="free-section">
          <view class="free-section__heading">
            <text class="free-section__title">自由探索</text>
            <text class="free-section__copy">没有加入路线的探索计划</text>
          </view>
          <button v-for="plan in freePlans" :key="plan.id" class="free-plan" @click="openFreePlan(plan)">
            <view>
              <text class="free-plan__title">{{ plan.title }}</text>
              <text class="free-plan__meta">{{ plan.destination }} · {{ planProgressText(plan) }}</text>
            </view>
            <text class="free-plan__arrow">›</text>
          </button>
        </view>
      </template>
    </view>

    <view v-if="stickyLabel" class="sticky-action">
      <button
        class="sticky-action__button"
        :disabled="stickyBusy"
        @click="handleStickyAction"
      >
        {{ stickyBusy ? '正在处理…' : stickyLabel }}
        <text class="sticky-action__arrow">›</text>
      </button>
    </view>

    <view v-if="showRouteSwitcher" class="sheet-mask" @click="showRouteSwitcher = false">
      <view class="sheet-panel" @click.stop>
        <view class="sheet-panel__head">
          <text>切换路线</text>
          <button @click="showRouteSwitcher = false">关闭</button>
        </view>
        <view class="route-options">
          <button
            v-for="route in routeStore.routes"
            :key="route.id"
            class="route-option"
            :class="{ 'route-option--active': sameId(route.id, selectedRouteId) }"
            @click="selectRoute(route.id)"
          >
            <view>
              <text class="route-option__title">{{ route.title }}</text>
              <text class="route-option__meta">{{ route.city }} · {{ formatRouteDates(route.startDate, route.endDate) }}</text>
            </view>
            <text v-if="sameId(route.id, selectedRouteId)" class="route-option__current">当前</text>
          </button>
        </view>
        <button class="sheet-panel__primary" @click="openCreateRouteSheet">＋ 新建路线</button>
      </view>
    </view>

    <view v-if="showCreateRouteSheet" class="sheet-mask" @click="closeCreateRouteSheet">
      <view class="sheet-panel" @click.stop>
        <view class="sheet-panel__head">
          <text>新建路线</text>
          <button @click="closeCreateRouteSheet">关闭</button>
        </view>
        <view class="form-field">
          <text>路线名称</text>
          <input v-model="createForm.title" placeholder="例如：北京周末文化游" maxlength="60" />
        </view>
        <view class="form-field">
          <text>城市</text>
          <input v-model="createForm.city" placeholder="例如：北京" maxlength="40" />
        </view>
        <view class="form-field">
          <text>出发日期（可选）</text>
          <picker mode="date" :value="createForm.startDate" @change="setCreateDate('startDate', $event)">
            <view class="form-field__picker">{{ createForm.startDate || '选择日期' }}</view>
          </picker>
        </view>
        <view class="form-field">
          <text>结束日期（可选）</text>
          <picker mode="date" :value="createForm.endDate" @change="setCreateDate('endDate', $event)">
            <view class="form-field__picker">{{ createForm.endDate || '选择日期' }}</view>
          </picker>
        </view>
        <text v-if="createError" class="form-error">{{ createError }}</text>
        <button class="sheet-panel__primary" :disabled="isCreatingRoute" @click="createRoute">
          {{ isCreatingRoute ? '正在创建…' : '创建并继续规划' }}
        </button>
      </view>
    </view>

    <AudioGuideSheet v-model:open="audioGuideOpen" :plan-id="audioGuidePlanId" />
    <AppTabbar active="explore" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import AudioGuideSheet from '../../components/AudioGuideSheet.vue'
import { useChildStore } from '../../stores/child'
import { usePlanStore } from '../../stores/plan'
import { useRecordStore } from '../../stores/record'
import { useRouteStore } from '../../stores/route'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request'
import { endUserSession } from '../../utils/sessionBoundary'
import brandLogo from '../../assets/brand/tonglvji-logo.png'
import defaultHero from '../../assets/home/home-hero-watercolor.webp'

function sameId(left, right) {
  return left !== null
    && left !== undefined
    && right !== null
    && right !== undefined
    && String(left) === String(right)
}

function hasId(value) {
  return value !== null && value !== undefined && String(value).trim() !== ''
}

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
    AudioGuideSheet,
  },
  data() {
    return {
      brandLogo,
      isBootstrapping: false,
      hasLoaded: false,
      pageError: '',
      selectedRouteId: '',
      selectedDayId: '',
      selectedStopId: '',
      preferredPlanId: '',
      showRouteSwitcher: false,
      showCreateRouteSheet: false,
      isCreatingRoute: false,
      createForm: emptyCreateForm(),
      createError: '',
      audioGuideOpen: false,
      audioGuidePlanId: null,
      isGeneratingStopId: '',
      isStartingPlan: false,
      isCompletingPlan: false,
    }
  },
  computed: {
    userStore() {
      return useUserStore()
    },
    childStore() {
      return useChildStore()
    },
    routeStore() {
      return useRouteStore()
    },
    planStore() {
      return usePlanStore()
    },
    taskStore() {
      return useTaskStore()
    },
    recordStore() {
      return useRecordStore()
    },
    activeChild() {
      return this.childStore.activeChild
    },
    currentRoute() {
      if (!this.routeStore.currentRoute || !sameId(this.routeStore.currentRoute.id, this.selectedRouteId)) {
        return null
      }
      return this.routeStore.currentRoute
    },
    currentDay() {
      return this.currentRoute?.days?.find((day) => sameId(day.id, this.selectedDayId)) || null
    },
    focusedStop() {
      return this.currentDay?.stops?.find((stop) => sameId(stop.id, this.selectedStopId)) || null
    },
    childPlans() {
      if (!this.activeChild) {
        return []
      }
      return this.planStore.plans.filter((plan) => sameId(plan.childId, this.activeChild.id))
    },
    routePlans() {
      if (!this.currentRoute) {
        return []
      }
      return this.childPlans.filter((plan) => sameId(plan.sourceSnapshot?.route?.id, this.currentRoute.id))
    },
    focusedPlan() {
      return this.focusedStop ? this.planForStop(this.focusedStop.id) : null
    },
    focusedTasks() {
      if (!this.focusedPlan) {
        return []
      }
      return this.taskStore.displayTasksForPlan(this.focusedPlan.id)
    },
    isFocusedTaskLoading() {
      return Boolean(this.focusedPlan && (this.taskStore.isLoading || this.taskStore.isGenerating))
    },
    completedTaskCount() {
      return this.focusedTasks.filter((task) => task.status === 'completed').length
    },
    allFocusedTasksCompleted() {
      return Boolean(this.focusedTasks.length && this.completedTaskCount === this.focusedTasks.length)
    },
    nextTask() {
      return this.focusedTasks.find((task) => task.status !== 'completed') || null
    },
    routeDayCount() {
      return this.currentRoute?.days?.length || 0
    },
    routeStopCount() {
      return (this.currentRoute?.days || []).reduce((sum, day) => sum + (day.stops?.length || 0), 0)
    },
    routePlanCount() {
      return this.routePlans.length
    },
    routeTaskCount() {
      return this.routePlans.reduce((sum, plan) => sum + (Number(plan.progress?.total) || Number(plan.taskCount) || 0), 0)
    },
    routeCover() {
      const stops = (this.currentRoute?.days || []).flatMap((day) => day.stops || [])
      return stops.find((stop) => stop.attraction?.coverImage)?.attraction?.coverImage || defaultHero
    },
    missingPlanStopIds() {
      if (!this.currentDay) {
        return []
      }
      return this.currentDay.stops
        .filter((stop) => !this.planForStop(stop.id))
        .map((stop) => stop.id)
    },
    freePlans() {
      return this.childPlans.filter((plan) => !hasId(plan.routeStopId))
    },
    stickyLabel() {
      if (!this.focusedStop) {
        return ''
      }
      if (!this.focusedPlan) {
        return this.currentRoute?.status === 'ready'
          ? '为' + (this.focusedStop.attraction?.name || '这个景点') + '准备探索'
          : '编辑路线并准备探索'
      }
      if (this.focusedPlan.status === 'completed') {
        return '查看探索相册'
      }
      if (this.focusedPlan.status === 'ready') {
        return '开始' + (this.focusedStop.attraction?.name || '') + '探索'
      }
      if (this.focusedPlan.status === 'in-progress' && this.allFocusedTasksCompleted) {
        return '完成本次探索'
      }
      if (this.focusedPlan.status === 'in-progress' && this.nextTask) {
        return '继续下一个任务'
      }
      return '查看探索任务'
    },
    stickyBusy() {
      return this.isStartingPlan
        || this.isCompletingPlan
        || this.routeStore.isGeneratingPlans
        || this.taskStore.isLoading
        || this.taskStore.isGenerating
    },
  },
  onLoad(options) {
    this.selectedRouteId = String(options?.routeId || '').trim()
    this.selectedDayId = String(options?.dayId || '').trim()
    this.selectedStopId = String(options?.stopId || '').trim()
    this.preferredPlanId = String(options?.planId || '').trim()
  },
  async onShow() {
    await this.loadWorkbench(this.hasLoaded)
  },
  methods: {
    sameId,
    showToast(title) {
      uni.showToast({ title, icon: 'none' })
    },
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadWorkbench(force = false) {
      this.isBootstrapping = true
      this.pageError = ''
      try {
        if (!this.userStore.isAuthReady || this.userStore.isRestoring) {
          await this.userStore.restoreSession()
        }
        if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
          uni.reLaunch({ url: '/pages/login/index' })
          return
        }

        const userId = this.userStore.userInfo.id
        await Promise.all([
          this.childStore.fetchChildren(userId),
          this.routeStore.fetchRoutes(userId, { force }),
          this.planStore.fetchPlans(userId, { force, selectionPolicy: 'none' }),
        ])

        await this.resolveInitialFocus()
        this.hasLoaded = true
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.pageError = error?.message || '路线或探索内容加载失败，请稍后重试'
      } finally {
        this.isBootstrapping = false
      }
    },
    async resolveInitialFocus() {
      if (!this.routeStore.routes.length) {
        this.selectedRouteId = ''
        this.selectedDayId = ''
        this.selectedStopId = ''
        return
      }

      const preferredPlan = hasId(this.preferredPlanId)
        ? this.childPlans.find((plan) => sameId(plan.id, this.preferredPlanId))
        : null
      const activePlan = preferredPlan || this.childPlans.find((plan) => plan.status === 'in-progress') || null

      const requestedRouteExists = this.routeStore.routes.some((route) => sameId(route.id, this.selectedRouteId))
      const planRouteId = activePlan?.sourceSnapshot?.route?.id
      const routeId = requestedRouteExists
        ? this.selectedRouteId
        : hasId(planRouteId)
          ? planRouteId
          : this.routeStore.routes[0].id

      await this.selectRoute(routeId, { focusPlan: activePlan, preserveExistingFocus: true })
    },
    async selectRoute(routeId, options = {}) {
      if (!hasId(routeId)) {
        return
      }
      this.showRouteSwitcher = false
      this.selectedRouteId = String(routeId)
      const route = await this.routeStore.fetchRoute(routeId)
      if (!route) {
        return
      }

      const focusPlan = options.focusPlan || null
      const existingDay = options.preserveExistingFocus
        ? route.days.find((day) => sameId(day.id, this.selectedDayId))
        : null
      const focusDayId = sameId(focusPlan?.sourceSnapshot?.route?.id, route.id)
        ? focusPlan?.sourceSnapshot?.day?.id
        : null
      const planDay = route.days.find((day) => sameId(day.id, focusDayId))
      const today = new Date()
      const todayKey = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0'),
      ].join('-')
      const todayDay = route.days.find((day) => day.date === todayKey)
      const targetDay = existingDay || planDay || todayDay || route.days[0] || null

      if (!targetDay) {
        this.selectedDayId = ''
        this.selectedStopId = ''
        return
      }

      await this.selectDay(targetDay.id, { focusPlan, preserveExistingFocus: options.preserveExistingFocus })
    },
    async selectDay(dayId, options = {}) {
      const day = this.currentRoute?.days?.find((item) => sameId(item.id, dayId))
      if (!day) {
        return
      }
      this.selectedDayId = String(day.id)

      const existingStop = options.preserveExistingFocus
        ? day.stops.find((stop) => sameId(stop.id, this.selectedStopId))
        : null
      const focusStopId = sameId(options.focusPlan?.sourceSnapshot?.day?.id, day.id)
        ? options.focusPlan?.routeStopId
        : null
      const planStop = day.stops.find((stop) => sameId(stop.id, focusStopId))
      const firstIncomplete = day.stops.find((stop) => {
        const plan = this.planForStop(stop.id)
        return !plan || plan.status !== 'completed'
      })
      const targetStop = existingStop || planStop || firstIncomplete || day.stops[0] || null

      if (!targetStop) {
        this.selectedStopId = ''
        return
      }
      await this.focusStop(targetStop, day)
    },
    async focusStop(stop, day = this.currentDay) {
      if (!stop) {
        return
      }
      if (day?.id) {
        this.selectedDayId = String(day.id)
      }
      this.selectedStopId = String(stop.id)
      const plan = this.planForStop(stop.id)
      if (plan) {
        await this.preparePlan(plan)
      }
    },
    planForStop(stopId) {
      return this.routePlans.find((plan) => sameId(plan.routeStopId, stopId)) || null
    },
    planStatusKey(plan) {
      if (!plan) return 'missing'
      return plan.status || 'ready'
    },
    planStatusText(plan) {
      if (!plan) return '未生成'
      return {
        ready: '待开始',
        'in-progress': '探索中',
        completed: '已完成',
      }[plan.status] || plan.status
    },
    planProgressText(plan) {
      const completed = Number(plan?.progress?.completed) || 0
      const total = Number(plan?.progress?.total) || Number(plan?.taskCount) || 0
      return total ? completed + '/' + total + ' 已完成' : '探索内容已准备'
    },
    stopMeta(stop) {
      const parts = []
      if (stop.attraction?.district) {
        parts.push(stop.attraction.district)
      }
      if (stop.attraction?.recommendedDurationMinutes) {
        parts.push('约' + stop.attraction.recommendedDurationMinutes + '分钟')
      }
      return parts.join(' · ') || '点击查看探索安排'
    },
    async preparePlan(plan) {
      if (!plan?.id) {
        return
      }
      this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)
      try {
        await this.taskStore.ensureTasks(plan.id, plan.status)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '探索任务加载失败')
      }
    },
    async refreshPlansAndFocus() {
      await this.planStore.fetchPlans(this.userStore.userInfo.id, { force: true, selectionPolicy: 'none' })
      const plan = this.focusedStop ? this.planForStop(this.focusedStop.id) : null
      if (plan) {
        await this.preparePlan(plan)
      }
    },
    async generatePlanForStop(stop) {
      if (!this.activeChild) {
        this.showToast('请先在“我的”中选择孩子')
        return
      }
      if (this.currentRoute?.status !== 'ready') {
        this.showToast('请先编辑路线并标记为已准备')
        return
      }
      if (!stop?.id || this.routeStore.isGeneratingPlans) {
        return
      }

      this.isGeneratingStopId = String(stop.id)
      try {
        await this.routeStore.generateExplorationPlans(this.currentRoute.id, this.activeChild.id, [stop.id])
        await this.refreshPlansAndFocus()
        this.showToast('探索内容已准备好')
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '探索生成失败，请稍后重试')
      } finally {
        this.isGeneratingStopId = ''
      }
    },
    async generateTodayPlans() {
      if (!this.activeChild) {
        this.showToast('请先在“我的”中选择孩子')
        return
      }
      if (this.currentRoute?.status !== 'ready') {
        this.showToast('请先编辑路线并标记为已准备')
        return
      }
      if (!this.missingPlanStopIds.length || this.routeStore.isGeneratingPlans) {
        return
      }

      try {
        await this.routeStore.generateExplorationPlans(
          this.currentRoute.id,
          this.activeChild.id,
          [...this.missingPlanStopIds],
        )
        await this.refreshPlansAndFocus()
        this.showToast('今天的探索内容已准备好')
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '探索生成失败，请稍后重试')
      }
    },
    async startFocusedPlan() {
      if (!this.focusedPlan || this.isStartingPlan) {
        return
      }
      this.isStartingPlan = true
      try {
        const started = await this.planStore.startExploration(
          this.focusedPlan.id,
          this.userStore.userInfo?.id,
        )
        await this.taskStore.ensureTasks(started.id, started.status)
        await this.planStore.fetchPlans(this.userStore.userInfo.id, { force: true, selectionPolicy: 'none' })
        const refreshed = this.planForStop(this.selectedStopId)
        if (refreshed) {
          await this.preparePlan(refreshed)
        }
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '无法开始探索')
      } finally {
        this.isStartingPlan = false
      }
    },
    async completeFocusedPlan() {
      if (!this.focusedPlan || !this.allFocusedTasksCompleted || this.isCompletingPlan) {
        return
      }
      this.isCompletingPlan = true
      try {
        const completed = await this.planStore.completeExploration(
          this.focusedPlan.id,
          this.userStore.userInfo?.id,
        )
        if (completed?.id) {
          await this.recordStore.ensureJourneyRecord(completed.id)
        }
        await this.planStore.fetchPlans(this.userStore.userInfo.id, { force: true, selectionPolicy: 'none' })
        const refreshed = this.planForStop(this.selectedStopId)
        if (refreshed) {
          this.planStore.selectPlanById(refreshed.id, this.userStore.userInfo?.id)
        }
        this.showToast('这次探索已完成')
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '完成探索失败，请稍后重试')
      } finally {
        this.isCompletingPlan = false
      }
    },
    async handleStickyAction() {
      if (!this.focusedStop) {
        return
      }
      if (!this.focusedPlan) {
        if (this.currentRoute?.status === 'ready') {
          await this.generatePlanForStop(this.focusedStop)
        } else {
          this.editRoute()
        }
        return
      }
      if (this.focusedPlan.status === 'completed') {
        await this.openJourneyRecord(this.focusedPlan)
        return
      }
      if (this.focusedPlan.status === 'ready') {
        await this.startFocusedPlan()
        return
      }
      if (this.focusedPlan.status === 'in-progress' && this.allFocusedTasksCompleted) {
        await this.completeFocusedPlan()
        return
      }
      if (this.nextTask) {
        this.openTask(this.nextTask)
        return
      }
      if (this.focusedTasks[0]) {
        this.openTask(this.focusedTasks[0])
      }
    },
    openTask(task) {
      if (!task || !this.focusedPlan) {
        return
      }
      this.planStore.selectPlanById(this.focusedPlan.id, this.userStore.userInfo?.id)
      this.taskStore.setCurrentTask(task.id)
      uni.navigateTo({
        url: '/pages/task-detail/index?id=' + encodeURIComponent(String(task.id))
          + '&planId=' + encodeURIComponent(String(this.focusedPlan.id)),
      })
    },
    openGuide(plan) {
      if (!plan?.id) {
        return
      }
      this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)
      this.audioGuidePlanId = plan.id
      this.audioGuideOpen = true
    },
    async openJourneyRecord(plan) {
      if (!plan?.id) {
        return
      }
      try {
        await this.recordStore.ensureJourneyRecord(plan.id)
        uni.navigateTo({
          url: '/pages/record-detail/index?planId=' + encodeURIComponent(String(plan.id)),
        })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '成长记录暂时无法打开')
      }
    },
    openFreePlan(plan) {
      if (!plan?.id) {
        return
      }
      this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)
      uni.navigateTo({
        url: '/pages/tasks/index',
      })
    },
    editRoute() {
      if (!this.currentRoute?.id) {
        return
      }
      uni.navigateTo({
        url: '/pages/route-detail/index?id=' + encodeURIComponent(String(this.currentRoute.id)),
      })
    },
    formatRouteDates(startDate, endDate) {
      const compact = (value) => {
        const match = String(value || '').match(/^\d{4}-(\d{2})-(\d{2})/)
        return match ? Number(match[1]) + '月' + Number(match[2]) + '日' : ''
      }
      if (startDate && endDate) {
        return compact(startDate) + ' – ' + compact(endDate)
      }
      if (startDate) {
        return compact(startDate) + '出发'
      }
      return '日期待定'
    },
    formatDayDate(value) {
      const match = String(value || '').match(/^\d{4}-(\d{2})-(\d{2})/)
      return match ? Number(match[1]) + '月' + Number(match[2]) + '日' : '日期待定'
    },
    formatDayDateLong(value) {
      const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
      return match ? match[1] + '年' + Number(match[2]) + '月' + Number(match[3]) + '日' : '日期待定'
    },
    openCreateRouteSheet() {
      this.showRouteSwitcher = false
      this.showCreateRouteSheet = true
      this.createError = ''
    },
    closeCreateRouteSheet() {
      if (this.isCreatingRoute) {
        return
      }
      this.showCreateRouteSheet = false
      this.createForm = emptyCreateForm()
      this.createError = ''
    },
    setCreateDate(field, event) {
      this.createForm[field] = event?.detail?.value || ''
    },
    async createRoute() {
      if (this.isCreatingRoute) {
        return
      }
      const title = this.createForm.title.trim()
      const city = this.createForm.city.trim()
      if (!title || !city) {
        this.createError = '请填写路线名称和城市'
        return
      }
      if (this.createForm.startDate && this.createForm.endDate && this.createForm.endDate < this.createForm.startDate) {
        this.createError = '结束日期不能早于开始日期'
        return
      }

      const payload = { title, city }
      if (this.createForm.startDate) payload.startDate = this.createForm.startDate
      if (this.createForm.endDate) payload.endDate = this.createForm.endDate

      this.isCreatingRoute = true
      this.createError = ''
      try {
        const route = await this.routeStore.createRoute(payload)
        this.showCreateRouteSheet = false
        this.createForm = emptyCreateForm()
        if (route?.id) {
          this.selectedRouteId = String(route.id)
          await this.selectRoute(route.id)
          this.editRoute()
        }
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
          return
        }
        this.createError = error?.message || '路线创建失败，请稍后重试'
      } finally {
        this.isCreatingRoute = false
      }
    },
  },
}
</script>

<style scoped>
.explore-workbench {
  min-height: 100vh;
  color: var(--tl-text-main);
  background: #fbf7ec;
}

.explore-workbench__paper {
  width: 100%;
  max-width: var(--tl-content-max-width);
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(22rpx + var(--tl-safe-top)) 24rpx calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 170rpx);
  box-sizing: border-box;
}

.workbench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 88rpx;
  margin-bottom: 18rpx;
}

.workbench-header__logo {
  width: 222rpx;
  height: auto;
}

.workbench-header__tools {
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.header-tool {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72rpx;
  height: 72rpx;
  padding: 0;
  color: #2f2a25;
  background: transparent;
}

.header-tool__search {
  width: 28rpx;
  height: 28rpx;
  border: 4rpx solid currentColor;
  border-radius: 50%;
}

.header-tool__search::after {
  position: absolute;
  right: 17rpx;
  bottom: 15rpx;
  width: 16rpx;
  height: 4rpx;
  content: '';
  background: currentColor;
  border-radius: 999rpx;
  transform: rotate(45deg);
}

.header-tool__bell {
  position: relative;
  width: 29rpx;
  height: 31rpx;
  border: 4rpx solid currentColor;
  border-top-left-radius: 16rpx;
  border-top-right-radius: 16rpx;
  border-bottom: 0;
}

.header-tool__bell::after {
  position: absolute;
  right: 5rpx;
  bottom: -10rpx;
  left: 5rpx;
  height: 4rpx;
  content: '';
  background: currentColor;
  border-radius: 999rpx;
}

.header-tool__dot {
  position: absolute;
  top: 11rpx;
  right: 10rpx;
  width: 12rpx;
  height: 12rpx;
  background: #f26a21;
  border: 3rpx solid #fbf7ec;
  border-radius: 50%;
}

.route-hero {
  position: relative;
  overflow: hidden;
  border-radius: 28rpx;
  background: #59311f;
}

.route-hero__image {
  width: 100%;
  height: 310rpx;
  display: block;
}

.route-hero__veil {
  position: absolute;
  inset: 0 0 112rpx;
  background: linear-gradient(90deg, rgba(44, 24, 15, .86) 0%, rgba(44, 24, 15, .48) 54%, rgba(44, 24, 15, .06) 100%);
}

.route-hero__content {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  min-height: 198rpx;
  padding: 30rpx 30rpx 20rpx;
  color: #fffdf8;
}

.route-hero__switch,
.route-hero__edit {
  position: absolute;
  right: 22rpx;
  min-height: 54rpx;
  padding: 0 18rpx;
  font-size: 22rpx;
  line-height: 54rpx;
  color: #fff;
  background: rgba(39, 35, 31, .52);
  border: 1rpx solid rgba(255, 255, 255, .45);
  border-radius: 999rpx;
}

.route-hero__switch {
  top: 20rpx;
}

.route-hero__edit {
  top: 86rpx;
}

.route-hero__title {
  display: block;
  max-width: 76%;
  margin-top: 58rpx;
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1.22;
}

.route-hero__meta,
.route-hero__child {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  line-height: 1.35;
}

.route-hero__child {
  font-size: 22rpx;
  opacity: .9;
}

.route-stats {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  min-height: 112rpx;
  background: #fffdfa;
}

.route-stats__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.route-stats__item + .route-stats__item::before {
  position: absolute;
  top: 25rpx;
  bottom: 25rpx;
  left: 0;
  width: 1rpx;
  content: '';
  background: rgba(81, 63, 49, .12);
}

.route-stats__value {
  font-size: 31rpx;
  font-weight: 700;
}

.route-stats__label {
  margin-top: 5rpx;
  font-size: 19rpx;
  color: #78695c;
}

.day-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
  margin: 24rpx 0;
}

.day-tab {
  min-height: 88rpx;
  padding: 12rpx;
  color: #4a4037;
  background: #fffdfa;
  border: 1rpx solid rgba(73, 59, 48, .12);
  border-radius: 18rpx;
}

.day-tab--active {
  color: #17683a;
  border: 2rpx solid #2d8b52;
}

.day-tab__title,
.day-tab__date {
  display: block;
}

.day-tab__title {
  font-size: 24rpx;
  font-weight: 700;
}

.day-tab__date {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: inherit;
  opacity: .78;
}

.day-heading,
.free-section__heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20rpx;
  margin: 30rpx 4rpx 16rpx;
}

.day-heading__title,
.free-section__title {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
}

.day-heading__meta,
.free-section__copy {
  display: block;
  margin-top: 5rpx;
  font-size: 21rpx;
  color: #7d6d60;
}

.day-heading__action {
  flex: 0 0 auto;
  min-height: 60rpx;
  padding: 0 18rpx;
  font-size: 21rpx;
  font-weight: 600;
  line-height: 60rpx;
  color: #1c7541;
  background: #eef8ef;
  border: 1rpx solid rgba(45, 139, 82, .35);
  border-radius: 999rpx;
}

.stop-list {
  overflow: hidden;
  background: #fffdfa;
  border: 1rpx solid rgba(73, 59, 48, .1);
  border-radius: 24rpx;
}

.stop-block + .stop-block {
  border-top: 1rpx solid rgba(73, 59, 48, .1);
}

.stop-block--focused {
  background: #fffefb;
}

.stop-summary {
  display: flex;
  align-items: center;
  gap: 16rpx;
  min-height: 118rpx;
  padding: 18rpx;
}

.stop-summary__number {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 44rpx;
  height: 44rpx;
  font-size: 22rpx;
  font-weight: 700;
  color: #fff;
  background: #248249;
  border-radius: 50%;
}

.stop-summary__image {
  flex: 0 0 auto;
  width: 94rpx;
  height: 80rpx;
  border-radius: 14rpx;
}

.stop-summary__image--placeholder {
  background: #eadfca;
}

.stop-summary__copy {
  flex: 1;
  min-width: 0;
}

.stop-summary__topline {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.stop-summary__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 29rpx;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stop-summary__meta,
.stop-summary__progress {
  display: block;
  margin-top: 5rpx;
  font-size: 21rpx;
  color: #7d6d60;
}

.stop-summary__progress {
  color: #2d7b49;
}

.stop-summary__arrow {
  flex: 0 0 auto;
  font-size: 34rpx;
  color: #817568;
}

.plan-status {
  flex: 0 0 auto;
  padding: 7rpx 11rpx;
  font-size: 18rpx;
  font-weight: 600;
  border-radius: 999rpx;
}

.plan-status--in-progress {
  color: #17683a;
  background: #e9f6e9;
}

.plan-status--ready {
  color: #2c6f97;
  background: #eaf4fb;
}

.plan-status--completed {
  color: #55753c;
  background: #edf5e5;
}

.plan-status--missing {
  color: #7b746d;
  background: #f1efec;
}

.stop-detail {
  padding: 0 18rpx 22rpx 78rpx;
}

.stop-detail__summary,
.stop-detail__note {
  display: block;
  font-size: 23rpx;
  line-height: 1.65;
  color: #6f6155;
}

.stop-detail__note {
  margin-top: 8rpx;
  color: #98612e;
}

.plan-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  padding: 20rpx;
  margin-top: 16rpx;
  background: #f8f4e9;
  border-radius: 18rpx;
}

.plan-empty__title,
.plan-empty__copy {
  display: block;
}

.plan-empty__title {
  font-size: 24rpx;
  font-weight: 700;
}

.plan-empty__copy {
  margin-top: 5rpx;
  font-size: 20rpx;
  line-height: 1.45;
  color: #7d6d60;
}

.plan-empty__button {
  flex: 0 0 auto;
  min-height: 64rpx;
  padding: 0 18rpx;
  font-size: 22rpx;
  font-weight: 700;
  line-height: 64rpx;
  color: #17683a;
  background: #fff;
  border: 2rpx solid #2d8b52;
  border-radius: 999rpx;
}

.plan-empty__button--quiet {
  color: #695b4f;
  border-color: rgba(73, 59, 48, .25);
}

.task-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 20rpx;
}

.task-heading__title,
.task-heading__meta {
  display: block;
}

.task-heading__title {
  font-size: 27rpx;
  font-weight: 700;
}

.task-heading__meta {
  margin-top: 4rpx;
  font-size: 19rpx;
  color: #817365;
}

.task-heading__guide {
  flex: 0 0 auto;
  min-height: 60rpx;
  padding: 0 16rpx;
  font-size: 21rpx;
  font-weight: 700;
  line-height: 60rpx;
  color: #17683a;
  background: #f2faf2;
  border: 2rpx solid rgba(45, 139, 82, .55);
  border-radius: 999rpx;
}

.task-list {
  margin-top: 12rpx;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
  width: 100%;
  min-height: 84rpx;
  padding: 12rpx 8rpx;
  text-align: left;
  color: #3f342b;
  background: transparent;
  border-top: 1rpx solid rgba(73, 59, 48, .08);
}

.task-row__check {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 38rpx;
  height: 38rpx;
  font-size: 22rpx;
  color: #fff;
  border: 2rpx solid #aeb3ad;
  border-radius: 50%;
}

.task-row--done .task-row__check {
  background: #2d8b52;
  border-color: #2d8b52;
}

.task-row__copy {
  flex: 1;
  min-width: 0;
}

.task-row__title,
.task-row__summary {
  display: block;
}

.task-row__title {
  font-size: 24rpx;
  font-weight: 700;
}

.task-row__summary {
  margin-top: 4rpx;
  overflow: hidden;
  font-size: 19rpx;
  color: #817365;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-row__arrow {
  flex: 0 0 auto;
  font-size: 32rpx;
  color: #8f8175;
}

.task-loading,
.task-empty {
  padding: 24rpx 4rpx 8rpx;
  font-size: 21rpx;
  color: #817365;
}

.add-stop-action {
  width: 100%;
  min-height: 82rpx;
  margin-top: 14rpx;
  font-size: 23rpx;
  font-weight: 600;
  color: #4f463e;
  background: #fffdfa;
  border: 1rpx solid rgba(73, 59, 48, .12);
  border-radius: 18rpx;
}

.free-section {
  margin-top: 34rpx;
}

.free-plan {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 94rpx;
  padding: 14rpx 18rpx;
  text-align: left;
  background: #fffdfa;
  border-top: 1rpx solid rgba(73, 59, 48, .1);
}

.free-plan__title,
.free-plan__meta {
  display: block;
}

.free-plan__title {
  font-size: 25rpx;
  font-weight: 700;
}

.free-plan__meta {
  margin-top: 5rpx;
  font-size: 20rpx;
  color: #817365;
}

.free-plan__arrow {
  font-size: 34rpx;
  color: #8f8175;
}

.sticky-action {
  position: fixed;
  right: 0;
  bottom: calc(var(--tl-tabbar-height) + var(--tl-safe-bottom));
  left: 0;
  z-index: 45;
  padding: 14rpx 24rpx;
  background: rgba(251, 247, 236, .96);
  border-top: 1rpx solid rgba(73, 59, 48, .09);
  backdrop-filter: blur(12px);
}

.sticky-action__button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  width: 100%;
  max-width: 390px;
  min-height: 82rpx;
  margin: 0 auto;
  font-size: 26rpx;
  font-weight: 700;
  color: #fff;
  background: #238248;
  border-radius: 999rpx;
}

.sticky-action__button[disabled] {
  opacity: .65;
}

.sticky-action__arrow {
  font-size: 34rpx;
}

.workbench-state {
  padding: 64rpx 28rpx;
  text-align: center;
  background: #fffdfa;
  border: 1rpx solid rgba(73, 59, 48, .12);
  border-radius: 24rpx;
}

.workbench-state--inline {
  margin-top: 20rpx;
  padding: 44rpx 24rpx;
}

.workbench-state__title,
.workbench-state__copy {
  display: block;
}

.workbench-state__title {
  font-size: 30rpx;
  font-weight: 700;
}

.workbench-state__copy {
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: #817365;
}

.workbench-state__button {
  min-height: 74rpx;
  padding: 0 26rpx;
  margin-top: 24rpx;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 74rpx;
  color: #fff;
  background: #238248;
  border-radius: 999rpx;
}

.workbench-state__button--quiet {
  color: #17683a;
  background: #f1f8f1;
  border: 1rpx solid rgba(45, 139, 82, .35);
}

.sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: flex;
  align-items: flex-end;
  background: rgba(43, 34, 28, .34);
}

.sheet-panel {
  width: 100%;
  max-width: var(--tl-content-max-width);
  max-height: 82vh;
  padding: 24rpx 28rpx calc(28rpx + var(--tl-safe-bottom));
  margin: 0 auto;
  overflow-y: auto;
  background: #fffdfa;
  border-radius: 30rpx 30rpx 0 0;
  box-sizing: border-box;
}

.sheet-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22rpx;
}

.sheet-panel__head text {
  font-size: 32rpx;
  font-weight: 700;
}

.sheet-panel__head button {
  min-height: 58rpx;
  padding: 0 14rpx;
  font-size: 22rpx;
  color: #72665b;
}

.route-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 94rpx;
  padding: 14rpx 8rpx;
  text-align: left;
  border-top: 1rpx solid rgba(73, 59, 48, .09);
}

.route-option__title,
.route-option__meta {
  display: block;
}

.route-option__title {
  font-size: 25rpx;
  font-weight: 700;
}

.route-option__meta {
  margin-top: 5rpx;
  font-size: 20rpx;
  color: #817365;
}

.route-option__current {
  flex: 0 0 auto;
  padding: 6rpx 10rpx;
  font-size: 18rpx;
  color: #17683a;
  background: #eaf6eb;
  border-radius: 999rpx;
}

.sheet-panel__primary {
  width: 100%;
  min-height: 82rpx;
  margin-top: 22rpx;
  font-size: 25rpx;
  font-weight: 700;
  color: #fff;
  background: #238248;
  border-radius: 999rpx;
}

.form-field {
  margin-bottom: 18rpx;
}

.form-field > text {
  display: block;
  margin-bottom: 8rpx;
  font-size: 22rpx;
  font-weight: 600;
  color: #6f6256;
}

.form-field input,
.form-field__picker {
  min-height: 76rpx;
  padding: 0 18rpx;
  font-size: 24rpx;
  line-height: 76rpx;
  background: #f8f4e9;
  border: 1rpx solid rgba(73, 59, 48, .12);
  border-radius: 16rpx;
}

.form-error {
  display: block;
  margin-top: 8rpx;
  font-size: 21rpx;
  color: #b64931;
}

@media (min-width: 431px) {
  .explore-workbench__paper {
    padding-right: 16px;
    padding-left: 16px;
  }

  .sticky-action {
    padding-right: calc((100vw - 430px) / 2 + 16px);
    padding-left: calc((100vw - 430px) / 2 + 16px);
  }
}
</style>
