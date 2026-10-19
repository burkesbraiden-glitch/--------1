<template>
  <view class="explore-workbench-page">
    <view class="explore-workbench-page__paper">
      <view v-if="isPageLoading" class="workbench-skeletons" aria-label="正在整理这次行程">
        <AppSkeleton class="workbench-skeleton workbench-skeleton--hero" variant="block" />
        <AppSkeleton v-for="item in 2" :key="item" class="workbench-skeleton" variant="block" />
      </view>

      <PageState
        v-else-if="showFullPageError"
        type="error"
        title="探索工作台暂时打不开"
        :description="pageError"
        action-text="重新加载"
        :disabled="isLoadingWorkbench"
        @action="loadWorkbench(true)"
      />

      <template v-else>
        <view v-if="pageError" class="workbench-refresh-error" role="alert">
          <text>加载最新探索内容失败，当前仍显示上次内容。</text>
          <button class="tl-pressable" :disabled="isLoadingWorkbench" @click="loadWorkbench(true)">
            {{ isLoadingWorkbench ? '正在加载…' : '重新加载' }}
          </button>
        </view>

        <PageState
          v-if="!currentRoute"
          type="empty"
          title="从一条路线开始探索"
          description="安排每天要去的景点，再为每一站准备孩子的探索内容。"
          action-text="创建路线"
          @action="goRoutePlanning"
        />

        <template v-else>
          <view class="route-overview" :class="{ 'route-overview--with-image': Boolean(routeHeroImage) }">
          <image
            v-if="routeHeroImage"
            class="route-overview__image"
            :src="routeHeroImage"
            mode="aspectFill"
          />
          <view v-if="routeHeroImage" class="route-overview__shade"></view>
          <view class="route-overview__content">
            <view class="route-overview__actions">
              <button class="route-overview__text-action route-overview__text-action--switch tl-pressable" @click="showRoutePicker = true">切换路线</button>
              <button class="route-overview__text-action route-overview__text-action--edit tl-pressable" @click="editCurrentRoute">编辑路线</button>
            </view>
            <text class="route-overview__title">{{ currentRoute.title }}</text>
            <text class="route-overview__meta">{{ routeMeta }}</text>
          </view>
        </view>

        <view class="route-stats" aria-label="当前路线统计">
          <view class="route-stats__item">
            <text class="route-stats__number">{{ routeStats.days }}</text>
            <text class="route-stats__label">天行程</text>
          </view>
          <view class="route-stats__item">
            <text class="route-stats__number">{{ routeStats.stops }}</text>
            <text class="route-stats__label">个景点</text>
          </view>
          <view class="route-stats__item">
            <text class="route-stats__number">{{ routeStats.plans }}</text>
            <text class="route-stats__label">个探索计划</text>
          </view>
          <view class="route-stats__item">
            <text class="route-stats__number">{{ routeStats.tasks }}</text>
            <text class="route-stats__label">个探索任务</text>
          </view>
        </view>

        <scroll-view v-if="hasMultipleDays" class="day-tabs" scroll-x :show-scrollbar="false">
          <view class="day-tabs__inner">
            <button
              v-for="day in currentRoute.days"
              :key="day.id"
              class="day-tab tl-pressable tl-selected-transition"
              :class="{ 'day-tab--active': sameId(activeDayId, day.id) }"
              @click="selectDay(day)"
            >
              <text class="day-tab__title">第{{ day.dayNumber }}天</text>
              <text class="day-tab__date">{{ formatDayDate(day.date) }}</text>
            </button>
          </view>
        </scroll-view>

        <view v-if="activeDay" class="day-content">
          <view class="day-content__heading">
            <view class="day-content__heading-copy">
              <text class="day-content__title">{{ activeDayLabel }}</text>
              <text v-if="hasDistinctActiveDayTitle" class="day-content__subtitle">{{ activeDay.title }}</text>
            </view>
            <button
              v-if="missingPlanStopIds.length"
                class="day-content__prepare tl-pressable"
              :disabled="isPreparingDay"
              @click="prepareActiveDay"
            >
              {{ isPreparingDay ? '正在准备…' : '准备今日探索' }}
            </button>
          </view>

          <view v-if="!activeDay.stops.length" class="day-empty">
            <text>这一天还没有景点安排。</text>
          </view>

          <view v-else class="stop-list">
            <view v-for="(stop, index) in activeDay.stops" :key="stop.id" class="stop-block">
              <view class="stop-block__rail" aria-hidden="true">
                <text>{{ index + 1 }}</text>
              </view>
              <view class="stop-block__main">
                <view
                  class="stop-summary tl-pressable tl-selected-transition"
                  :class="{ 'stop-summary--active': isFocusedStop(stop.id) }"
                  @click="focusStop(stop, activeDay)"
                >
                  <image
                    v-if="stop.attraction?.coverImage"
                    class="stop-summary__image"
                    :src="stop.attraction.coverImage"
                    mode="aspectFill"
                  />
                  <view v-else class="stop-summary__image stop-summary__image--blank" aria-hidden="true"></view>
                  <view class="stop-summary__copy">
                    <view class="stop-summary__title-row">
                      <text class="stop-summary__title">{{ stop.attraction?.name || '未命名景点' }}</text>
                      <text class="status-chip" :class="`status-chip--${planStatusKey(planForStop(stop.id))}`">
                        {{ planStatusLabel(planForStop(stop.id)) }}
                      </text>
                    </view>
                    <view class="stop-summary__meta">
                      <text>{{ stopTime(stop) }}</text>
                      <text>{{ planProgressText(planForStop(stop.id)) }}</text>
                    </view>
                    <text v-if="stop.attraction?.summary" class="stop-summary__summary">{{ stop.attraction.summary }}</text>
                  </view>
                  <text class="stop-summary__arrow">{{ isFocusedStop(stop.id) ? '⌃' : '›' }}</text>
                </view>

                <view v-if="isFocusedStop(stop.id)" class="stop-expanded">
                  <template v-if="planForStop(stop.id)">
                    <view class="stop-expanded__task-head">
                      <text>探索任务</text>
                      <button class="stop-expanded__guide tl-pressable" @click="openGuide(planForStop(stop.id))">听讲解</button>
                    </view>

                    <view v-if="taskStore.isLoading && !activeTasks.length" class="task-state">正在准备这个景点的任务…</view>
                    <view v-else-if="taskStore.error" class="task-state task-state--error">
                      <text>任务暂时加载失败</text>
                      <button class="tl-pressable" @click="focusStop(stop, activeDay)">重试</button>
                    </view>
                    <view v-else-if="!activeTasks.length" class="task-state">这次探索还没有可用任务。</view>
                    <view v-else class="task-list">
                      <view
                        v-for="task in activeTasks"
                        :key="task.id"
                        class="task-row tl-pressable tl-selected-transition"
                        :class="{ 'task-row--completed': task.status === 'completed' }"
                        @click="openTask(task)"
                      >
                        <view class="task-row__mark" aria-hidden="true"><text v-if="task.status === 'completed'">✓</text></view>
                        <view class="task-row__copy">
                          <text class="task-row__title">{{ task.title }}</text>
                          <text v-if="task.subtitle || task.summary" class="task-row__desc">{{ task.subtitle || task.summary }}</text>
                        </view>
                        <text class="task-row__arrow">›</text>
                      </view>
                    </view>
                  </template>

                  <view v-else class="plan-missing">
                    <text class="plan-missing__title">未生成</text>
                    <text class="plan-missing__copy">先为这个景点准备一份探索内容。</text>
                    <button class="tl-pressable" :disabled="isGeneratingStop(stop.id)" @click="generatePlanForStop(stop)">
                      {{ isGeneratingStop(stop.id) ? '正在生成…' : '生成探索' }}
                    </button>
                  </view>
                </view>
              </view>
            </view>
          </view>
        </view>

        <view v-if="freeExplorationPlans.length" class="free-explorations">
          <text class="free-explorations__title">自由探索</text>
          <text class="free-explorations__note">未加入当前路线的探索</text>
          <view v-for="plan in freeExplorationPlans" :key="plan.id" class="free-exploration tl-pressable" @click="openFreePlan(plan)">
            <view>
              <text class="free-exploration__title">{{ plan.title }}</text>
              <text class="free-exploration__meta">{{ plan.destination }} · {{ planProgressText(plan) }}</text>
            </view>
            <text>›</text>
          </view>
        </view>
        </template>
      </template>
    </view>

    <view v-if="primaryAction" class="workbench-primary-action">
      <button class="tl-pressable" :disabled="primaryAction.disabled" @click="handlePrimaryAction">{{ primaryAction.label }}</button>
    </view>

    <view v-if="showRoutePicker" class="route-picker-mask" @click="showRoutePicker = false">
      <view class="route-picker" @click.stop>
        <text class="route-picker__title">切换路线</text>
        <button
          v-for="route in routeStore.routes"
          :key="route.id"
              class="route-picker__item tl-pressable tl-selected-transition"
          :class="{ 'route-picker__item--active': sameId(currentRoute?.id, route.id) }"
          @click="changeRoute(route.id)"
        >
          <view>
            <text>{{ route.title }}</text>
            <text>{{ formatRouteDateRange(route.startDate, route.endDate) }}</text>
          </view>
          <text v-if="sameId(currentRoute?.id, route.id)">✓</text>
        </button>
      </view>
    </view>

    <AudioGuideSheet v-model:open="audioGuideOpen" :plan-id="audioGuidePlanId" />
    <AppTabbar active="explore" />
  </view>
</template>

<script>
import AudioGuideSheet from '../../components/AudioGuideSheet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { useChildStore } from '../../stores/child'
import { usePlanStore } from '../../stores/plan'
import { useRouteStore } from '../../stores/route'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request'
import { endUserSession } from '../../utils/sessionBoundary'
import AppSkeleton from '../../components/ui/AppSkeleton.vue'
import PageState from '../../components/ui/PageState.vue'

function sameId(left, right) {
  return left !== null && left !== undefined && right !== null && right !== undefined && String(left) === String(right)
}

function validId(value) {
  return value !== null && value !== undefined && String(value).trim() !== ''
}

export default {
  components: { AppSkeleton, AudioGuideSheet, AppTabbar, PageState },
  data() {
    return {
      requestedRouteId: '',
      requestedDayId: '',
      requestedStopId: '',
      requestedPlanId: '',
      selectedRouteId: '',
      activeDayId: '',
      activeStopId: '',
      isLoadingWorkbench: false,
      pageError: '',
      generatingStopId: null,
      isPreparingDay: false,
      isStartingExploration: false,
      audioGuideOpen: false,
      audioGuidePlanId: null,
      showRoutePicker: false,
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
    isPageLoading() {
      return (this.isLoadingWorkbench || this.userStore.isRestoring) && !this.currentRoute
    },
    showFullPageError() {
      return Boolean(this.pageError) && !this.currentRoute
    },
    currentRoute() {
      const routeId = this.selectedRouteId || this.requestedRouteId
      if (!routeId) return null
      return this.routeStore.routes.find((route) => sameId(route.id, routeId))
        || (sameId(this.routeStore.currentRoute?.id, routeId) ? this.routeStore.currentRoute : null)
    },
    plansForCurrentChild() {
      const childId = this.childStore.activeChild?.id
      if (!validId(childId)) return this.planStore.plans
      return this.planStore.plans.filter((plan) => sameId(plan.childId, childId))
    },
    currentRouteStopIds() {
      return new Set((this.currentRoute?.days || []).flatMap((day) => day.stops || []).map((stop) => String(stop.id)))
    },
    routePlans() {
      return this.plansForCurrentChild.filter((plan) => this.currentRouteStopIds.has(String(plan.routeStopId)))
    },
    activeDay() {
      return this.currentRoute?.days?.find((day) => sameId(day.id, this.activeDayId)) || null
    },
    hasMultipleDays() {
      return (this.currentRoute?.days?.length || 0) > 1
    },
    activeDayLabel() {
      if (!this.activeDay) return ''
      return `第${this.activeDay.dayNumber}天 · ${this.formatDayDate(this.activeDay.date)}`
    },
    hasDistinctActiveDayTitle() {
      const title = String(this.activeDay?.title || '').trim()
      if (!title) return false
      return !(this.activeDay?.stops || []).some((stop) => {
        const stopName = String(stop.attraction?.name || '').trim()
        return stopName && (stopName.includes(title) || title.includes(stopName))
      })
    },
    activeStop() {
      return this.activeDay?.stops?.find((stop) => sameId(stop.id, this.activeStopId)) || null
    },
    activePlan() {
      return this.activeStop ? this.planForStop(this.activeStop.id) : null
    },
    activeTasks() {
      return this.activePlan ? this.taskStore.displayTasksForPlan(this.activePlan.id) : []
    },
    routeStats() {
      const days = this.currentRoute?.days || []
      const stops = days.flatMap((day) => day.stops || [])
      return {
        days: days.length,
        stops: stops.length,
        plans: this.routePlans.length,
        tasks: this.routePlans.reduce((total, plan) => total + (Number(plan.taskCount) || 0), 0),
      }
    },
    routeMeta() {
      return `${this.currentRoute?.city || '城市待定'} · ${this.formatRouteDateRange(this.currentRoute?.startDate, this.currentRoute?.endDate)}`
    },
    routeHeroImage() {
      const stops = (this.currentRoute?.days || []).flatMap((day) => day.stops || [])
      return this.activeStop?.attraction?.coverImage || stops.find((stop) => stop.attraction?.coverImage)?.attraction?.coverImage || ''
    },
    missingPlanStopIds() {
      return (this.activeDay?.stops || [])
        .filter((stop) => !this.planForStop(stop.id))
        .map((stop) => stop.id)
    },
    freeExplorationPlans() {
      return this.plansForCurrentChild.filter((plan) => !validId(plan.routeStopId))
    },
    primaryAction() {
      const stop = this.activeStop
      const plan = this.activePlan
      if (!stop) return null
      const name = stop.attraction?.name || '这个景点'
      if (!plan) return { label: `为${name}准备探索`, type: 'generate', disabled: this.isGeneratingStop(stop.id) }
      if (plan.status === 'ready') return { label: `开始${name}探索`, type: 'start', disabled: this.isStartingExploration }
      if (plan.status === 'in-progress') {
        const nextTask = this.activeTasks.find((task) => task.status !== 'completed')
        if (nextTask) return { label: '继续下一个任务', type: 'task', task: nextTask, disabled: false }
        return { label: '完成本次探索', type: 'complete', disabled: this.planStore.isCompleting }
      }
      if (plan.status === 'completed') return { label: '查看探索相册', type: 'record', disabled: false }
      return null
    },
  },
  onLoad(options) {
    this.requestedRouteId = String(options?.routeId || '').trim()
    this.requestedDayId = String(options?.dayId || '').trim()
    this.requestedStopId = String(options?.stopId || '').trim()
    this.requestedPlanId = String(options?.planId || '').trim()
  },
  async onShow() {
    await this.loadWorkbench(true)
  },
  methods: {
    sameId,
    showToast(title) {
      uni.showToast({ title, icon: 'none' })
    },
    async loadWorkbench(force = false) {
      if (this.isLoadingWorkbench) return
      this.isLoadingWorkbench = true
      this.pageError = ''
      try {
        if (!this.userStore.isAuthReady || this.userStore.isRestoring) {
          await this.userStore.restoreSession()
        }
        const userId = this.userStore.userInfo?.id
        if (!this.userStore.isLoggedIn || !userId) {
          uni.reLaunch({ url: '/pages/login/index' })
          return
        }

        await Promise.all([
          this.routeStore.fetchRoutes(userId, { force }),
          this.planStore.fetchPlans(userId, { force, selectionPolicy: 'none' }),
          this.childStore.fetchChildren(userId),
        ])

        const routeId = this.resolveRouteId()
        if (!routeId) {
          this.selectedRouteId = ''
          this.activeDayId = ''
          this.activeStopId = ''
          return
        }

        this.selectedRouteId = String(routeId)
        await this.routeStore.fetchRoute(routeId)
        await this.applyInitialFocus()
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.pageError = '请检查网络后再试一次。'
      } finally {
        this.isLoadingWorkbench = false
      }
    },
    resolveRouteId() {
      const routes = this.routeStore.routes || []
      const belongsToRoutes = (routeId) => routes.some((route) => sameId(route.id, routeId))
      if (validId(this.requestedRouteId) && belongsToRoutes(this.requestedRouteId)) return this.requestedRouteId

      const requestedPlan = this.planStore.plans.find((plan) => sameId(plan.id, this.requestedPlanId))
      const requestedPlanRouteId = requestedPlan?.sourceSnapshot?.route?.id
      if (validId(requestedPlanRouteId) && belongsToRoutes(requestedPlanRouteId)) return requestedPlanRouteId

      const inProgressPlan = this.plansForCurrentChild.find((plan) => plan.status === 'in-progress' && validId(plan.sourceSnapshot?.route?.id))
      if (validId(inProgressPlan?.sourceSnapshot?.route?.id) && belongsToRoutes(inProgressPlan.sourceSnapshot.route.id)) {
        return inProgressPlan.sourceSnapshot.route.id
      }

      if (validId(this.routeStore.currentRoute?.id) && belongsToRoutes(this.routeStore.currentRoute.id)) {
        return this.routeStore.currentRoute.id
      }
      return routes[0]?.id || null
    },
    async applyInitialFocus() {
      const route = this.currentRoute
      if (!route?.days?.length) {
        this.activeDayId = ''
        this.activeStopId = ''
        return
      }

      const requestedPlan = this.planStore.plans.find((plan) => sameId(plan.id, this.requestedPlanId))
      const requestedStopId = this.requestedStopId || requestedPlan?.routeStopId
      let day = route.days.find((item) => sameId(item.id, this.requestedDayId)) || null
      let stop = null

      if (validId(requestedStopId)) {
        day = route.days.find((item) => item.stops?.some((itemStop) => sameId(itemStop.id, requestedStopId))) || day
        stop = day?.stops?.find((itemStop) => sameId(itemStop.id, requestedStopId)) || null
      }

      if (!stop) {
        const inProgressPlan = this.routePlans.find((plan) => plan.status === 'in-progress')
        if (inProgressPlan) {
          day = route.days.find((item) => item.stops?.some((itemStop) => sameId(itemStop.id, inProgressPlan.routeStopId))) || day
          stop = day?.stops?.find((itemStop) => sameId(itemStop.id, inProgressPlan.routeStopId)) || null
        }
      }

      if (!stop) {
        const today = this.localToday()
        const todayDay = route.days.find((item) => item.date === today)
        const unfinishedStop = todayDay?.stops?.find((itemStop) => this.planForStop(itemStop.id)?.status !== 'completed')
        if (unfinishedStop) {
          day = todayDay
          stop = unfinishedStop
        }
      }

      if (!stop) {
        day = day || route.days.find((item) => item.stops?.some((itemStop) => this.planForStop(itemStop.id))) || route.days[0]
        stop = day?.stops?.find((itemStop) => this.planForStop(itemStop.id)) || day?.stops?.[0] || null
      }

      this.activeDayId = day?.id || ''
      if (stop) {
        await this.focusStop(stop, day)
      } else {
        this.activeStopId = ''
      }
    },
    planForStop(stopId) {
      return this.plansForCurrentChild.find((plan) => sameId(plan.routeStopId, stopId)) || null
    },
    async selectDay(day) {
      if (!day) return
      this.activeDayId = day.id
      const inProgressStop = day.stops?.find((stop) => this.planForStop(stop.id)?.status === 'in-progress')
      const firstPlannedStop = day.stops?.find((stop) => this.planForStop(stop.id))
      const stop = inProgressStop || firstPlannedStop || day.stops?.[0]
      if (stop) await this.focusStop(stop, day)
    },
    async focusStop(stop, day = this.activeDay) {
      if (!stop) return
      if (day) this.activeDayId = day.id
      this.activeStopId = stop.id
      const plan = this.planForStop(stop.id)
      if (!plan) return
      this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)
      try {
        await this.taskStore.ensureTasks(plan.id, plan.status)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
        }
      }
    },
    isFocusedStop(stopId) {
      return sameId(this.activeStopId, stopId)
    },
    planStatusKey(plan) {
      return plan?.status || 'missing'
    },
    planStatusLabel(plan) {
      return { ready: '待开始', 'in-progress': '探索中', completed: '已完成' }[plan?.status] || '未生成'
    },
    planProgressText(plan) {
      if (!plan) return '尚未准备探索内容'
      const progress = plan.progress || { completed: 0, total: plan.taskCount || 0 }
      return `${progress.completed || 0}/${progress.total || plan.taskCount || 0}`
    },
    stopTime(stop) {
      const minutes = Number(stop.attraction?.recommendedDurationMinutes)
      if (!Number.isFinite(minutes) || minutes <= 0) return '游览时长待定'
      return `约 ${minutes} 分钟`
    },
    formatDayDate(date) {
      if (!date) return '日期待定'
      const parts = String(date).split('-')
      return parts.length === 3 ? `${Number(parts[1])}月${Number(parts[2])}日` : date
    },
    localToday() {
      const date = new Date()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${date.getFullYear()}-${month}-${day}`
    },
    formatRouteDateRange(startDate, endDate) {
      if (startDate && endDate) return `${this.formatDayDate(startDate)}—${this.formatDayDate(endDate)}`
      if (startDate) return `${this.formatDayDate(startDate)}出发`
      return '日期待定'
    },
    isGeneratingStop(stopId) {
      return sameId(this.generatingStopId, stopId) || this.routeStore.isGeneratingPlans
    },
    async generatePlanForStop(stop = this.activeStop) {
      if (!stop || !this.currentRoute || this.routeStore.isGeneratingPlans) return
      const child = this.childStore.activeChild
      if (!child?.id) {
        this.showToast('请先去“我的”选择或添加孩子')
        return
      }

      this.generatingStopId = stop.id
      try {
        await this.routeStore.generateExplorationPlans(this.currentRoute.id, child.id, [stop.id])
        await this.planStore.fetchPlans(this.userStore.userInfo?.id, { force: true, selectionPolicy: 'none' })
        await this.focusStop(stop, this.activeDay)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.showToast('探索生成失败，请稍后重试')
      } finally {
        this.generatingStopId = null
      }
    },
    async prepareActiveDay() {
      if (!this.currentRoute || !this.missingPlanStopIds.length || this.isPreparingDay || this.routeStore.isGeneratingPlans) return
      const child = this.childStore.activeChild
      if (!child?.id) {
        this.showToast('请先去“我的”选择或添加孩子')
        return
      }

      this.isPreparingDay = true
      try {
        await this.routeStore.generateExplorationPlans(this.currentRoute.id, child.id, this.missingPlanStopIds)
        await this.planStore.fetchPlans(this.userStore.userInfo?.id, { force: true, selectionPolicy: 'none' })
        const firstPreparedStop = this.activeDay?.stops?.find((stop) => this.planForStop(stop.id))
        if (firstPreparedStop) await this.focusStop(firstPreparedStop, this.activeDay)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.showToast('今日探索准备失败，请稍后重试')
      } finally {
        this.isPreparingDay = false
      }
    },
    openGuide(plan) {
      if (!plan?.id) return
      this.audioGuidePlanId = plan.id
      this.audioGuideOpen = true
    },
    openTask(task) {
      if (!task?.id || !this.activePlan?.id) return
      this.taskStore.setCurrentTask(task.id)
      uni.navigateTo({
        url: `/pages/task-detail/index?id=${encodeURIComponent(String(task.id))}&planId=${encodeURIComponent(String(this.activePlan.id))}`,
      })
    },
    async handlePrimaryAction() {
      const action = this.primaryAction
      if (!action || action.disabled) return
      if (action.type === 'generate') {
        await this.generatePlanForStop()
        return
      }
      if (action.type === 'start') {
        await this.startExploration()
        return
      }
      if (action.type === 'task') {
        this.openTask(action.task)
        return
      }
      if (action.type === 'complete') {
        await this.completeExploration()
        return
      }
      if (action.type === 'record') {
        this.openExplorationAlbum()
      }
    },
    async startExploration() {
      if (!this.activePlan || this.isStartingExploration) return
      this.isStartingExploration = true
      try {
        const plan = await this.planStore.startExploration(this.activePlan.id, this.userStore.userInfo?.id)
        await this.taskStore.ensureTasks(plan.id, plan.status)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.showToast('无法开始探索，请稍后重试')
      } finally {
        this.isStartingExploration = false
      }
    },
    async completeExploration() {
      if (!this.activePlan || this.planStore.isCompleting) return
      try {
        await this.planStore.completeExploration(this.activePlan.id, this.userStore.userInfo?.id)
        await this.planStore.fetchPlans(this.userStore.userInfo?.id, { force: true, selectionPolicy: 'none' })
        this.planStore.selectPlanById(this.activePlan.id, this.userStore.userInfo?.id)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.showToast('探索尚未完成，请检查任务后再试')
      }
    },
    openExplorationAlbum() {
      if (!this.activePlan?.id) return
      uni.navigateTo({ url: `/pages/record-detail/index?planId=${encodeURIComponent(String(this.activePlan.id))}` })
    },
    openFreePlan(plan) {
      if (!plan?.id) return
      this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)
      uni.navigateTo({ url: `/pages/explore-detail/index?planId=${encodeURIComponent(String(plan.id))}` })
    },
    editCurrentRoute() {
      if (!this.currentRoute?.id) return
      uni.navigateTo({ url: `/pages/route-detail/index?id=${encodeURIComponent(String(this.currentRoute.id))}` })
    },
    goRoutePlanning() {
      uni.navigateTo({ url: '/pages/route/index' })
    },
    async changeRoute(routeId) {
      this.showRoutePicker = false
      if (!routeId || sameId(routeId, this.currentRoute?.id)) return
      this.requestedRouteId = ''
      this.requestedDayId = ''
      this.requestedStopId = ''
      this.requestedPlanId = ''
      this.selectedRouteId = String(routeId)
      this.activeDayId = ''
      this.activeStopId = ''
      try {
        await this.routeStore.fetchRoute(routeId)
        await this.applyInitialFocus()
      } catch (error) {
        this.showToast('路线加载失败，请稍后重试')
      }
    },
  },
}
</script>

<style scoped>
.explore-workbench-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }
.explore-workbench-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; margin: 0 auto; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 156rpx); }
.workbench-skeletons { display: flex; flex-direction: column; gap: 24rpx; }.workbench-skeleton { height: 180rpx; }.workbench-skeleton--hero { height: 286rpx; }.explore-workbench-page__paper > .page-state { min-height: 560rpx; padding-right: 0; padding-left: 0; }.workbench-refresh-error { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; min-height: var(--tl-touch-target); padding: 12rpx 16rpx; margin-bottom: 20rpx; color: #8b3f2c; background: rgba(180, 61, 49, .08); border: 1rpx solid rgba(180, 61, 49, .28); border-radius: var(--tl-radius-small); }.workbench-refresh-error text { flex: 1; min-width: 0; font-size: var(--tl-type-meta); line-height: 1.45; }.workbench-refresh-error button { flex: 0 0 auto; min-width: var(--tl-touch-target); min-height: var(--tl-touch-target); padding: 0 14rpx; font-size: var(--tl-type-meta); color: inherit; background: transparent; border: 1rpx solid currentColor; border-radius: var(--tl-radius-small); }
.route-overview { position: relative; min-height: 206rpx; overflow: hidden; background: linear-gradient(135deg, #2e704b, #23613f); border-radius: var(--tl-radius-media); }.route-overview--with-image { min-height: 286rpx; background: #3e6b51; }.route-overview__image,.route-overview__shade { position: absolute; inset: 0; width: 100%; height: 100%; }.route-overview__image { z-index: 0; }.route-overview__shade { z-index: 1; background: linear-gradient(180deg, rgba(17, 46, 31, .08), rgba(17, 46, 31, .7)); }.route-overview__content { position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: flex-end; min-height: 206rpx; padding: 24rpx; color: #fff; }.route-overview--with-image .route-overview__content { min-height: 286rpx; }.route-overview__actions { position: absolute; top: 14rpx; right: 18rpx; display: flex; gap: 8rpx; align-items: center; }.route-overview__text-action { display: flex; align-items: center; justify-content: center; min-height: var(--tl-touch-target); padding: 0 14rpx; font-size: 21rpx; line-height: 1; color: rgba(255, 255, 255, .82); background: transparent; border: 1rpx solid transparent; border-radius: 999rpx; }.route-overview__text-action--switch { padding: 0 16rpx; font-size: 24rpx; font-weight: 600; color: rgba(255, 255, 255, .96); background: rgba(18, 58, 37, .24); border-color: rgba(255,255,255,.58); }.route-overview__text-action--edit { padding: 0 10rpx; color: rgba(255,255,255,.72); }.route-overview__title { display: block; font-size: 40rpx; font-weight: 700; line-height: 1.24; }.route-overview__meta { display: block; margin-top: 8rpx; font-size: 23rpx; color: rgba(255,255,255,.78); }
.route-stats { display: grid; grid-template-columns: repeat(4, 1fr); padding: 28rpx 10rpx; background: rgba(255, 253, 247, .86); border-bottom: 1rpx solid var(--tl-divider); }.route-stats__item { display: flex; flex-direction: column; align-items: center; gap: 5rpx; min-width: 0; border-right: 1rpx solid var(--tl-divider); }.route-stats__item:last-child { border-right: 0; }.route-stats__number { font-size: 36rpx; font-weight: 700; color: #1f7b47; }.route-stats__label { font-size: 21rpx; color: var(--tl-text-secondary); white-space: nowrap; }
.day-tabs { margin: 26rpx 0 0; white-space: nowrap; }.day-tabs__inner { display: flex; gap: 12rpx; width: max-content; padding-right: 32rpx; }.day-tab { display: flex; flex-direction: column; gap: 3rpx; align-items: flex-start; min-width: 132rpx; min-height: var(--tl-touch-target); padding: 13rpx 16rpx; color: var(--tl-text-main); text-align: left; background: rgba(255, 253, 247, .52); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); }.day-tab--active { color: #1f7b47; background: #f7fcf7; border: 1rpx solid #1f7b47; }.day-tab__title { font-size: 24rpx; font-weight: 700; }.day-tab__date { font-size: 21rpx; color: var(--tl-text-secondary); }.day-content__heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20rpx; margin: 30rpx 0 18rpx; }.day-content__heading-copy { min-width: 0; }.day-content__title,.day-content__subtitle { display: block; }.day-content__title { font-size: 31rpx; font-weight: var(--tl-weight-section-title); }.day-content__subtitle { margin-top: 6rpx; font-size: 23rpx; color: var(--tl-text-secondary); }.day-content__prepare { min-height: var(--tl-touch-target); padding: 0 13rpx; font-size: 21rpx; color: #1f7b47; background: transparent; border: 1rpx solid rgba(31,123,71,.56); border-radius: var(--tl-radius-small); }.day-empty { padding: 32rpx 0; font-size: var(--tl-type-body); color: var(--tl-text-secondary); border-top: 1rpx solid var(--tl-divider); }
.stop-list { border-top: 1rpx solid var(--tl-divider); }.stop-block { position: relative; display: flex; gap: 16rpx; padding: 28rpx 0; border-bottom: 1rpx solid var(--tl-divider); }.stop-block + .stop-block { padding-top: 34rpx; }.stop-block__rail { position: relative; z-index: 1; display: flex; flex: 0 0 44rpx; align-items: flex-start; justify-content: center; }.stop-block__rail::after { position: absolute; top: 44rpx; bottom: -40rpx; width: 2rpx; content: ''; background: rgba(31, 123, 71, .18); }.stop-block:last-child .stop-block__rail::after { display: none; }.stop-block__rail text { display: flex; align-items: center; justify-content: center; width: 40rpx; height: 40rpx; font-size: 21rpx; font-weight: 700; color: #fff; background: #1f7b47; border-radius: 50%; }.stop-block__main { flex: 1; min-width: 0; }.stop-summary { display: flex; gap: 15rpx; align-items: flex-start; min-height: var(--tl-touch-target); padding: 4rpx; border: 1rpx solid transparent; border-radius: var(--tl-radius-small); }.stop-summary--active { background: var(--tl-color-primary-soft); border-color: var(--tl-color-primary); }.stop-summary__image { flex: 0 0 112rpx; width: 112rpx; height: 96rpx; background: var(--tl-blue); border-radius: var(--tl-radius-small); }.stop-summary__image--blank { background: linear-gradient(135deg, #dcebdd, #b8d4bf); }.stop-summary__copy { flex: 1; min-width: 0; }.stop-summary__title-row { display: flex; gap: 8rpx; align-items: center; justify-content: space-between; }.stop-summary__title { overflow: hidden; font-size: 28rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.status-chip { flex: 0 0 auto; padding: 6rpx 10rpx; font-size: 19rpx; line-height: 1.25; border-radius: 999rpx; }.status-chip--in-progress { color: #17673c; background: #e2f3e7; }.status-chip--ready { color: #9c6016; background: #fff0d6; }.status-chip--completed { color: #59753f; background: #e8f0d8; }.status-chip--missing { color: var(--tl-text-secondary); background: var(--tl-surface-muted); }.stop-summary__meta { display: flex; gap: 11rpx; align-items: center; margin-top: 8rpx; font-size: 21rpx; color: var(--tl-text-secondary); }.stop-summary__meta text + text::before { margin-right: 11rpx; content: '·'; color: var(--tl-divider); }.stop-summary__summary { display: -webkit-box; margin-top: 7rpx; overflow: hidden; font-size: 21rpx; line-height: 1.45; color: var(--tl-text-secondary); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }.stop-summary__arrow { align-self: center; margin-left: 0; font-size: 31rpx; color: var(--tl-text-secondary); }
.stop-expanded { padding-top: 18rpx; }.stop-expanded__task-head { display: flex; align-items: center; justify-content: space-between; margin-top: 12rpx; padding: 0 0 10rpx; font-size: 27rpx; font-weight: 700; }.stop-expanded__guide { min-height: var(--tl-touch-target); padding: 0 13rpx; font-size: 20rpx; color: #1f7b47; background: transparent; border: 1rpx solid rgba(31,123,71,.52); border-radius: var(--tl-radius-small); }.task-list { border-top: 1rpx solid var(--tl-divider); }.task-row { display: flex; gap: 13rpx; align-items: center; min-height: var(--tl-touch-target); padding: 15rpx 4rpx; border-bottom: 1rpx solid var(--tl-divider); }.task-row__mark { display: flex; flex: 0 0 30rpx; align-items: center; justify-content: center; width: 30rpx; height: 30rpx; font-size: 19rpx; color: #1f7b47; border: 2rpx solid currentColor; border-radius: 50%; }.task-row--completed .task-row__mark { color: #fff; background: #1f7b47; }.task-row__copy { flex: 1; min-width: 0; }.task-row__title,.task-row__desc { display: block; }.task-row__title { overflow: hidden; font-size: 25rpx; font-weight: 600; line-height: 1.3; text-overflow: ellipsis; white-space: nowrap; }.task-row__desc { margin-top: 3rpx; overflow: hidden; font-size: 21rpx; line-height: 1.35; color: var(--tl-text-secondary); text-overflow: ellipsis; white-space: nowrap; }.task-row__arrow { font-size: 29rpx; color: var(--tl-text-secondary); }.task-state { padding: 24rpx 0; font-size: 24rpx; color: var(--tl-text-secondary); }.task-state--error { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; color: #a94b36; }.task-state--error button { min-width: var(--tl-touch-target); min-height: var(--tl-touch-target); padding: 0 14rpx; color: inherit; background: transparent; border: 1rpx solid currentColor; border-radius: var(--tl-radius-small); }
.plan-missing { padding-top: 12rpx; }.plan-missing__title,.plan-missing__copy { display: block; }.plan-missing__title { font-size: 27rpx; font-weight: 600; color: var(--tl-text-secondary); }.plan-missing__copy { margin-top: 7rpx; font-size: 24rpx; color: var(--tl-text-secondary); }.plan-missing button { min-height: var(--tl-touch-target); margin-top: 18rpx; padding: 0 20rpx; font-size: 25rpx; color: #1f7b47; background: transparent; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-small); }
.free-explorations { margin-top: 56rpx; padding-top: 26rpx; border-top: 1rpx solid var(--tl-divider); }.free-explorations__title,.free-explorations__note { display: block; }.free-explorations__title { font-size: 29rpx; font-weight: var(--tl-weight-section-title); }.free-explorations__note { margin-top: 7rpx; font-size: 21rpx; line-height: 1.4; color: var(--tl-text-secondary); }.free-exploration { display: flex; align-items: center; justify-content: space-between; min-height: var(--tl-touch-target); padding: 18rpx 0; border-bottom: 1rpx solid var(--tl-divider); }.free-exploration__title,.free-exploration__meta { display: block; }.free-exploration__title { font-size: 26rpx; font-weight: 600; }.free-exploration__meta { margin-top: 5rpx; font-size: 21rpx; color: var(--tl-text-secondary); }.free-exploration > text { font-size: 31rpx; color: var(--tl-text-secondary); }
.workbench-primary-action { position: fixed; right: var(--tl-page-padding); bottom: calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 14rpx); left: var(--tl-page-padding); z-index: var(--tl-z-sticky); max-width: calc(var(--tl-content-max-width) - (var(--tl-page-padding) * 2)); margin: 0 auto; }.workbench-primary-action button { width: 100%; min-height: 88rpx; height: 88rpx; font-size: var(--tl-type-primary-action); font-weight: var(--tl-weight-primary-action); color: #fff; background: #1f7b47; border-radius: var(--tl-radius-control); box-shadow: 0 6rpx 14rpx rgba(31, 123, 71, .14); }.workbench-primary-action button[disabled] { opacity: .65; }
.route-picker-mask { position: fixed; inset: 0; z-index: var(--tl-z-overlay); display: flex; align-items: flex-end; background: rgba(49, 39, 27, .38); }.route-picker { width: 100%; max-width: var(--tl-content-max-width); padding: 30rpx var(--tl-page-padding) calc(var(--tl-space-lg) + var(--tl-safe-bottom)); margin: 0 auto; background: var(--tl-surface); border-radius: var(--tl-radius-sheet) var(--tl-radius-sheet) 0 0; }.route-picker__title { display: block; margin-bottom: 18rpx; font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }.route-picker__item { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 100rpx; padding: 18rpx 0; font-size: 28rpx; color: var(--tl-text-main); text-align: left; background: transparent; border-bottom: 1rpx solid var(--tl-divider); }.route-picker__item view text { display: block; }.route-picker__item view text:last-child { margin-top: 6rpx; font-size: 23rpx; color: var(--tl-text-secondary); }.route-picker__item--active { color: #1f7b47; }
@media (min-width: 431px) { .explore-workbench-page__paper { padding-right: 18px; padding-left: 18px; }.workbench-primary-action { right: 18px; left: 18px; max-width: 394px; } }
</style>
