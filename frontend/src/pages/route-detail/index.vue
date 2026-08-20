<template>
  <view class="route-detail-page">
    <view class="route-detail-page__paper">
      <view class="route-detail-header">
        <button class="route-detail-header__back" @click="goBack" aria-label="返回">‹</button>
        <view class="route-detail-header__copy"><text class="route-detail-header__eyebrow">TRAVEL ROUTE</text><text class="route-detail-header__title">路线详情</text></view>
        <view class="route-detail-header__spacer"></view>
      </view>

      <view v-if="isPageLoading" class="route-detail-state"><text>正在打开这条路线...</text></view>
      <view v-else-if="pageError || (!currentRoute && routeStore.error)" class="route-detail-state">
        <text>{{ pageError || '路线信息不存在' }}</text><text class="route-link" @click="loadRoute">重新试一次</text>
      </view>

      <template v-else-if="currentRoute">
        <view class="route-detail-card">
          <view class="route-detail-card__tape"></view>
          <text class="route-detail-card__status">{{ formatRouteStatus(currentRoute.status) }}</text>
          <text class="route-detail-card__title">{{ currentRoute.title }}</text>
          <view class="route-detail-card__item"><text>目的地</text><text>{{ currentRoute.city }}</text></view>
          <view class="route-detail-card__item"><text>出行日期</text><text>{{ formatRouteDates(currentRoute.startDate, currentRoute.endDate) }}</text></view>
          <view class="route-detail-card__days"><text v-if="currentRoute.days.length">已安排 {{ currentRoute.days.length }} 天</text><text v-else>这条路线还没有安排行程</text></view>
        </view>

        <view class="route-actions">
          <text class="route-section__eyebrow">ROUTE ACTIONS</text><text class="route-section__title">路线操作</text>
          <view class="route-actions__buttons">
            <button :disabled="isUpdatingRoute" @click="openRouteEditSheet">编辑路线</button>
            <button v-if="currentRoute.status === 'draft'" :disabled="isMarkingReady" @click="markRouteReady">{{ isMarkingReady ? '正在标记…' : '标记为已准备' }}</button>
            <text v-else class="route-actions__ready">已准备</text>
          </view>
          <text v-if="mutationError" class="route-error">{{ mutationError }}</text>
          <text class="route-actions__delete" @click="confirmDeleteRoute">{{ isDeletingRoute ? '正在删除…' : '删除路线' }}</text>
        </view>

        <view class="plan-generation-section">
          <text class="route-section__eyebrow">EXPLORE TOGETHER</text><text class="route-section__title">探索计划</text>
          <text class="plan-generation-section__copy">从路线里选几个想认真探索的地方，为孩子准备专属探索计划。</text>
          <text v-if="!isRouteReady" class="plan-generation-section__hint">请先完成路线安排，并标记为“已准备”。</text>
          <button :disabled="!isRouteReady" @click="openPlanGenerationSheet">生成探索计划</button>
        </view>

        <view class="day-section">
          <view class="day-section__heading"><view><text class="route-section__eyebrow">DAILY NOTES</text><text class="route-section__title">每日行程</text></view><view class="day-section__heading-actions"><button v-if="currentRoute.days.length > 1" :disabled="isReorderingDays" @click="toggleDayOrderEditing">{{ isDayOrderEditing ? '完成排序' : '调整天数顺序' }}</button><button @click="openCreateDaySheet">+ 添加一天</button></view></view>
          <view v-if="currentRoute.days.length" class="day-section__list">
            <view v-for="day in currentRoute.days" :key="day.id" class="day-card">
              <view class="day-card__topline"><text>第 {{ day.dayNumber }} 天</text><view><text @click="openEditDaySheet(day)">编辑</text><text class="day-card__delete" @click="confirmDeleteDay(day)">删除</text></view></view>
              <view v-if="isDayOrderEditing" class="order-controls"><button :disabled="isReorderingDays || currentRoute.days.indexOf(day) === 0" @click="moveDay(day.id, -1)">↑</button><button :disabled="isReorderingDays || currentRoute.days.indexOf(day) === currentRoute.days.length - 1" @click="moveDay(day.id, 1)">↓</button></view>
              <text class="day-card__date">{{ formatDayDate(day.date) }}</text>
              <text class="day-card__title">{{ day.title || '未命名行程' }}</text>
              <view class="stop-section">
                <view class="stop-section__heading"><text>当天景点</text><view class="stop-section__actions"><text v-if="day.stops.length > 1" @click="toggleStopOrderEditing(day.id)">{{ stopOrderDayId === day.id ? '完成排序' : '调整景点顺序' }}</text><text @click="openAttractionSheet(day)">+ 添加景点</text></view></view>
                <view v-if="day.stops.length" class="stop-section__list">
                  <view v-for="stop in day.stops" :key="stop.id" class="stop-card">
                    <view class="stop-card__topline"><text class="stop-card__name">{{ stop.attraction.name }}</text><view><text @click="openStopNoteSheet(day, stop)">{{ stop.note ? '编辑备注' : '添加备注' }}</text><text class="day-card__delete" @click="confirmDeleteStop(day, stop)">删除</text></view></view>
                    <view v-if="stopOrderDayId === day.id" class="order-controls order-controls--stop"><button :disabled="reorderingStopsDayId === day.id || day.stops.indexOf(stop) === 0" @click="moveStop(day, stop.id, -1)">↑</button><button :disabled="reorderingStopsDayId === day.id || day.stops.indexOf(stop) === day.stops.length - 1" @click="moveStop(day, stop.id, 1)">↓</button></view>
                    <text v-if="stop.attraction.district" class="stop-card__meta">{{ stop.attraction.district }}</text>
                    <text v-if="stop.attraction.summary" class="stop-card__summary">{{ stop.attraction.summary }}</text>
                    <text v-if="stop.attraction.recommendedDurationMinutes" class="stop-card__meta">约 {{ stop.attraction.recommendedDurationMinutes }} 分钟</text>
                    <text v-if="stop.note" class="stop-card__note">{{ stop.note }}</text>
                  </view>
                </view>
                <text v-else class="day-card__stops">暂未添加景点</text>
              </view>
            </view>
          </view>
          <view v-else class="day-section__empty">先为这次旅行写下第一天的安排吧。</view>
        </view>
      </template>
    </view>

    <view v-if="showPlanGenerationSheet" class="route-sheet-mask" @click="closePlanGenerationSheet"><view class="route-sheet plan-generation-sheet" @click.stop>
      <view class="route-sheet__heading"><view><text class="route-section__eyebrow">EXPLORE PLAN</text><text class="route-sheet__title">探索计划</text></view><button @click="closePlanGenerationSheet">×</button></view>
      <template v-if="!hasRealChildren">
        <view class="plan-generation-sheet__empty">请先完善孩子档案后再生成探索计划。</view>
      </template>
      <template v-else>
        <view class="plan-generation-sheet__block"><text class="plan-generation-sheet__label">1. 选择孩子</text><view class="plan-generation-child-list"><view v-for="child in realChildren" :key="child.id" class="plan-generation-child" :class="{ 'plan-generation-child--selected': selectedChildId === child.id }" @click="selectGenerationChild(child.id)"><text>{{ child.name }}</text><text>{{ child.age }} 岁</text></view></view></view>
        <view class="plan-generation-sheet__block"><view class="plan-generation-sheet__row"><text class="plan-generation-sheet__label">2. 选择探索景点</text><view><text @click="selectAllRouteStops">全选</text><text @click="clearRouteStopSelection">取消全选</text></view></view><view v-for="day in generationDays" :key="day.id" class="plan-generation-day"><text class="plan-generation-day__title">第 {{ day.dayNumber }} 天</text><view v-for="stop in day.stops" :key="stop.id" class="plan-generation-stop" :class="{ 'plan-generation-stop--selected': isRouteStopSelected(stop.id) }" @click="toggleRouteStopSelection(stop.id)"><text class="plan-generation-stop__mark">{{ isRouteStopSelected(stop.id) ? '●' : '○' }}</text><view><text class="plan-generation-stop__name">{{ stop.attraction.name }}</text><text v-if="stop.attraction.district || stop.attraction.recommendedDurationMinutes" class="plan-generation-stop__meta">{{ stop.attraction.district || '' }}{{ stop.attraction.district && stop.attraction.recommendedDurationMinutes ? ' · ' : '' }}{{ stop.attraction.recommendedDurationMinutes ? `约 ${stop.attraction.recommendedDurationMinutes} 分钟` : '' }}</text></view></view></view></view>
        <text class="plan-generation-sheet__count">已选择 {{ selectedRouteStopIds.length }} 个</text>
      </template>
      <text v-if="planGenerationError" class="route-error">{{ planGenerationError }}</text>
      <view v-if="hasSubmittedGeneration" class="plan-generation-result"><text class="plan-generation-result__title">探索计划已准备好</text><view v-for="item in generationDisplayResults" :key="item.routeStopId" class="plan-generation-result__item"><text>{{ item.stopName }}</text><text>{{ item.label }}</text></view></view>
      <button class="route-sheet__submit" :disabled="!canSubmitPlanGeneration" @click="submitPlanGeneration">{{ routeStore.isGeneratingPlans ? '正在生成…' : '生成探索计划' }}</button>
    </view></view>

    <view v-if="showRouteEditSheet" class="route-sheet-mask" @click="closeRouteEditSheet"><view class="route-sheet" @click.stop>
      <view class="route-sheet__heading"><view><text class="route-section__eyebrow">EDIT ROUTE</text><text class="route-sheet__title">编辑路线</text></view><button @click="closeRouteEditSheet">×</button></view>
      <view class="route-form-field"><text>路线名称</text><input v-model="routeEditForm.title" placeholder="例如：北京周末文化游" maxlength="120" /></view>
      <view class="route-form-field"><text>城市</text><input v-model="routeEditForm.city" placeholder="例如：北京" maxlength="80" /></view>
      <view class="route-form-field"><text>出发日期（可选）</text><picker mode="date" :value="routeEditForm.startDate" @change="setRouteDate('startDate', $event)"><view>{{ routeEditForm.startDate || '选择出发日期' }}</view></picker><text v-if="routeEditForm.startDate" @click="clearRouteDate('startDate')">清除</text></view>
      <view class="route-form-field"><text>结束日期（可选）</text><picker mode="date" :value="routeEditForm.endDate" @change="setRouteDate('endDate', $event)"><view>{{ routeEditForm.endDate || '选择结束日期' }}</view></picker><text v-if="routeEditForm.endDate" @click="clearRouteDate('endDate')">清除</text></view>
      <text v-if="routeEditError" class="route-error">{{ routeEditError }}</text><button class="route-sheet__submit" :disabled="isUpdatingRoute" @click="submitRouteEdit">{{ isUpdatingRoute ? '正在保存…' : '保存修改' }}</button>
    </view></view>

    <view v-if="showDaySheet" class="route-sheet-mask" @click="closeDaySheet"><view class="route-sheet" @click.stop>
      <view class="route-sheet__heading"><view><text class="route-section__eyebrow">DAY NOTE</text><text class="route-sheet__title">{{ dayFormMode === 'edit' ? '编辑当天安排' : '添加一天' }}</text></view><button @click="closeDaySheet">×</button></view>
      <view class="route-form-field"><text>日期（可选）</text><picker mode="date" :value="dayForm.date" @change="setDayDate"><view>{{ dayForm.date || '选择日期' }}</view></picker><text v-if="dayForm.date" @click="clearDayDate">清除</text></view>
      <view class="route-form-field"><text>当天标题（可选）</text><input v-model="dayForm.title" placeholder="例如：故宫屋顶观察日" maxlength="120" /></view>
      <text v-if="dayFormError" class="route-error">{{ dayFormError }}</text><button class="route-sheet__submit" :disabled="isSavingDay" @click="submitDay">{{ isSavingDay ? '正在保存…' : '保存当天安排' }}</button>
    </view></view>

    <view v-if="showAttractionSheet" class="route-sheet-mask" @click="closeAttractionSheet"><view class="route-sheet" @click.stop>
      <view class="route-sheet__heading"><view><text class="route-section__eyebrow">ATTRACTIONS</text><text class="route-sheet__title">添加景点</text></view><button @click="closeAttractionSheet">×</button></view>
      <text class="attraction-sheet__city">当前城市：{{ currentRoute.city }}</text>
      <view class="attraction-sheet__search"><input v-model="attractionKeyword" placeholder="搜索景点或介绍" confirm-type="search" @confirm="searchAttractions" /><button :disabled="isLoadingAttractions" @click="searchAttractions">{{ isLoadingAttractions ? '查找中…' : '搜索' }}</button></view>
      <view v-if="isLoadingAttractions" class="attraction-sheet__state">正在查找景点...</view>
      <view v-else-if="attractionError" class="attraction-sheet__state"><text>{{ attractionError }}</text><text class="route-link" @click="searchAttractions">重新搜索</text></view>
      <view v-else-if="!attractionItems.length" class="attraction-sheet__state">没有找到符合条件的景点</view>
      <view v-else class="attraction-sheet__list"><view v-for="attraction in attractionItems" :key="attraction.id" class="attraction-card">
        <text class="attraction-card__name">{{ attraction.name }}</text><text v-if="attraction.district" class="attraction-card__meta">{{ attraction.district }}</text><text v-if="attraction.summary" class="attraction-card__summary">{{ attraction.summary }}</text><text v-if="attraction.recommendedDurationMinutes" class="attraction-card__meta">约 {{ attraction.recommendedDurationMinutes }} 分钟</text>
        <button :disabled="addingAttractionId === attraction.id" @click="addAttraction(attraction)">{{ addingAttractionId === attraction.id ? '正在加入…' : '加入行程' }}</button>
      </view></view>
    </view></view>

    <view v-if="showStopNoteSheet" class="route-sheet-mask" @click="closeStopNoteSheet"><view class="route-sheet" @click.stop>
      <view class="route-sheet__heading"><view><text class="route-section__eyebrow">STOP NOTE</text><text class="route-sheet__title">景点备注</text></view><button @click="closeStopNoteSheet">×</button></view>
      <view class="route-form-field"><text>备注</text><input v-model="stopNote" placeholder="写下这站的小提醒" maxlength="500" /></view>
      <text v-if="stopNoteError" class="route-error">{{ stopNoteError }}</text><button class="route-sheet__submit" :disabled="isUpdatingStop" @click="submitStopNote">{{ isUpdatingStop ? '正在保存…' : '保存备注' }}</button>
    </view></view>
    <AppTabbar active="route" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { getAttractions } from '../../api/attractions'
import { useRouteStore } from '../../stores/route'
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request'
import { endUserSession } from '../../utils/sessionBoundary'

const emptyRouteEditForm = () => ({ title: '', city: '', startDate: '', endDate: '' })
const emptyDayForm = () => ({ id: null, date: '', title: '' })

export default {
  components: { AppTabbar },
  data() {
    return {
      routeId: '', pageError: '', mutationError: '', showRouteEditSheet: false, isUpdatingRoute: false,
      isMarkingReady: false, isDeletingRoute: false, routeEditForm: emptyRouteEditForm(), routeEditError: '',
      showDaySheet: false, dayFormMode: 'create', dayForm: emptyDayForm(), isSavingDay: false, deletingDayId: null, dayFormError: '', isDayOrderEditing: false, isReorderingDays: false,
      showAttractionSheet: false, attractionDayId: null, attractionKeyword: '', attractionItems: [], attractionTotal: 0,
      isLoadingAttractions: false, attractionError: '', addingAttractionId: null,
      showStopNoteSheet: false, editingStopDayId: null, editingStopId: null, stopNote: '', isUpdatingStop: false, stopNoteError: '', deletingStopId: null, stopOrderDayId: null, reorderingStopsDayId: null,
      showPlanGenerationSheet: false, selectedChildId: null, selectedRouteStopIds: [], hasSubmittedGeneration: false, planGenerationError: '',
    }
  },
  computed: {
    routeStore() { return useRouteStore() },
    childStore() { return useChildStore() },
    userStore() { return useUserStore() },
    currentRoute() { return this.routeStore.currentRoute },
    isPageLoading() { return this.userStore.isRestoring || this.routeStore.isLoading },
    realChildren() { return this.childStore.children.filter((child) => child?.id !== null && child?.id !== undefined) },
    hasRealChildren() { return this.realChildren.length > 0 },
    isRouteReady() { return this.currentRoute?.status === 'ready' },
    generationDays() { return (this.currentRoute?.days || []).filter((day) => Array.isArray(day.stops) && day.stops.length) },
    allRouteStopIds() { return this.generationDays.flatMap((day) => day.stops.map((stop) => stop.id)) },
    canSubmitPlanGeneration() { return this.isRouteReady && this.hasRealChildren && Boolean(this.selectedChildId) && this.selectedRouteStopIds.length > 0 && !this.routeStore.isGeneratingPlans },
    generationDisplayResults() {
      const stopsById = new Map(this.allRouteStopIds.map((stopId) => [String(stopId), this.findRouteStop(stopId)]))
      return (this.routeStore.planGenerationResult?.results || []).map((result) => ({
        ...result,
        stopName: stopsById.get(String(result.routeStopId))?.attraction?.name || '路线景点',
        label: { created: '已生成', existing: '已存在' }[result.result] || result.result,
      }))
    },
  },
  onLoad(options) {
    this.routeId = String(options?.id || '').trim()
    if (!this.routeId) this.pageError = '路线信息不存在'
  },
  async onShow() { await this.loadRoute() },
  methods: {
    async loadRoute() {
      if (!this.routeId) { this.pageError = '路线信息不存在'; return }
      try {
        if (!this.userStore.isAuthReady || this.userStore.isRestoring) await this.userStore.restoreSession()
        if (!this.userStore.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return }
        this.pageError = ''
        await this.routeStore.fetchRoute(this.routeId)
        await this.childStore.fetchChildren(this.userStore.userInfo.id)
      } catch (error) {
        if (isAuthenticationError(error)) { await endUserSession(); return }
        this.pageError = error?.message || '路线信息不存在'
      }
    },
    async handleRequestError(error, field) {
      if (isAuthenticationError(error)) { await endUserSession(); return true }
      this[field] = error?.message || '操作失败，请稍后重试'
      return false
    },
    formatRouteDates(startDate, endDate) {
      const formatDate = (value) => String(value || '').replace(/-/g, '.')
      if (startDate && endDate) return `${formatDate(startDate)} - ${formatDate(endDate)}`
      if (startDate) return `${formatDate(startDate)} 出发`
      return '日期待定'
    },
    formatDayDate(value) { return value ? String(value).replace(/-/g, '.') : '日期待定' },
    formatRouteStatus(status) { return { draft: '草稿', ready: '已准备' }[status] || '' },
    findRouteStop(routeStopId) { return this.generationDays.flatMap((day) => day.stops).find((stop) => String(stop.id) === String(routeStopId)) },
    openPlanGenerationSheet() {
      if (!this.currentRoute) return
      const currentChildId = this.childStore.currentChild?.id
      this.selectedChildId = this.realChildren.some((child) => String(child.id) === String(currentChildId)) ? currentChildId : null
      this.selectedRouteStopIds = []
      this.hasSubmittedGeneration = false
      this.planGenerationError = ''
      this.showPlanGenerationSheet = true
    },
    closePlanGenerationSheet() {
      if (this.routeStore.isGeneratingPlans) return
      this.showPlanGenerationSheet = false
    },
    selectGenerationChild(childId) { this.selectedChildId = childId },
    isRouteStopSelected(stopId) { return this.selectedRouteStopIds.includes(stopId) },
    toggleRouteStopSelection(stopId) {
      this.selectedRouteStopIds = this.isRouteStopSelected(stopId)
        ? this.selectedRouteStopIds.filter((id) => id !== stopId)
        : [...this.selectedRouteStopIds, stopId]
    },
    selectAllRouteStops() { this.selectedRouteStopIds = [...this.allRouteStopIds] },
    clearRouteStopSelection() { this.selectedRouteStopIds = [] },
    async submitPlanGeneration() {
      if (this.routeStore.isGeneratingPlans) return
      if (!this.canSubmitPlanGeneration) return
      this.planGenerationError = ''
      this.hasSubmittedGeneration = false
      try {
        await this.routeStore.generateExplorationPlans(
          this.currentRoute.id,
          this.selectedChildId,
          this.selectedRouteStopIds,
        )
        this.hasSubmittedGeneration = true
      } catch (error) {
        this.hasSubmittedGeneration = false
        if (isAuthenticationError(error)) { await endUserSession(); return }
        this.planGenerationError = error?.message || '操作失败，请稍后重试'
      }
    },
    openRouteEditSheet() {
      if (!this.currentRoute) return
      this.routeEditForm = { title: this.currentRoute.title || '', city: this.currentRoute.city || '', startDate: this.currentRoute.startDate || '', endDate: this.currentRoute.endDate || '' }
      this.routeEditError = ''
      this.showRouteEditSheet = true
    },
    closeRouteEditSheet() {
      if (this.isUpdatingRoute) return
      this.showRouteEditSheet = false
      this.routeEditForm = emptyRouteEditForm()
      this.routeEditError = ''
    },
    setRouteDate(field, event) { this.routeEditForm[field] = event?.detail?.value || '' },
    clearRouteDate(field) { this.routeEditForm[field] = '' },
    buildRoutePayload() {
      const title = this.routeEditForm.title.trim()
      const city = this.routeEditForm.city.trim()
      if (!title || !city) { this.routeEditError = '请填写路线名称和城市'; return null }
      if (this.routeEditForm.startDate && this.routeEditForm.endDate && this.routeEditForm.endDate < this.routeEditForm.startDate) { this.routeEditError = '结束日期不能早于开始日期'; return null }
      return { title, city, startDate: this.routeEditForm.startDate || null, endDate: this.routeEditForm.endDate || null }
    },
    async submitRouteEdit() {
      if (this.isUpdatingRoute) return
      const payload = this.buildRoutePayload()
      if (!payload) return
      this.isUpdatingRoute = true; this.routeEditError = ''
      try {
        await this.routeStore.updateRoute(this.routeId, payload)
        this.isUpdatingRoute = false
        this.closeRouteEditSheet()
      } catch (error) { await this.handleRequestError(error, 'routeEditError') } finally { this.isUpdatingRoute = false }
    },
    async markRouteReady() {
      if (this.isMarkingReady || this.currentRoute?.status !== 'draft') return
      this.isMarkingReady = true; this.mutationError = ''
      try { await this.routeStore.updateRoute(this.routeId, { status: 'ready' }) } catch (error) { await this.handleRequestError(error, 'mutationError') } finally { this.isMarkingReady = false }
    },
    async confirmDeleteRoute() {
      if (this.isDeletingRoute) return
      const confirmed = await new Promise((resolve) => uni.showModal({ title: '确认删除这条路线？', content: '路线中的每日安排也会一起删除。', success: (result) => resolve(Boolean(result.confirm)), fail: () => resolve(false) }))
      if (!confirmed) return
      this.isDeletingRoute = true; this.mutationError = ''
      try { await this.routeStore.deleteRoute(this.routeId); uni.reLaunch({ url: '/pages/route/index' }) } catch (error) { await this.handleRequestError(error, 'mutationError') } finally { this.isDeletingRoute = false }
    },
    openCreateDaySheet() { this.dayFormMode = 'create'; this.dayForm = emptyDayForm(); this.dayFormError = ''; this.showDaySheet = true },
    openEditDaySheet(day) { this.dayFormMode = 'edit'; this.dayForm = { id: day.id, date: day.date || '', title: day.title || '' }; this.dayFormError = ''; this.showDaySheet = true },
    closeDaySheet() { if (this.isSavingDay) return; this.showDaySheet = false; this.dayFormMode = 'create'; this.dayForm = emptyDayForm(); this.dayFormError = '' },
    setDayDate(event) { this.dayForm.date = event?.detail?.value || '' },
    clearDayDate() { this.dayForm.date = '' },
    buildDayPayload() { return { date: this.dayForm.date || null, title: this.dayForm.title.trim() || null } },
    async submitDay() {
      if (this.isSavingDay) return
      const payload = this.buildDayPayload()
      this.isSavingDay = true; this.dayFormError = ''
      try {
        if (this.dayFormMode === 'edit') await this.routeStore.updateDay(this.routeId, this.dayForm.id, payload)
        else await this.routeStore.createDay(this.routeId, payload)
        this.isSavingDay = false
        this.closeDaySheet()
      } catch (error) { await this.handleRequestError(error, 'dayFormError') } finally { this.isSavingDay = false }
    },
    async confirmDeleteDay(day) {
      if (this.deletingDayId) return
      const content = day.stops.length ? '这一天已安排的景点也会一起删除。' : ''
      const confirmed = await new Promise((resolve) => uni.showModal({ title: `删除第 ${day.dayNumber} 天的行程？`, content, success: (result) => resolve(Boolean(result.confirm)), fail: () => resolve(false) }))
      if (!confirmed) return
      this.deletingDayId = day.id; this.mutationError = ''
      try { await this.routeStore.deleteDay(this.routeId, day.id) } catch (error) { await this.handleRequestError(error, 'mutationError') } finally { this.deletingDayId = null }
    },
    toggleDayOrderEditing() {
      if (this.isReorderingDays || this.currentRoute?.days.length <= 1) return
      this.isDayOrderEditing = !this.isDayOrderEditing
    },
    async moveDay(dayId, direction) {
      if (this.isReorderingDays || !this.isDayOrderEditing) return
      const dayIds = this.currentRoute.days.map((day) => day.id)
      const index = dayIds.indexOf(dayId)
      const nextIndex = index + direction
      if (index < 0 || nextIndex < 0 || nextIndex >= dayIds.length) return
      ;[dayIds[index], dayIds[nextIndex]] = [dayIds[nextIndex], dayIds[index]]
      this.isReorderingDays = true
      this.mutationError = ''
      try {
        await this.routeStore.reorderDays(this.routeId, dayIds)
        this.isDayOrderEditing = false
      } catch (error) {
        await this.handleRequestError(error, 'mutationError')
      } finally {
        this.isReorderingDays = false
      }
    },
    toggleStopOrderEditing(dayId) {
      if (this.reorderingStopsDayId) return
      this.stopOrderDayId = this.stopOrderDayId === dayId ? null : dayId
    },
    async moveStop(day, stopId, direction) {
      if (this.reorderingStopsDayId || this.stopOrderDayId !== day.id) return
      const stopIds = day.stops.map((stop) => stop.id)
      const index = stopIds.indexOf(stopId)
      const nextIndex = index + direction
      if (index < 0 || nextIndex < 0 || nextIndex >= stopIds.length) return
      ;[stopIds[index], stopIds[nextIndex]] = [stopIds[nextIndex], stopIds[index]]
      this.reorderingStopsDayId = day.id
      this.mutationError = ''
      try {
        await this.routeStore.reorderStops(this.routeId, day.id, stopIds)
        this.stopOrderDayId = null
      } catch (error) {
        await this.handleRequestError(error, 'mutationError')
      } finally {
        this.reorderingStopsDayId = null
      }
    },
    async openAttractionSheet(day) {
      this.attractionDayId = day.id
      this.attractionKeyword = ''
      this.attractionItems = []
      this.attractionTotal = 0
      this.attractionError = ''
      this.showAttractionSheet = true
      await this.searchAttractions()
    },
    closeAttractionSheet() {
      if (this.addingAttractionId) return
      this.showAttractionSheet = false
      this.attractionDayId = null
      this.attractionKeyword = ''
      this.attractionItems = []
      this.attractionTotal = 0
      this.attractionError = ''
    },
    async searchAttractions() {
      if (this.isLoadingAttractions || !this.currentRoute?.city) return
      const keyword = this.attractionKeyword.trim()
      this.isLoadingAttractions = true
      this.attractionError = ''
      try {
        const result = await getAttractions({
          city: this.currentRoute.city,
          ...(keyword ? { keyword } : {}),
          limit: 100,
          offset: 0,
        })
        this.attractionItems = Array.isArray(result?.items) ? result.items : []
        this.attractionTotal = Number(result?.total) || 0
      } catch (error) {
        await this.handleRequestError(error, 'attractionError')
      } finally {
        this.isLoadingAttractions = false
      }
    },
    async addAttraction(attraction) {
      if (this.addingAttractionId || !this.attractionDayId) return
      this.addingAttractionId = attraction.id
      this.attractionError = ''
      try {
        await this.routeStore.createStop(this.routeId, this.attractionDayId, { attractionId: attraction.id })
        this.addingAttractionId = null
        this.closeAttractionSheet()
      } catch (error) {
        await this.handleRequestError(error, 'attractionError')
      } finally {
        this.addingAttractionId = null
      }
    },
    openStopNoteSheet(day, stop) {
      this.editingStopDayId = day.id
      this.editingStopId = stop.id
      this.stopNote = stop.note || ''
      this.stopNoteError = ''
      this.showStopNoteSheet = true
    },
    closeStopNoteSheet() {
      if (this.isUpdatingStop) return
      this.showStopNoteSheet = false
      this.editingStopDayId = null
      this.editingStopId = null
      this.stopNote = ''
      this.stopNoteError = ''
    },
    async submitStopNote() {
      if (this.isUpdatingStop || !this.editingStopId) return
      const note = this.stopNote.trim()
      this.isUpdatingStop = true
      this.stopNoteError = ''
      try {
        await this.routeStore.updateStop(this.routeId, this.editingStopDayId, this.editingStopId, { note })
        this.isUpdatingStop = false
        this.closeStopNoteSheet()
      } catch (error) {
        await this.handleRequestError(error, 'stopNoteError')
      } finally {
        this.isUpdatingStop = false
      }
    },
    async confirmDeleteStop(day, stop) {
      if (this.deletingStopId) return
      const confirmed = await new Promise((resolve) => uni.showModal({ title: '确认移除这个景点？', content: '', success: (result) => resolve(Boolean(result.confirm)), fail: () => resolve(false) }))
      if (!confirmed) return
      this.deletingStopId = stop.id
      this.mutationError = ''
      try {
        await this.routeStore.deleteStop(this.routeId, day.id, stop.id)
      } catch (error) {
        await this.handleRequestError(error, 'mutationError')
      } finally {
        this.deletingStopId = null
      }
    },
    goBack() { uni.navigateBack({ delta: 1 }) },
  },
}
</script>

<style scoped>
.route-detail-page { min-height: 100vh; color: var(--tl-text-main); background: radial-gradient(circle at 88% 8%, rgba(210, 232, 242, .68) 0, rgba(210, 232, 242, 0) 190rpx), var(--tl-bg); }
.route-detail-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; margin: 0 auto; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 64rpx); }
.route-detail-header { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; margin-bottom: 34rpx; }.route-detail-header__back,.route-detail-header__spacer{flex:0 0 64rpx;width:64rpx;height:64rpx}.route-detail-header__back{padding:0 0 8rpx;font-size:64rpx;line-height:1;color:var(--tl-text-main);background:transparent}.route-detail-header__copy{display:flex;flex:1;flex-direction:column;align-items:center}.route-detail-header__eyebrow,.route-section__eyebrow{display:block;margin-bottom:5rpx;font-size:17rpx;font-weight:900;color:var(--tl-primary);letter-spacing:3rpx}.route-detail-header__title{font-size:45rpx;font-weight:900}.route-section__title{display:block;font-size:34rpx;font-weight:900}
.route-detail-state,.day-section__empty{padding:56rpx 34rpx;text-align:center;background:var(--tl-paper);border:3rpx dashed var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.route-link,.route-actions__delete{display:inline-block;margin-top:18rpx;font-size:24rpx;font-weight:800;color:var(--tl-primary-deep);text-decoration:underline}
.route-detail-card,.route-actions,.day-card{background:var(--tl-paper);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.route-detail-card{position:relative;padding:58rpx 32rpx 36rpx;overflow:hidden}.route-detail-card__tape{position:absolute;top:18rpx;left:50%;width:126rpx;height:28rpx;background:rgba(243,205,114,.7);transform:translateX(-50%) rotate(-4deg)}.route-detail-card__status,.route-actions__ready{display:inline-flex;padding:8rpx 15rpx;font-size:21rpx;font-weight:900;color:var(--tl-green-deep);background:var(--tl-green);border-radius:999rpx}.route-detail-card__title{display:block;margin:19rpx 0 22rpx;font-size:44rpx;font-weight:900}.route-detail-card__item{display:flex;gap:18rpx;margin-top:16rpx;font-size:27rpx}.route-detail-card__item text:first-child{flex:0 0 116rpx;color:var(--tl-text-secondary)}.route-detail-card__days{margin-top:30rpx;padding:20rpx;font-size:26rpx;font-weight:800;color:var(--tl-primary-deep);background:rgba(255,236,187,.52);border:2rpx dashed var(--tl-primary);border-radius:var(--tl-radius-md)}
.route-actions,.day-section{margin-top:34rpx}.route-actions{padding:28rpx}.route-actions__buttons,.day-section__heading,.day-card__topline{display:flex;align-items:center;justify-content:space-between;gap:14rpx}.route-actions__buttons,.day-section__heading-actions,.stop-section__actions{justify-content:flex-start;flex-wrap:wrap}.day-section__heading-actions,.stop-section__actions{display:flex;gap:12rpx;align-items:center}.route-actions button,.day-section button,.order-controls button{margin:0;padding:14rpx 20rpx;font-size:24rpx;font-weight:900;color:var(--tl-primary-deep);background:#fff0d2;border:2rpx solid var(--tl-primary);border-radius:999rpx}.route-error{display:block;margin-top:16rpx;font-size:23rpx;color:#b84a2f}.route-actions__delete,.day-card__delete{color:#a9523b}.day-section__heading{margin-bottom:18rpx}.day-section__list{display:flex;flex-direction:column;gap:18rpx}.day-card{padding:24rpx 26rpx}.day-card__topline{font-size:24rpx;font-weight:900}.day-card__topline view{display:flex;gap:16rpx;color:var(--tl-primary-deep)}.order-controls{display:flex;gap:12rpx;margin-top:14rpx}.order-controls--stop{margin-top:12rpx}.order-controls button{min-width:66rpx;padding:7rpx 16rpx}.day-card__date,.day-card__stops{display:block;margin-top:14rpx;font-size:23rpx;color:var(--tl-text-secondary)}.day-card__title{display:block;margin-top:6rpx;font-size:31rpx;font-weight:900}
.plan-generation-section{margin-top:34rpx;padding:28rpx;background:linear-gradient(135deg,rgba(255,244,211,.96),rgba(239,247,226,.9));border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-lg);box-shadow:var(--tl-shadow-card)}.plan-generation-section__copy,.plan-generation-section__hint{display:block;margin-top:13rpx;font-size:24rpx;line-height:1.55;color:var(--tl-text-secondary)}.plan-generation-section__hint{padding:12rpx 14rpx;color:var(--tl-primary-deep);background:rgba(255,236,187,.62);border-radius:var(--tl-radius-sm)}.plan-generation-section button{margin:20rpx 0 0;padding:16rpx 26rpx;font-size:26rpx;font-weight:900;color:var(--tl-paper);background:var(--tl-primary);border:2rpx solid var(--tl-primary-deep);border-radius:999rpx}.plan-generation-section button[disabled],.route-sheet__submit[disabled]{opacity:.48}
.route-sheet-mask{position:fixed;inset:0;z-index:60;display:flex;align-items:flex-end;background:rgba(70,43,20,.36)}.route-sheet{width:100%;max-width:var(--tl-content-max-width);margin:0 auto;padding:26rpx var(--tl-page-padding) calc(var(--tl-safe-bottom) + 34rpx);background:var(--tl-paper);border-radius:36rpx 36rpx 0 0}.route-sheet__heading{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:22rpx}.route-sheet__title{display:block;font-size:34rpx;font-weight:900}.route-sheet__heading button{width:56rpx;height:56rpx;padding:0;font-size:40rpx;line-height:1;color:var(--tl-text-secondary);background:var(--tl-paper-deep);border-radius:50%}.route-form-field{margin-bottom:18rpx}.route-form-field>text:first-child{display:block;margin-bottom:8rpx;font-size:23rpx;font-weight:800;color:var(--tl-text-secondary)}.route-form-field input,.route-form-field picker view{min-height:78rpx;padding:0 20rpx;font-size:27rpx;line-height:78rpx;background:var(--tl-paper-deep);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-md)}.route-form-field>text:last-child{display:inline-block;margin-top:8rpx;font-size:22rpx;color:var(--tl-primary-deep)}.route-sheet__submit{width:100%;min-height:92rpx;margin-top:18rpx;font-size:30rpx;font-weight:900;color:var(--tl-paper);background:var(--tl-primary);border:3rpx solid var(--tl-primary-deep);border-radius:var(--tl-radius-md)}
.plan-generation-sheet{max-height:88vh;overflow:auto}.plan-generation-sheet__block{margin-top:22rpx}.plan-generation-sheet__label,.plan-generation-result__title{display:block;font-size:25rpx;font-weight:900}.plan-generation-child-list{display:flex;gap:12rpx;margin-top:12rpx;overflow:auto}.plan-generation-child{flex:0 0 auto;min-width:156rpx;padding:16rpx 18rpx;background:var(--tl-paper-deep);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-md)}.plan-generation-child text{display:block;font-size:24rpx;font-weight:800}.plan-generation-child text+text{margin-top:5rpx;font-size:21rpx;font-weight:600;color:var(--tl-text-secondary)}.plan-generation-child--selected,.plan-generation-stop--selected{background:#fff0d2;border-color:var(--tl-primary)}.plan-generation-sheet__row{display:flex;justify-content:space-between;gap:16rpx}.plan-generation-sheet__row view{display:flex;gap:16rpx;font-size:22rpx;font-weight:900;color:var(--tl-primary-deep)}.plan-generation-day{margin-top:16rpx;padding:16rpx;background:rgba(239,247,226,.75);border-radius:var(--tl-radius-md)}.plan-generation-day__title{display:block;font-size:23rpx;font-weight:900;color:var(--tl-primary-deep)}.plan-generation-stop{display:flex;gap:13rpx;align-items:flex-start;margin-top:10rpx;padding:14rpx;background:var(--tl-paper);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-sm)}.plan-generation-stop__mark{font-size:25rpx;color:var(--tl-primary)}.plan-generation-stop__name,.plan-generation-stop__meta{display:block;font-size:24rpx;font-weight:800}.plan-generation-stop__meta{margin-top:4rpx;font-size:21rpx;font-weight:600;color:var(--tl-text-secondary)}.plan-generation-sheet__count{display:block;margin-top:18rpx;font-size:24rpx;font-weight:900;color:var(--tl-primary-deep)}.plan-generation-sheet__empty{padding:34rpx 16rpx;text-align:center;font-size:25rpx;color:var(--tl-text-secondary);background:var(--tl-paper-deep);border:2rpx dashed var(--tl-line);border-radius:var(--tl-radius-md)}.plan-generation-result{margin-top:20rpx;padding:18rpx;background:rgba(239,247,226,.9);border:2rpx solid var(--tl-green-deep);border-radius:var(--tl-radius-md)}.plan-generation-result__item{display:flex;justify-content:space-between;gap:14rpx;margin-top:12rpx;font-size:24rpx;font-weight:800}.plan-generation-result__item text:last-child{color:var(--tl-green-deep)}
.stop-section{margin-top:22rpx;padding-top:18rpx;border-top:2rpx dashed var(--tl-line)}.stop-section__heading,.stop-card__topline{display:flex;align-items:center;justify-content:space-between;gap:14rpx;font-size:23rpx;font-weight:800}.stop-section__heading text,.stop-section__actions text{color:var(--tl-primary-deep)}.stop-section__list{display:flex;flex-direction:column;gap:12rpx;margin-top:16rpx}.stop-card{padding:18rpx;background:var(--tl-paper-deep);border-radius:var(--tl-radius-md)}.stop-card__topline view{display:flex;gap:14rpx;font-size:20rpx;color:var(--tl-primary-deep)}.stop-card__name{font-size:27rpx;font-weight:900}.stop-card__meta,.stop-card__summary,.stop-card__note{display:block;margin-top:9rpx;font-size:22rpx;line-height:1.5;color:var(--tl-text-secondary)}.stop-card__note{padding:10rpx 12rpx;color:var(--tl-primary-deep);background:rgba(255,236,187,.55);border-radius:var(--tl-radius-sm)}
.attraction-sheet__city{display:block;margin-bottom:16rpx;font-size:24rpx;font-weight:800;color:var(--tl-primary-deep)}.attraction-sheet__search{display:flex;gap:12rpx;align-items:center}.attraction-sheet__search input{flex:1;min-width:0;min-height:70rpx;padding:0 18rpx;font-size:25rpx;background:var(--tl-paper-deep);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-md)}.attraction-sheet__search button,.attraction-card button{margin:0;padding:13rpx 18rpx;font-size:22rpx;font-weight:900;color:var(--tl-paper);background:var(--tl-primary);border:2rpx solid var(--tl-primary-deep);border-radius:999rpx}.attraction-sheet__state{padding:46rpx 12rpx;text-align:center;font-size:25rpx;color:var(--tl-text-secondary)}.attraction-sheet__list{display:flex;flex-direction:column;gap:14rpx;margin-top:20rpx;max-height:58vh;overflow:auto}.attraction-card{padding:20rpx;background:var(--tl-paper-deep);border:2rpx solid var(--tl-line);border-radius:var(--tl-radius-md)}.attraction-card__name{display:block;font-size:29rpx;font-weight:900}.attraction-card__meta,.attraction-card__summary{display:block;margin-top:8rpx;font-size:22rpx;line-height:1.45;color:var(--tl-text-secondary)}.attraction-card button{margin-top:14rpx}
</style>
