<template>
  <view class="profile-page">
    <view class="profile-page__paper">
      <view class="profile-header">
        <view>
          <text class="profile-header__title">我的</text>
          <text class="profile-header__subtitle">和孩子一起，发现更大的世界</text>
        </view>
        <button class="profile-header__settings" aria-label="账号与设置" @click="openSettings">
          <view class="profile-header__settings-icon" aria-hidden="true"></view>
        </button>
      </view>

      <view v-if="child.isLoading" class="profile-state">
        <text>正在同步孩子档案…</text>
      </view>
      <view v-else-if="child.error" class="profile-state profile-state--error">
        <text>孩子资料加载失败，请重试</text>
        <button class="profile-state__action" @click="loadChildren">重试</button>
      </view>
      <view v-else-if="child.isLoaded && child.children.length === 0" class="profile-state">
        <text class="profile-state__title">尚未添加孩子</text>
        <text class="profile-state__copy">添加孩子档案后，就能开始保存专属探索记录。</text>
        <button class="profile-state__action" @click="openAddChildForm">添加孩子</button>
      </view>
      <view v-else-if="activeChild" class="active-child-card">
        <button class="active-child-card__identity" @click="openManageChild">
          <view class="active-child-card__avatar" aria-hidden="true"><text>{{ childInitial }}</text></view>
          <view class="active-child-card__copy">
            <text class="active-child-card__name">{{ activeChild.name }}</text>
            <text class="active-child-card__meta"><template v-if="ageText">{{ ageText }} · </template>当前探索档案</text>
          </view>
          <text class="active-child-card__arrow" aria-hidden="true">›</text>
        </button>
        <view class="active-child-card__actions">
          <button class="active-child-card__action active-child-card__action--primary" @click="openChildSwitcher">切换孩子</button>
          <button class="active-child-card__action" @click="openManageChild">管理孩子</button>
        </view>
      </view>
      <view v-else class="profile-state"><text>正在同步孩子档案…</text></view>

      <view class="profile-section">
        <text class="profile-section__title">孩子与家庭</text>
        <view class="profile-list">
          <button class="profile-list__item" @click="openManageChild">
            <view class="profile-list__icon profile-list__icon--profile" aria-hidden="true"></view>
            <view class="profile-list__copy"><text>孩子档案</text><text>查看和编辑孩子的基本信息</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
          <button class="profile-list__item" @click="openAddChildForm">
            <view class="profile-list__icon profile-list__icon--add" aria-hidden="true"></view>
            <view class="profile-list__copy"><text>添加孩子</text><text>为家人添加新的孩子档案</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view v-if="activeChild" class="profile-section">
        <text class="profile-section__title">探索偏好</text>
        <view class="profile-list">
          <button class="profile-list__item" @click="openManageChild">
            <view class="profile-list__icon profile-list__icon--interest" aria-hidden="true"></view>
            <view class="profile-list__copy"><text>兴趣偏好</text><text>设置孩子感兴趣的探索主题</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view class="profile-section profile-section--last">
        <text class="profile-section__title">账号与设置</text>
        <view class="profile-list">
          <button class="profile-list__item" @click="openSettings">
            <view class="profile-list__icon profile-list__icon--settings" aria-hidden="true"></view>
            <view class="profile-list__copy"><text>账号与设置</text><text>查看账号信息与应用说明</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>
    </view>

    <view v-if="showChildForm" class="child-form-sheet">
      <view class="child-form-sheet__mask" @click="closeChildForm"></view>
      <view class="child-form-sheet__panel">
        <view class="child-form-sheet__header"><text>{{ childFormMode === 'create' ? '添加孩子' : '管理孩子' }}</text><button :disabled="isSavingChild" @click="closeChildForm">关闭</button></view>
        <view class="child-form-sheet__field"><text>姓名</text><input v-model="childForm.name" placeholder="请输入孩子姓名" /></view>
        <view class="child-form-sheet__field"><text>年龄</text><input v-model="childForm.age" type="number" placeholder="3-12" /></view>
        <view class="child-form-sheet__field"><text>城市</text><input v-model="childForm.city" placeholder="可不填" /></view>
        <view class="child-form-sheet__field">
          <text>兴趣偏好</text>
          <view class="child-form-sheet__interests">
            <button v-for="interest in interestOptions" :key="interest" :class="{ 'child-form-sheet__interest--selected': childForm.interests.includes(interest) }" class="child-form-sheet__interest" @click="toggleChildInterest(interest)">{{ interest }}</button>
          </view>
        </view>
        <button class="child-form-sheet__submit" :disabled="isSavingChild" @click="saveChildProfile">{{ isSavingChild ? '保存中…' : '保存档案' }}</button>
      </view>
    </view>
    <AppTabbar active="profile" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

const DEFAULT_INTERESTS = ['历史故事', '古建筑', '观察探索']

export default {
  components: { AppTabbar },
  data() {
    return {
      showChildForm: false,
      isSavingChild: false,
      childFormMode: 'create',
      pendingChildAction: '',
      childForm: { name: '', age: '7', city: '', interests: [...DEFAULT_INTERESTS] },
      interestOptions: DEFAULT_INTERESTS,
    }
  },
  computed: {
    child() { return useChildStore() },
    user() { return useUserStore() },
    activeChild() { return this.child.activeChild },
    childInitial() { return String(this.activeChild?.name || '孩').trim().slice(0, 1) || '孩' },
    ageText() { return Number.isInteger(this.activeChild?.age) ? `${this.activeChild.age}岁` : '' },
    canSwitchChild() { return this.child.children.length > 1 },
  },
  onLoad(options) {
    this.pendingChildAction = options?.childAction || ''
  },
  async onShow() {
    await this.user.restoreSession()
    if (!this.user.isLoggedIn) {
      uni.reLaunch({ url: '/pages/login/index' })
      return
    }
    await this.loadChildren()
    this.runPendingChildAction()
  },
  methods: {
    showToast(title) { uni.showToast({ title, icon: 'none' }) },
    async loadChildren() {
      try {
        await this.child.fetchChildren(this.user.userInfo.id)
      } catch (error) {
        if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    runPendingChildAction() {
      const action = this.pendingChildAction
      this.pendingChildAction = ''
      if (action === 'create') this.openAddChildForm()
      if (action === 'manage' && this.activeChild) this.openEditChildForm()
    },
    openChildSwitcher() {
      if (!this.canSwitchChild) {
        this.showToast('添加更多孩子后即可切换')
        return
      }
      uni.navigateTo({ url: '/pages/child-switch/index' })
    },
    openSettings() { uni.navigateTo({ url: '/pages/settings/index' }) },
    openManageChild() {
      if (this.activeChild) this.openEditChildForm()
      else this.openAddChildForm()
    },
    openAddChildForm() {
      this.childFormMode = 'create'
      this.childForm = { name: '', age: '7', city: '', interests: [...DEFAULT_INTERESTS] }
      this.showChildForm = true
    },
    openEditChildForm() {
      const current = this.activeChild
      this.childFormMode = 'edit'
      this.childForm = {
        name: current?.name || '',
        age: Number.isInteger(current?.age) ? String(current.age) : '',
        city: current?.city || '',
        interests: current?.interests?.length ? [...current.interests] : [...DEFAULT_INTERESTS],
      }
      this.showChildForm = true
    },
    openChildForm() { this.openManageChild() },
    closeChildForm() {
      if (!this.isSavingChild) this.showChildForm = false
    },
    toggleChildInterest(interest) {
      if (this.childForm.interests.includes(interest)) {
        if (this.childForm.interests.length > 1) this.childForm.interests = this.childForm.interests.filter((item) => item !== interest)
        return
      }
      this.childForm.interests = [...this.childForm.interests, interest]
    },
    validateChildForm() {
      const age = Number(this.childForm.age)
      if (!this.childForm.name.trim()) {
        this.showToast('请输入孩子姓名')
        return false
      }
      if (!Number.isInteger(age) || age < 3 || age > 12) {
        this.showToast('年龄需为 3 到 12 岁')
        return false
      }
      return true
    },
    async saveChildProfile() {
      if (this.isSavingChild || !this.validateChildForm()) return
      const payload = { name: this.childForm.name.trim(), age: Number(this.childForm.age), city: this.childForm.city.trim(), interests: [...this.childForm.interests] }
      this.isSavingChild = true
      try {
        if (this.childFormMode === 'create') {
          const savedChild = await this.child.createChild(payload)
          this.child.setActiveChild(savedChild.id)
        } else if (this.activeChild) {
          await this.child.updateChild(this.activeChild.id, payload)
        }
        this.showChildForm = false
        this.showToast('孩子档案已保存')
      } catch (error) {
        this.showToast(error?.message || '保存失败，请稍后重试')
      } finally {
        this.isSavingChild = false
      }
    },
  },
}
</script>

<style scoped>
.profile-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }
.profile-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 40rpx); margin: 0 auto; }
.profile-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 40rpx; }.profile-header__title,.profile-header__subtitle { display: block; }.profile-header__title { font-size: var(--tl-type-page-title); font-weight: var(--tl-weight-page-title); line-height: 1.25; }.profile-header__subtitle { margin-top: 10rpx; font-size: var(--tl-type-body); line-height: 1.5; color: var(--tl-text-secondary); }
.profile-header__settings { display: flex; align-items: center; justify-content: center; width: 88rpx; min-width: 88rpx; height: 88rpx; }.profile-header__settings-icon { position: relative; width: 34rpx; height: 34rpx; border: 4rpx solid #315248; border-radius: 50%; }.profile-header__settings-icon::before,.profile-header__settings-icon::after { position: absolute; inset: -9rpx; content: ''; border: 3rpx solid #315248; border-radius: 10rpx; transform: rotate(45deg); }.profile-header__settings-icon::after { inset: 8rpx; background: var(--tl-bg); border: 0; border-radius: 50%; }
.active-child-card,.profile-state { background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-sheet); box-shadow: var(--tl-shadow-media); }.active-child-card { overflow: hidden; }.active-child-card__identity { display: flex; align-items: center; width: 100%; min-height: 170rpx; padding: 30rpx; text-align: left; }.active-child-card__avatar { display: flex; flex: 0 0 104rpx; align-items: center; justify-content: center; width: 104rpx; height: 104rpx; margin-right: 24rpx; font-size: 42rpx; font-weight: 600; color: #fff; background: #1f7b47; border-radius: 50%; }.active-child-card__copy { flex: 1; min-width: 0; }.active-child-card__name,.active-child-card__meta { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.active-child-card__name { font-size: 34rpx; font-weight: 700; }.active-child-card__meta { margin-top: 10rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.active-child-card__arrow,.profile-list__arrow { flex: 0 0 auto; margin-left: 16rpx; font-size: 42rpx; font-weight: 300; color: var(--tl-text-secondary); }.active-child-card__actions { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; padding: 16rpx 30rpx 28rpx; border-top: 1rpx solid var(--tl-divider); }.active-child-card__action { min-height: 76rpx; font-size: var(--tl-type-meta); font-weight: 600; color: #315248; background: #eff7f1; border-radius: var(--tl-radius-control); }.active-child-card__action--primary { color: #17673c; background: #e2f3e7; }
.profile-state { display: flex; flex-direction: column; gap: 18rpx; align-items: flex-start; padding: 32rpx; font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); }.profile-state--error { color: #a34a38; }.profile-state__title { font-size: var(--tl-type-section-title); font-weight: 700; color: var(--tl-text-main); }.profile-state__copy { color: var(--tl-text-secondary); }.profile-state__action { min-height: 72rpx; padding: 0 24rpx; font-size: var(--tl-type-meta); font-weight: 600; color: #17673c; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-control); }
.profile-section { margin-top: 52rpx; }.profile-section--last { padding-bottom: 12rpx; }.profile-section__title { display: block; margin-bottom: 20rpx; font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }.profile-list { overflow: hidden; background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-media); box-shadow: var(--tl-shadow-media); }.profile-list__item { display: flex; align-items: center; width: 100%; min-height: 120rpx; padding: 18rpx 24rpx; color: var(--tl-text-main); text-align: left; }.profile-list__item + .profile-list__item { border-top: 1rpx solid var(--tl-divider); }.profile-list__icon { position: relative; display: flex; flex: 0 0 56rpx; align-items: center; justify-content: center; width: 56rpx; height: 56rpx; margin-right: 20rpx; color: #315248; }.profile-list__icon::before,.profile-list__icon::after { position: absolute; box-sizing: border-box; content: ''; }.profile-list__icon--profile::before { top: 3rpx; width: 21rpx; height: 21rpx; border: 3rpx solid currentColor; border-radius: 50%; }.profile-list__icon--profile::after { bottom: 2rpx; width: 40rpx; height: 24rpx; border: 3rpx solid currentColor; border-bottom: 0; border-radius: 24rpx 24rpx 0 0; }.profile-list__icon--add::before { width: 42rpx; height: 42rpx; border: 3rpx solid currentColor; border-radius: 50%; }.profile-list__icon--add::after { width: 20rpx; height: 3rpx; background: currentColor; transform: rotate(90deg); }.profile-list__icon--interest::before { width: 34rpx; height: 24rpx; border: 3rpx solid currentColor; border-radius: 24rpx 4rpx 24rpx 4rpx; transform: rotate(-38deg); }.profile-list__icon--interest::after { width: 3rpx; height: 42rpx; background: currentColor; transform: rotate(45deg); }.profile-list__icon--settings::before { width: 38rpx; height: 38rpx; border: 3rpx solid currentColor; border-radius: 50%; }.profile-list__icon--settings::after { width: 12rpx; height: 12rpx; background: currentColor; border-radius: 50%; }.profile-list__copy { flex: 1; min-width: 0; }.profile-list__copy text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.profile-list__copy text:first-child { font-size: var(--tl-type-body); font-weight: 600; }.profile-list__copy text:last-child { margin-top: 6rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }
.child-form-sheet { position: fixed; inset: 0; z-index: 80; }.child-form-sheet__mask { position: absolute; inset: 0; background: rgba(47, 35, 25, .28); }.child-form-sheet__panel { position: absolute; right: 0; bottom: 0; left: 0; max-height: 84vh; padding: 32rpx var(--tl-page-padding) calc(32rpx + var(--tl-safe-bottom)); overflow-y: auto; background: var(--tl-surface); border-radius: var(--tl-radius-sheet) var(--tl-radius-sheet) 0 0; box-shadow: var(--tl-shadow-overlay); }.child-form-sheet__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28rpx; font-size: var(--tl-type-section-title); font-weight: 700; }.child-form-sheet__header button { min-height: 64rpx; padding: 0 12rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.child-form-sheet__field { margin-top: 22rpx; }.child-form-sheet__field > text { display: block; margin-bottom: 12rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.child-form-sheet__field input { width: 100%; height: 84rpx; padding: 0 20rpx; font-size: var(--tl-type-body); color: var(--tl-text-main); background: var(--tl-surface-muted); border-radius: var(--tl-radius-control); }.child-form-sheet__interests { display: flex; flex-wrap: wrap; gap: 12rpx; }.child-form-sheet__interest { min-height: 64rpx; padding: 0 18rpx; font-size: var(--tl-type-meta); color: #315248; background: #eff7f1; border-radius: var(--tl-radius-control); }.child-form-sheet__interest--selected { color: #17673c; background: #e2f3e7; }.child-form-sheet__submit { width: 100%; min-height: var(--tl-control-min-height); margin-top: 36rpx; font-size: var(--tl-type-primary-action); font-weight: 600; color: #fff; background: #1f7b47; border-radius: var(--tl-radius-control); }.child-form-sheet__submit[disabled] { opacity: .55; }
@media (min-width: 431px) { .profile-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 22px); }.profile-header { margin-bottom: 20px; }.profile-header__settings { width: 44px; min-width: 44px; height: 44px; }.profile-header__settings-icon { width: 17px; height: 17px; border-width: 2px; }.profile-header__settings-icon::before { inset: -5px; border-width: 1px; }.profile-header__settings-icon::after { inset: 4px; }.active-child-card__identity { min-height: 85px; padding: 15px; }.active-child-card__avatar { flex-basis: 52px; width: 52px; height: 52px; margin-right: 12px; font-size: 21px; }.active-child-card__actions { padding: 8px 15px 14px; gap: 8px; }.active-child-card__action { min-height: 38px; }.profile-section { margin-top: 26px; }.profile-list__item { min-height: 60px; padding: 9px 12px; }.profile-list__icon { flex-basis: 28px; width: 28px; height: 28px; margin-right: 10px; }.child-form-sheet__panel { max-width: var(--tl-content-max-width); margin: 0 auto; padding: 16px 18px calc(16px + var(--tl-safe-bottom)); } }
</style>
