<template>
  <view class="child-edit-page">
    <view v-if="loadState === 'loading'" class="child-edit-page__paper child-edit-page__paper--loading">
      <view class="child-edit-header">
        <view class="child-edit-header__placeholder"></view>
        <view class="child-edit-header__title-placeholder"></view>
        <view class="child-edit-header__placeholder"></view>
      </view>
      <view class="child-edit-skeleton" v-for="item in 4" :key="item"></view>
    </view>

    <view v-else-if="loadState === 'error'" class="child-edit-page__paper child-edit-page__paper--state">
      <text class="child-edit-state__title">儿童资料加载失败</text>
      <text class="child-edit-state__copy">请检查网络后重试，已填写的内容不会被清除。</text>
      <button class="child-edit-state__action" @click="loadChildDetail">重试</button>
    </view>

    <view v-else-if="loadState === 'missing'" class="child-edit-page__paper child-edit-page__paper--state">
      <text class="child-edit-state__title">该儿童资料不存在或已被删除</text>
    </view>

    <view v-else class="child-edit-page__paper">
      <view class="child-edit-header">
        <button class="child-edit-header__back" aria-label="返回" :disabled="isSubmitting" @click="requestLeave">‹</button>
        <text class="child-edit-header__title">{{ isCreateMode ? '添加孩子' : '儿童资料' }}</text>
        <view class="child-edit-header__spacer"></view>
      </view>

      <view class="child-edit-section child-edit-section--avatars">
        <text class="child-edit-section__label">选择头像</text>
        <view class="child-edit-avatar-grid">
          <button
            v-for="avatar in childAvatars"
            :key="avatar.key"
            class="child-edit-avatar"
            :class="{ 'child-edit-avatar--selected': form.avatarPreset === avatar.key }"
            :aria-label="`选择${avatar.label}头像`"
            @click="selectAvatar(avatar.key)"
          >
            <image :src="avatar.src" mode="aspectFit" />
            <text>{{ avatar.label }}</text>
          </button>
        </view>
        <text v-if="fieldErrors.avatarPreset" class="child-edit-field__error">{{ fieldErrors.avatarPreset }}</text>
      </view>

      <view class="child-edit-section">
        <text class="child-edit-section__label" for="child-name">孩子昵称</text>
        <input
          id="child-name"
          v-model="form.name"
          class="child-edit-input"
          :class="{ 'child-edit-input--error': fieldErrors.name }"
          maxlength="50"
          placeholder="请输入孩子昵称"
          confirm-type="next"
          :adjust-position="true"
          @input="clearFieldError('name')"
          @blur="validateField('name')"
        />
        <text v-if="fieldErrors.name" class="child-edit-field__error">{{ fieldErrors.name }}</text>
      </view>

      <view class="child-edit-section">
        <text class="child-edit-section__label">年龄</text>
        <picker class="child-edit-picker" mode="selector" :range="ageLabels" :value="agePickerIndex" @change="selectAge">
          <view class="child-edit-picker__value" :class="{ 'child-edit-picker__value--placeholder': form.age === null }">
            <text>{{ form.age === null ? '请选择年龄' : `${form.age}岁` }}</text>
            <text aria-hidden="true">›</text>
          </view>
        </picker>
        <text v-if="fieldErrors.age" class="child-edit-field__error">{{ fieldErrors.age }}</text>
      </view>

      <view class="child-edit-section">
        <text class="child-edit-section__label" for="child-city">所在城市（可选）</text>
        <input
          id="child-city"
          v-model="form.city"
          class="child-edit-input"
          :class="{ 'child-edit-input--error': fieldErrors.city }"
          maxlength="50"
          placeholder="请输入所在城市"
          :adjust-position="true"
          @input="clearFieldError('city')"
          @blur="validateField('city')"
        />
        <text v-if="fieldErrors.city" class="child-edit-field__error">{{ fieldErrors.city }}</text>
      </view>

      <view class="child-edit-section">
        <text class="child-edit-section__label">兴趣</text>
        <view class="child-edit-tags">
          <button
            v-for="interest in interestOptions"
            :key="interest"
            class="child-edit-tag"
            :class="{ 'child-edit-tag--selected': form.interests.includes(interest) }"
            @click="toggleInterest(interest)"
          >{{ interest }}</button>
          <button class="child-edit-tag child-edit-tag--add" @click="showCustomInterestInput = !showCustomInterestInput">＋ 自定义</button>
        </view>
        <view v-if="form.customInterests.length" class="child-edit-custom-tags">
          <button v-for="interest in form.customInterests" :key="interest" class="child-edit-tag child-edit-tag--selected" @click="removeCustomInterest(interest)">
            {{ interest }} <text aria-hidden="true">×</text>
          </button>
        </view>
        <view v-if="showCustomInterestInput" class="child-edit-custom-input">
          <input
            v-model="customInterest"
            maxlength="30"
            placeholder="输入自定义兴趣"
            :adjust-position="true"
            @confirm="addCustomInterest"
            @input="customInterestError = ''"
          />
          <button @click="addCustomInterest">添加</button>
        </view>
        <text v-if="customInterestError" class="child-edit-field__error">{{ customInterestError }}</text>
        <text v-else-if="fieldErrors.interests" class="child-edit-field__error">{{ fieldErrors.interests }}</text>
      </view>

      <view v-if="isCreateMode" class="child-edit-consent">
        <button class="child-edit-consent__check" :class="{ 'child-edit-consent__check--selected': form.guardianConsent }" @click="toggleGuardianConsent">
          <text aria-hidden="true">{{ form.guardianConsent ? '✓' : '' }}</text>
        </button>
        <button class="child-edit-consent__copy" @click="toggleGuardianConsent">我是孩子的监护人，并同意为其创建儿童资料</button>
      </view>
      <view v-else-if="childDetail?.guardianConsentGranted" class="child-edit-consent child-edit-consent--confirmed">
        <text>监护人同意已确认</text>
      </view>
      <view v-else class="child-edit-consent">
        <button class="child-edit-consent__check" :class="{ 'child-edit-consent__check--selected': form.guardianConsent }" @click="toggleGuardianConsent">
          <text aria-hidden="true">{{ form.guardianConsent ? '✓' : '' }}</text>
        </button>
        <button class="child-edit-consent__copy" @click="toggleGuardianConsent">我是孩子的监护人，并确认继续保存该儿童资料</button>
      </view>

      <view v-if="!isCreateMode" class="child-edit-privacy">
        <text class="child-edit-privacy__title">数据与隐私</text>
        <button class="child-edit-privacy__delete" :disabled="isSubmitting" @click="requestDelete">删除儿童资料</button>
      </view>
    </view>

    <view v-if="loadState === 'ready'" class="child-edit-actions" :style="bottomActionStyle">
      <view class="child-edit-actions__inner">
        <text v-if="formError" class="child-edit-actions__error">{{ formError }}</text>
        <button class="child-edit-actions__save" :disabled="!canSave" @click="saveProfile">{{ isSubmitting ? '保存中…' : (isCreateMode ? '保存' : '保存修改') }}</button>
      </view>
    </view>

    <view v-if="showDeleteNameDialog" class="child-edit-dialog" role="dialog" aria-modal="true" aria-label="确认删除儿童资料">
      <view class="child-edit-dialog__mask" @click="closeDeleteNameDialog"></view>
      <view class="child-edit-dialog__panel">
        <text class="child-edit-dialog__title">确认删除儿童资料</text>
        <text class="child-edit-dialog__copy">请输入孩子昵称以确认：{{ childDetail?.name }}</text>
        <input v-model="deleteName" class="child-edit-input" :adjust-position="true" placeholder="请输入孩子昵称" />
        <view class="child-edit-dialog__actions">
          <button :disabled="isDeleting" @click="closeDeleteNameDialog">取消</button>
          <button class="child-edit-dialog__confirm" :disabled="!deleteNameMatches || isDeleting" @click="deleteProfile">{{ isDeleting ? '删除中…' : '确认删除' }}</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { CHILD_AVATARS, CHILD_AVATAR_KEYS } from '../../constants/childAvatars.js'
import { getChild } from '../../api/children.js'
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { isAuthenticationError } from '../../utils/request'
import { endUserSession } from '../../utils/sessionBoundary'

const INTEREST_OPTIONS = ['历史故事', '古建筑', '观察探索', '动物', '手工']
const AGE_OPTIONS = Array.from({ length: 10 }, (_, index) => index + 3)

function emptyForm() {
  return {
    avatarPreset: '',
    name: '',
    age: null,
    city: '',
    interests: [],
    customInterests: [],
    guardianConsent: false,
  }
}

export default {
  data() {
    return {
      childId: null,
      childDetail: null,
      loadState: 'loading',
      isSubmitting: false,
      isDeleting: false,
      form: emptyForm(),
      initialSnapshot: '',
      fieldErrors: {},
      formError: '',
      customInterest: '',
      customInterestError: '',
      showCustomInterestInput: false,
      showDeleteNameDialog: false,
      deleteName: '',
      keyboardHeight: 0,
      keyboardHeightHandler: null,
    }
  },
  computed: {
    child() { return useChildStore() },
    user() { return useUserStore() },
    childAvatars() { return CHILD_AVATARS },
    interestOptions() { return INTEREST_OPTIONS },
    ageLabels() { return AGE_OPTIONS.map((age) => `${age}岁`) },
    agePickerIndex() { return Math.max(AGE_OPTIONS.indexOf(this.form.age), 0) },
    isCreateMode() { return this.childId === null },
    requiresGuardianConsent() { return !this.isCreateMode && !this.childDetail?.guardianConsentGranted },
    isDirty() { return !this.isCreateMode && Boolean(this.initialSnapshot) && this.initialSnapshot !== this.snapshotForm() },
    isFormValid() { return Object.keys(this.collectValidationErrors()).length === 0 },
    canSave() {
      if (this.isSubmitting || !this.isFormValid) return false
      if (this.isCreateMode) return this.form.guardianConsent === true
      return this.isDirty && (!this.requiresGuardianConsent || this.form.guardianConsent === true)
    },
    deleteNameMatches() {
      return this.deleteName.trim() === String(this.childDetail?.name || '').trim()
    },
    bottomActionStyle() {
      return { bottom: `${this.keyboardHeight}px` }
    },
  },
  async onLoad(options) {
    this.childId = this.parseChildId(options?.id)
    this.bindKeyboardHeight()
    await this.preparePage(options?.id)
  },
  onUnload() {
    if (this.keyboardHeightHandler && typeof uni.offKeyboardHeightChange === 'function') {
      uni.offKeyboardHeightChange(this.keyboardHeightHandler)
    }
  },
  onBackPress() {
    if (this.isDirty) {
      this.showDiscardDialog()
      return true
    }
    return false
  },
  methods: {
    parseChildId(value) {
      const childId = Number(value)
      return Number.isInteger(childId) && childId > 0 ? childId : null
    },
    bindKeyboardHeight() {
      if (typeof uni.onKeyboardHeightChange !== 'function') return
      this.keyboardHeightHandler = (event) => {
        this.keyboardHeight = Math.max(0, Number(event?.height) || 0)
      }
      uni.onKeyboardHeightChange(this.keyboardHeightHandler)
    },
    async preparePage(requestedChildId) {
      await this.user.restoreSession()
      if (!this.user.isLoggedIn) {
        uni.reLaunch({ url: '/pages/login/index' })
        return
      }
      if (requestedChildId !== undefined && this.childId === null) {
        this.loadState = 'missing'
        this.showToast('该儿童资料不存在或已被删除')
        this.returnToProfile()
        return
      }
      if (this.isCreateMode) {
        this.initializeForm(null)
        this.loadState = 'ready'
        return
      }
      await this.loadChildDetail()
    },
    async loadChildDetail() {
      this.loadState = 'loading'
      try {
        const data = await getChild(this.childId)
        if (!data?.child) throw new Error('Child detail is missing')
        this.initializeForm(data.child)
        this.loadState = 'ready'
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        if (error?.code === 'CHILD_NOT_FOUND' || error?.statusCode === 404) {
          await this.handleMissingChild()
          return
        }
        this.loadState = 'error'
      }
    },
    initializeForm(child) {
      const interests = Array.isArray(child?.interests) ? child.interests : []
      const standardInterests = interests.filter((interest) => INTEREST_OPTIONS.includes(interest))
      const customInterests = interests.filter((interest) => !INTEREST_OPTIONS.includes(interest))
      this.childDetail = child
      this.form = {
        avatarPreset: CHILD_AVATAR_KEYS.includes(child?.avatarPreset) ? child.avatarPreset : '',
        name: child?.name || '',
        age: AGE_OPTIONS.includes(child?.age) ? child.age : null,
        city: child?.city || '',
        interests: standardInterests,
        customInterests,
        guardianConsent: false,
      }
      this.fieldErrors = {}
      this.formError = ''
      this.customInterest = ''
      this.customInterestError = ''
      this.showCustomInterestInput = false
      this.initialSnapshot = this.snapshotForm()
    },
    snapshotForm() {
      return JSON.stringify({
        avatarPreset: this.form.avatarPreset,
        name: this.form.name,
        age: this.form.age,
        city: this.form.city,
        interests: this.form.interests,
        customInterests: this.form.customInterests,
        guardianConsent: this.form.guardianConsent,
      })
    },
    collectValidationErrors() {
      const errors = {}
      const name = this.form.name.trim()
      const city = this.form.city.trim()
      const interests = [...this.form.interests, ...this.form.customInterests]
      if (!CHILD_AVATAR_KEYS.includes(this.form.avatarPreset)) errors.avatarPreset = '请选择一个预设头像'
      if (name.length < 1 || name.length > 50) errors.name = '昵称需为 1–50 个字符'
      if (!AGE_OPTIONS.includes(this.form.age)) errors.age = '请选择 3–12 岁'
      if (city.length > 50) errors.city = '城市最多 50 个字符'
      if (interests.length > 10 || interests.some((interest) => !interest || interest.length > 30)) {
        errors.interests = '兴趣最多 10 项，每项不超过 30 个字符'
      }
      return errors
    },
    validateForSave() {
      this.fieldErrors = this.collectValidationErrors()
      if (Object.keys(this.fieldErrors).length) return false
      if (this.isCreateMode && this.form.guardianConsent !== true) {
        this.formError = '请先确认监护人同意'
        return false
      }
      if (this.requiresGuardianConsent && this.form.guardianConsent !== true) {
        this.formError = '请先确认监护人同意'
        return false
      }
      return true
    },
    clearFieldError(field) {
      if (this.fieldErrors[field]) {
        const errors = { ...this.fieldErrors }
        delete errors[field]
        this.fieldErrors = errors
      }
      this.formError = ''
    },
    validateField(field) {
      const errors = this.collectValidationErrors()
      if (errors[field]) {
        this.fieldErrors = { ...this.fieldErrors, [field]: errors[field] }
        return
      }
      this.clearFieldError(field)
    },
    selectAvatar(avatarPreset) {
      this.form.avatarPreset = avatarPreset
      this.clearFieldError('avatarPreset')
    },
    selectAge(event) {
      const index = Number(event?.detail?.value)
      this.form.age = AGE_OPTIONS[index] || null
      this.clearFieldError('age')
    },
    toggleInterest(interest) {
      if (this.form.interests.includes(interest)) {
        this.form.interests = this.form.interests.filter((item) => item !== interest)
        this.clearFieldError('interests')
        return
      }
      if (this.selectedInterests().length >= 10) {
        this.fieldErrors = { ...this.fieldErrors, interests: '兴趣最多选择 10 项' }
        return
      }
      this.form.interests = [...this.form.interests, interest]
      this.clearFieldError('interests')
    },
    selectedInterests() {
      return [...this.form.interests, ...this.form.customInterests]
    },
    addCustomInterest() {
      const interest = this.customInterest.trim()
      if (!interest) {
        this.customInterestError = ''
        return
      }
      if (interest.length > 30) {
        this.customInterestError = '自定义兴趣最多 30 个字符'
        return
      }
      if (INTEREST_OPTIONS.includes(interest) || this.selectedInterests().includes(interest)) {
        this.customInterestError = '该兴趣已经添加'
        return
      }
      if (this.selectedInterests().length >= 10) {
        this.customInterestError = '兴趣最多选择 10 项'
        return
      }
      this.form.customInterests = [...this.form.customInterests, interest]
      this.customInterest = ''
      this.customInterestError = ''
      this.clearFieldError('interests')
    },
    removeCustomInterest(interest) {
      this.form.customInterests = this.form.customInterests.filter((item) => item !== interest)
      this.clearFieldError('interests')
    },
    toggleGuardianConsent() {
      this.form.guardianConsent = !this.form.guardianConsent
      this.formError = ''
    },
    buildPayload() {
      const payload = {
        avatarPreset: this.form.avatarPreset,
        name: this.form.name.trim(),
        age: this.form.age,
        city: this.form.city.trim() || null,
        interests: this.selectedInterests(),
      }
      if (this.isCreateMode || (this.requiresGuardianConsent && this.form.guardianConsent)) {
        payload.guardianConsent = true
      }
      return payload
    },
    async saveProfile() {
      if (this.isSubmitting || !this.validateForSave()) return
      if (!this.isCreateMode && !this.isDirty) return

      this.isSubmitting = true
      this.formError = ''
      try {
        const savedChild = this.isCreateMode
          ? await this.child.createChild(this.buildPayload())
          : await this.child.updateChild(this.childId, this.buildPayload())
        if (this.isCreateMode) this.child.setActiveChild(savedChild.id)
        this.initialSnapshot = this.snapshotForm()
        uni.navigateBack()
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.applySaveError(error)
      } finally {
        this.isSubmitting = false
      }
    },
    applySaveError(error) {
      const fieldByCode = {
        INVALID_CHILD_AVATAR: 'avatarPreset',
        INVALID_CHILD_NAME: 'name',
        INVALID_CHILD_AGE: 'age',
        INVALID_CHILD_CITY: 'city',
        INVALID_CHILD_INTERESTS: 'interests',
      }
      const field = fieldByCode[error?.code]
      if (field) {
        this.fieldErrors = { ...this.fieldErrors, [field]: error?.message || '请检查此项' }
        return
      }
      this.formError = error?.message || '保存失败，请稍后重试'
    },
    requestLeave() {
      if (this.isSubmitting) return
      if (!this.isDirty) {
        uni.navigateBack()
        return
      }
      this.showDiscardDialog()
    },
    showDiscardDialog() {
      uni.showModal({
        title: '放弃本次修改？',
        content: '未保存的修改将不会保留。',
        cancelText: '继续编辑',
        confirmText: '放弃修改',
        success: (result) => {
          if (result?.confirm) uni.navigateBack()
        },
      })
    },
    requestDelete() {
      if (this.isSubmitting || this.isDeleting) return
      uni.showModal({
        title: '删除儿童资料？',
        content: '将删除该儿童的探索计划、任务、提交内容、照片和探索记录。家庭共享路线不会删除，其他孩子资料不会受到影响。操作不可恢复。',
        cancelText: '取消',
        confirmText: '继续',
        success: (result) => {
          if (result?.confirm) {
            this.deleteName = ''
            this.showDeleteNameDialog = true
          }
        },
      })
    },
    closeDeleteNameDialog() {
      if (this.isDeleting) return
      this.showDeleteNameDialog = false
      this.deleteName = ''
    },
    async deleteProfile() {
      if (!this.deleteNameMatches || this.isDeleting) return
      this.isDeleting = true
      this.formError = ''
      try {
        const result = await this.child.deleteChild(this.childId)
        this.showDeleteNameDialog = false
        if (result.currentChild) {
          uni.navigateBack()
          return
        }
        uni.reLaunch({ url: '/pages/profile/index' })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.formError = error?.message || '删除失败，请稍后重试'
      } finally {
        this.isDeleting = false
      }
    },
    async handleMissingChild() {
      this.loadState = 'missing'
      this.showToast('该儿童资料不存在或已被删除')
      try {
        await this.child.fetchChildren(this.user.userInfo.id)
      } catch (error) {
        if (isAuthenticationError(error)) await endUserSession()
      }
      this.returnToProfile()
    },
    returnToProfile() {
      uni.navigateBack({
        fail: () => uni.reLaunch({ url: '/pages/profile/index' }),
      })
    },
    showToast(title) {
      uni.showToast({ title, icon: 'none' })
    },
  },
}
</script>

<style scoped>
.child-edit-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }
.child-edit-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(232rpx + var(--tl-safe-bottom)); margin: 0 auto; box-sizing: border-box; }
.child-edit-page__paper--state { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; min-height: 70vh; }.child-edit-state__title { font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }.child-edit-state__copy { margin-top: 16rpx; font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); }.child-edit-state__action { min-height: var(--tl-control-min-height); margin-top: 30rpx; padding: 0 30rpx; color: #fff; background: #1f7b47; border-radius: var(--tl-radius-control); }
.child-edit-header { display: grid; grid-template-columns: 88rpx 1fr 88rpx; align-items: center; min-height: 88rpx; margin-bottom: 26rpx; }.child-edit-header__back { min-width: 88rpx; min-height: 88rpx; padding: 0; font-size: 58rpx; font-weight: 300; line-height: 1; color: var(--tl-text-main); text-align: left; }.child-edit-header__title { font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); text-align: center; }.child-edit-header__spacer { min-width: 88rpx; }.child-edit-header__placeholder,.child-edit-header__title-placeholder,.child-edit-skeleton { background: linear-gradient(90deg, rgba(218, 220, 195, .48), rgba(238, 238, 219, .9), rgba(218, 220, 195, .48)); border-radius: 12rpx; }.child-edit-header__placeholder { width: 64rpx; height: 64rpx; }.child-edit-header__title-placeholder { width: 150rpx; height: 34rpx; margin: 0 auto; }.child-edit-skeleton { height: 148rpx; margin-top: 24rpx; }
.child-edit-section { padding: 32rpx 0; border-top: 1rpx solid var(--tl-divider); }.child-edit-section--avatars { padding-top: 12rpx; border-top: 0; }.child-edit-section__label { display: block; margin-bottom: 18rpx; font-size: var(--tl-type-body); font-weight: 600; }.child-edit-avatar-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18rpx; }.child-edit-avatar { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 176rpx; padding: 12rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); background: transparent; border: 2rpx solid transparent; border-radius: var(--tl-radius-media); }.child-edit-avatar image { width: 104rpx; height: 104rpx; }.child-edit-avatar text { margin-top: 6rpx; }.child-edit-avatar--selected { color: #17673c; background: rgba(226, 243, 231, .5); border-color: #1f7b47; }
.child-edit-input,.child-edit-picker { width: 100%; min-height: var(--tl-control-min-height); padding: 0 24rpx; font-size: var(--tl-type-body); color: var(--tl-text-main); background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); box-sizing: border-box; }.child-edit-input--error { border-color: #b4513d; }.child-edit-picker__value { display: flex; align-items: center; justify-content: space-between; min-height: var(--tl-control-min-height); }.child-edit-picker__value > text:last-child { font-size: 38rpx; color: var(--tl-text-secondary); }.child-edit-picker__value--placeholder { color: var(--tl-text-secondary); }.child-edit-field__error { display: block; margin-top: 12rpx; font-size: var(--tl-type-meta); line-height: 1.4; color: #b4513d; }
.child-edit-tags,.child-edit-custom-tags { display: flex; flex-wrap: wrap; gap: 14rpx; }.child-edit-custom-tags { margin-top: 14rpx; }.child-edit-tag { min-height: 68rpx; padding: 0 22rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: 999rpx; }.child-edit-tag--selected { color: #17673c; background: #e2f3e7; border-color: #1f7b47; }.child-edit-tag--add { color: #17673c; border-style: dashed; }.child-edit-custom-input { display: flex; gap: 16rpx; align-items: center; margin-top: 18rpx; }.child-edit-custom-input input { flex: 1; min-width: 0; min-height: 72rpx; padding: 0 20rpx; font-size: var(--tl-type-meta); background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); }.child-edit-custom-input button { flex: 0 0 auto; min-height: 72rpx; padding: 0 22rpx; font-size: var(--tl-type-meta); color: #17673c; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-control); }
.child-edit-consent { display: flex; gap: 16rpx; align-items: flex-start; padding: 30rpx 0; border-top: 1rpx solid var(--tl-divider); }.child-edit-consent__check { display: flex; flex: 0 0 44rpx; align-items: center; justify-content: center; width: 44rpx; min-width: 44rpx; height: 44rpx; min-height: 44rpx; padding: 0; color: #fff; border: 2rpx solid #789083; border-radius: 10rpx; }.child-edit-consent__check--selected { background: #1f7b47; border-color: #1f7b47; }.child-edit-consent__copy { flex: 1; padding: 0; font-size: var(--tl-type-meta); line-height: 1.55; color: var(--tl-text-main); text-align: left; background: transparent; }.child-edit-consent--confirmed { padding-left: 2rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }
.child-edit-privacy { margin-top: 10rpx; padding: 34rpx 0 10rpx; border-top: 1rpx solid var(--tl-divider); }.child-edit-privacy__title { display: block; font-size: var(--tl-type-body); font-weight: 600; }.child-edit-privacy__delete { min-height: 72rpx; padding: 0; margin-top: 18rpx; font-size: var(--tl-type-meta); color: #a94b36; background: transparent; }
.child-edit-actions { position: fixed; right: 0; left: 0; z-index: 60; padding: 16rpx var(--tl-page-padding) calc(16rpx + var(--tl-safe-bottom)); background: rgba(248, 239, 217, .96); border-top: 1rpx solid var(--tl-divider); box-sizing: border-box; }.child-edit-actions__inner { width: 100%; max-width: calc(var(--tl-content-max-width) - (var(--tl-page-padding) * 2)); margin: 0 auto; }.child-edit-actions__error { display: block; margin: 0 4rpx 12rpx; font-size: var(--tl-type-meta); color: #b4513d; }.child-edit-actions__save { width: 100%; min-height: 88rpx; font-size: var(--tl-type-primary-action); font-weight: var(--tl-weight-primary-action); color: #fff; background: #1f7b47; border-radius: var(--tl-radius-control); transition: opacity .16s ease; }.child-edit-actions__save[disabled] { opacity: .45; }
.child-edit-dialog { position: fixed; inset: 0; z-index: 80; display: flex; align-items: flex-end; }.child-edit-dialog__mask { position: absolute; inset: 0; background: rgba(49, 39, 27, .38); }.child-edit-dialog__panel { position: relative; width: 100%; max-width: var(--tl-content-max-width); padding: 32rpx var(--tl-page-padding) calc(32rpx + var(--tl-safe-bottom)); margin: 0 auto; background: var(--tl-surface); border-radius: var(--tl-radius-sheet) var(--tl-radius-sheet) 0 0; box-sizing: border-box; }.child-edit-dialog__title { display: block; font-size: var(--tl-type-section-title); font-weight: var(--tl-weight-section-title); }.child-edit-dialog__copy { display: block; margin: 14rpx 0 22rpx; font-size: var(--tl-type-meta); line-height: 1.5; color: var(--tl-text-secondary); }.child-edit-dialog__actions { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; margin-top: 22rpx; }.child-edit-dialog__actions button { min-height: 80rpx; font-size: var(--tl-type-body); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); }.child-edit-dialog__confirm { color: #fff; background: #a94b36; border-color: #a94b36 !important; }.child-edit-dialog__confirm[disabled] { opacity: .45; }
@media (min-width: 431px) { .child-edit-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(116px + var(--tl-safe-bottom)); }.child-edit-header { grid-template-columns: 44px 1fr 44px; min-height: 44px; margin-bottom: 13px; }.child-edit-header__back { min-width: 44px; min-height: 44px; font-size: 29px; }.child-edit-header__spacer { min-width: 44px; }.child-edit-section { padding: 16px 0; }.child-edit-avatar-grid { gap: 9px; }.child-edit-avatar { min-height: 88px; padding: 6px; }.child-edit-avatar image { width: 52px; height: 52px; }.child-edit-avatar text { margin-top: 3px; }.child-edit-input,.child-edit-picker { min-height: 44px; padding: 0 12px; }.child-edit-picker__value { min-height: 44px; }.child-edit-tags,.child-edit-custom-tags { gap: 7px; }.child-edit-tag { min-height: 34px; padding: 0 11px; }.child-edit-actions { padding: 8px 18px calc(8px + var(--tl-safe-bottom)); }.child-edit-actions__inner { max-width: 394px; }.child-edit-actions__save { min-height: 44px; }.child-edit-dialog__panel { padding: 16px 18px calc(16px + var(--tl-safe-bottom)); }.child-edit-dialog__actions button { min-height: 40px; } }
</style>
