<template>
  <view class="profile-page">
    <view class="profile-page__title-row">
      <text class="profile-page__title">我的</text>
      <view class="profile-page__spark" aria-hidden="true"></view>
    </view>

    <view class="profile-page__hero-art">
      <image src="../../assets/profile/profile-growth-watercolor.webp" mode="aspectFill" />
    </view>

    <view class="profile-page__user">
      <view class="profile-page__avatar">
        <view class="profile-page__avatar-portrait" aria-hidden="true"></view>
      </view>
      <view class="profile-page__user-copy">
        <view class="profile-page__name-row">
          <text class="profile-page__name">{{ displayUser.nickname }}</text>
        </view>
        <text class="profile-page__meta">{{ displayUser.meta }}</text>
        <text v-if="activeChild" class="profile-page__age-tag">{{ activeAgeGroup }}岁</text>
      </view>
    </view>

    <view class="profile-page__section">
      <view class="profile-page__section-title">
        <view class="profile-page__section-mark" aria-hidden="true"></view>
        <text>成长记录</text>
      </view>
      <view class="profile-page__record-list">
        <button class="profile-page__record" @click="openJourneyRecords">
          <view class="profile-page__record-thumb profile-page__record-thumb--record" aria-hidden="true"></view>
          <view class="profile-page__record-copy">
            <text class="profile-page__record-title">成长记录</text>
            <text class="profile-page__record-meta">查看探索中的任务、照片与笔记</text>
          </view>
          <view class="profile-page__arrow" aria-hidden="true"></view>
        </button>
      </view>
    </view>

    <view v-if="showChildCard" class="profile-page__child-card">
      <view class="profile-page__child-head">
        <text>孩子档案</text>
        <button @click="showChildCard = false">收起</button>
      </view>

      <view v-if="child.isLoading" class="profile-page__child-state">
        <text>正在加载孩子档案...</text>
      </view>
      <view v-else-if="child.error" class="profile-page__child-state">
        <text>孩子资料加载失败，请重试</text>
        <button @click="loadChildren">重试</button>
      </view>
      <view v-else-if="child.isLoaded && child.children.length === 0" class="profile-page__child-state">
        <text class="profile-page__child-empty-title">尚未添加孩子</text>
        <text class="profile-page__child-empty-desc">完善孩子档案后，就能记录专属成长旅程</text>
        <button @click="openChildForm">添加孩子档案</button>
      </view>
      <view v-else-if="activeChild">
        <view class="profile-page__child-context">
          <text class="profile-page__child-current-tag">当前孩子</text>
          <button v-if="canSwitchChild" class="profile-page__child-switch" @click="openChildSwitcher">切换孩子</button>
        </view>
        <text class="profile-page__child-name">{{ activeChild.name }} · {{ activeChild.age }}岁 · {{ activeChild.city || '未填写城市' }}</text>
        <view class="profile-page__interest-list">
          <text v-for="interest in activeChild.interests" :key="interest" class="profile-page__interest">{{ interest }}</text>
        </view>
        <button class="profile-page__child-edit" @click="openChildForm">编辑孩子档案</button>
      </view>
      <view v-else class="profile-page__child-state">
        <text>正在加载孩子资料...</text>
      </view>
    </view>

    <view class="profile-page__menu">
      <button v-for="item in menuItems" :key="item.key" class="profile-page__menu-item" @click="handleMenu(item.key)">
        <view class="profile-page__menu-icon" :class="`profile-page__menu-icon--${item.icon}`" aria-hidden="true"></view>
        <text>{{ item.label }}</text>
        <view class="profile-page__arrow" aria-hidden="true"></view>
      </button>
    </view>

    <view v-if="showChildForm" class="profile-page__sheet">
      <view class="profile-page__sheet-mask" @click="closeChildForm"></view>
      <view class="profile-page__sheet-panel profile-page__sheet-panel--child">
        <view class="profile-page__sheet-head">
          <text>{{ activeChild ? '编辑孩子档案' : '完善孩子档案' }}</text>
          <button @click="closeChildForm">关闭</button>
        </view>

        <view class="profile-page__form-field">
          <text>姓名</text>
          <input v-model="childForm.name" placeholder="请输入孩子姓名" />
        </view>
        <view class="profile-page__form-field">
          <text>年龄</text>
          <input v-model="childForm.age" type="number" placeholder="3-12" />
          <text class="profile-page__form-hint">{{ formAgeGroup }}岁</text>
        </view>
        <view class="profile-page__form-field">
          <text>城市</text>
          <input v-model="childForm.city" placeholder="可不填" />
        </view>
        <view class="profile-page__form-field">
          <text>兴趣</text>
          <view class="profile-page__interest-list profile-page__interest-list--form">
            <button
              v-for="interest in interestOptions"
              :key="interest"
              class="profile-page__interest"
              :class="{ 'profile-page__interest--active': childForm.interests.includes(interest) }"
              @click="toggleChildInterest(interest)"
            >
              {{ interest }}
            </button>
          </view>
        </view>

        <button class="profile-page__form-submit" :disabled="isSavingChild" @click="saveChildProfile">
          {{ isSavingChild ? '保存中' : '保存档案' }}
        </button>
      </view>
    </view>

    <view v-if="showChildSwitcher" class="profile-page__sheet">
      <view class="profile-page__sheet-mask" @click="closeChildSwitcher"></view>
      <view class="profile-page__sheet-panel profile-page__sheet-panel--switcher">
        <view class="profile-page__sheet-head">
          <text>切换孩子</text>
          <button @click="closeChildSwitcher">关闭</button>
        </view>
        <view class="profile-page__child-option-list">
          <button
            v-for="candidate in child.children"
            :key="candidate.id"
            class="profile-page__child-option"
            :class="{ 'profile-page__child-option--active': isActiveChild(candidate) }"
            @click="selectActiveChild(candidate)"
          >
            <view class="profile-page__child-option-copy">
              <text class="profile-page__child-option-name">{{ candidate.name }}</text>
              <text class="profile-page__child-option-meta">{{ candidate.age }}岁 · {{ candidate.city || '未填写城市' }}</text>
            </view>
            <text v-if="isActiveChild(candidate)" class="profile-page__child-option-current">当前孩子</text>
          </button>
        </view>
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

export default {
  components: {
    AppTabbar,
  },
  data() {
    return {
      showChildCard: true,
      showChildForm: false,
      showChildSwitcher: false,
      isSavingChild: false,
      childForm: {
        name: '',
        age: '7',
        city: '',
        interests: ['历史故事', '古建筑', '观察探索'],
      },
      interestOptions: ['历史故事', '古建筑', '观察探索'],
    }
  },
  computed: {
    child() {
      return useChildStore()
    },
    user() {
      return useUserStore()
    },
    activeChild() {
      return this.child.activeChild
    },
    canSwitchChild() {
      return Boolean(this.activeChild) && this.child.children.length > 1
    },
    activeAgeGroup() {
      if (this.activeChild?.ageGroup) {
        return this.activeChild.ageGroup
      }
      return this.activeChild?.age >= 3 && this.activeChild.age <= 6 ? '3-6' : '7-12'
    },
    displayUser() {
      if (this.child.isLoading) {
        return {
          nickname: '孩子档案加载中',
          meta: '正在同步真实孩子资料',
        }
      }

      if (this.child.error) {
        return {
          nickname: '孩子资料加载失败',
          meta: '请重试后再查看孩子档案',
        }
      }

      if (this.child.isLoaded && this.child.children.length === 0) {
        return {
          nickname: '尚未添加孩子',
          meta: '完善后记录专属成长旅程',
        }
      }

      if (this.activeChild) {
        return {
          nickname: this.activeChild.name,
          meta: `${this.activeChild.age}岁 · ${this.activeChild.city || '未填写城市'}`,
        }
      }

      return {
        nickname: '孩子资料加载中',
        meta: '正在同步真实孩子资料',
      }
    },
    formAgeGroup() {
      const age = Number(this.childForm.age)
      if (age >= 3 && age <= 6) {
        return '3-6'
      }
      return '7-12'
    },
    menuItems() {
      return [
        { key: 'child', label: '孩子档案', icon: 'child' },
        { key: 'logout', label: '退出登录', icon: 'logout' },
      ]
    },
  },
  async onShow() {
    await this.user.restoreSession()
    if (!this.user.isLoggedIn) {
      uni.reLaunch({
        url: '/pages/login/index',
      })
      return
    }
    await this.loadChildren()
  },
  methods: {
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    mapChildError(error) {
      const messages = {
        NETWORK_ERROR: '无法加载孩子档案，请重试',
        VALIDATION_ERROR: '请检查孩子档案信息',
        UNAUTHORIZED: '登录状态已失效，请重新登录',
        INVALID_TOKEN: '登录状态已失效，请重新登录',
        TOKEN_EXPIRED: '登录状态已失效，请重新登录',
      }
      return messages[error?.code] || error?.message || '操作失败，请稍后再试'
    },
    async loadChildren() {
      try {
        await this.child.fetchChildren(this.user.userInfo.id)
      } catch (error) {
        if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    openJourneyRecords() {
      uni.navigateTo({
        url: '/pages/record/index',
      })
    },
    openChildForm() {
      const current = this.activeChild
      this.childForm = {
        name: current?.name || '',
        age: String(current?.age || 7),
        city: current?.city || '',
        interests: current?.interests?.length ? [...current.interests] : ['历史故事', '古建筑', '观察探索'],
      }
      this.showChildForm = true
    },
    openChildSwitcher() {
      if (this.canSwitchChild) {
        this.showChildSwitcher = true
      }
    },
    closeChildSwitcher() {
      this.showChildSwitcher = false
    },
    isActiveChild(candidate) {
      return String(candidate?.id) === String(this.activeChild?.id)
    },
    selectActiveChild(candidate) {
      if (this.child.setActiveChild(candidate?.id)) {
        this.showChildSwitcher = false
        return
      }
      this.showToast('切换孩子失败，请稍后重试')
    },
    closeChildForm() {
      if (!this.isSavingChild) {
        this.showChildForm = false
      }
    },
    toggleChildInterest(interest) {
      if (this.childForm.interests.includes(interest)) {
        if (this.childForm.interests.length === 1) {
          return
        }
        this.childForm.interests = this.childForm.interests.filter((item) => item !== interest)
        return
      }
      this.childForm.interests = [...this.childForm.interests, interest]
    },
    validateChildForm() {
      const name = this.childForm.name.trim()
      const age = Number(this.childForm.age)
      if (!name) {
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
      if (this.isSavingChild || !this.validateChildForm()) {
        return
      }

      const payload = {
        name: this.childForm.name.trim(),
        age: Number(this.childForm.age),
        city: this.childForm.city.trim(),
        interests: [...this.childForm.interests],
      }

      this.isSavingChild = true
      try {
        if (this.activeChild) {
          await this.child.updateChild(this.activeChild.id, payload)
        } else {
          await this.child.createChild(payload)
        }
        this.showChildForm = false
        this.showToast('孩子档案已保存')
      } catch (error) {
        this.showToast(this.mapChildError(error))
      } finally {
        this.isSavingChild = false
      }
    },
    handleMenu(key) {
      if (key === 'child') {
        this.showChildCard = true
        this.openChildForm()
        return
      }

      if (key === 'logout') {
        endUserSession()
      }
    },
  },
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 40rpx 42rpx calc(170rpx + env(safe-area-inset-bottom));
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 18% 8%, rgba(255, 240, 189, 0.72), transparent 24%),
    linear-gradient(180deg, #fff4da 0%, #f8efd9 100%);
}

.profile-page__title-row,
.profile-page__user,
.profile-page__name-row,
.profile-page__child-head,
.profile-page__sheet-head,
.profile-page__setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profile-page__title-row {
  justify-content: flex-start;
  gap: 16rpx;
  margin-top: 22rpx;
}

.profile-page__title {
  font-size: 66rpx;
  font-weight: 900;
}

.profile-page__spark {
  position: relative;
  width: 22rpx;
  height: 22rpx;
  color: #f4aa23;
  transform: rotate(45deg);
}

.profile-page__spark::after,
.profile-page__section-mark::after {
  position: absolute;
  inset: 0;
  content: '';
  background: currentColor;
  border-radius: 5rpx;
}

.profile-page__user {
  justify-content: flex-start;
  gap: 26rpx;
  margin-top: 26rpx;
}

.profile-page__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 142rpx;
  height: 142rpx;
  color: #d94b12;
  background: #ffd782;
  border: 8rpx solid #fffaf0;
  border-radius: 50%;
  box-shadow: 0 12rpx 24rpx rgba(97, 63, 28, 0.12);
}

.profile-page__avatar-portrait {
  position: relative;
  width: 58rpx;
  height: 68rpx;
  border: 4rpx solid currentColor;
  border-radius: 34rpx 34rpx 20rpx 20rpx;
}

.profile-page__avatar-portrait::before,
.profile-page__avatar-portrait::after {
  position: absolute;
  right: 0;
  left: 0;
  margin: auto;
  content: '';
}

.profile-page__avatar-portrait::before {
  top: 10rpx;
  width: 18rpx;
  height: 18rpx;
  border: 4rpx solid currentColor;
  border-radius: 50%;
}

.profile-page__avatar-portrait::after {
  bottom: 9rpx;
  width: 32rpx;
  height: 16rpx;
  border: 4rpx solid currentColor;
  border-bottom: 0;
  border-radius: 22rpx 22rpx 0 0;
}

.profile-page__user-copy {
  flex: 1;
  min-width: 0;
}

.profile-page__name-row {
  justify-content: flex-start;
  gap: 12rpx;
}

.profile-page__name {
  font-size: 40rpx;
  font-weight: 900;
}

.profile-page__edit {
  position: relative;
  width: 24rpx;
  height: 24rpx;
  color: #d94b12;
  transform: rotate(-38deg);
}

.profile-page__edit::before {
  position: absolute;
  top: 2rpx;
  left: 9rpx;
  width: 6rpx;
  height: 20rpx;
  content: '';
  background: currentColor;
  border-radius: 999rpx;
}

.profile-page__meta {
  display: block;
  margin-top: 12rpx;
  font-size: 28rpx;
  color: #5e3c22;
}

.profile-page__age-tag {
  display: inline-flex;
  padding: 8rpx 18rpx;
  margin-top: 14rpx;
  font-size: 24rpx;
  color: #f26a21;
  background: #fff0bd;
  border: 2rpx solid rgba(242, 106, 33, 0.28);
  border-radius: 999rpx;
}

.profile-page__tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 4rpx;
  margin-top: 26rpx;
  background: #f7dfb4;
  border-radius: 999rpx;
}

.profile-page__tabs button {
  height: 64rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #5e3c22;
  border-radius: 999rpx;
}

.profile-page__tab--active {
  color: #f26a21;
  background: #fffaf0;
}

.profile-page__section {
  margin-top: 28rpx;
}

.profile-page__section-title {
  display: flex;
  gap: 12rpx;
  align-items: center;
  margin-bottom: 16rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.profile-page__section-mark {
  position: relative;
  width: 18rpx;
  height: 18rpx;
  color: #f4aa23;
  transform: rotate(45deg);
}

.profile-page__record,
.profile-page__favorite {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 104rpx;
  padding: 12rpx 18rpx;
  margin-bottom: 14rpx;
  text-align: left;
  background: rgba(255, 250, 240, 0.72);
  border: 2rpx solid rgba(190, 142, 78, 0.2);
  border-radius: 22rpx;
}

.profile-page__record-thumb {
  position: relative;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 160rpx;
  height: 74rpx;
  margin-right: 22rpx;
  color: #d94b12;
  background: #dfeff8;
  border-radius: 16rpx;
}

.profile-page__record-thumb::before,
.profile-page__record-thumb::after,
.profile-page__menu-icon::before,
.profile-page__menu-icon::after,
.profile-page__arrow::after {
  position: absolute;
  box-sizing: border-box;
  content: '';
}

.profile-page__record-thumb--record::before {
  width: 32rpx;
  height: 38rpx;
  border: 3rpx solid currentColor;
  border-radius: 6rpx;
}

.profile-page__record-thumb--record::after {
  width: 17rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
  box-shadow: 0 9rpx 0 currentColor, 0 18rpx 0 currentColor;
}

.profile-page__record-copy,
.profile-page__favorite view {
  flex: 1;
  min-width: 0;
}

.profile-page__record-title,
.profile-page__favorite-title {
  display: block;
  overflow: hidden;
  font-size: 29rpx;
  font-weight: 900;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-page__record-meta,
.profile-page__favorite-desc {
  display: block;
  margin-top: 8rpx;
  overflow: hidden;
  font-size: 23rpx;
  color: #6f5238;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-page__arrow {
  position: relative;
  width: 22rpx;
  height: 28rpx;
  flex-shrink: 0;
  margin-left: 12rpx;
  color: #8a6d54;
}

.profile-page__arrow::after {
  top: 7rpx;
  left: 2rpx;
  width: 11rpx;
  height: 11rpx;
  border-top: 3rpx solid currentColor;
  border-right: 3rpx solid currentColor;
  transform: rotate(45deg);
}

.profile-page__favorite-type {
  flex-shrink: 0;
  padding: 10rpx 14rpx;
  margin-right: 16rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #d94b12;
  background: #fff0bd;
  border-radius: 14rpx;
}

.profile-page__child-card,
.profile-page__menu {
  padding: 24rpx;
  margin-top: 28rpx;
  background: rgba(255, 250, 240, 0.72);
  border: 2rpx solid rgba(190, 142, 78, 0.22);
  border-radius: 24rpx;
}

.profile-page__child-head {
  font-size: 30rpx;
  font-weight: 900;
}

.profile-page__child-head button {
  font-size: 24rpx;
  color: #8a6d54;
}

.profile-page__child-name {
  display: block;
  margin-top: 16rpx;
  font-size: 28rpx;
  font-weight: 800;
}

.profile-page__child-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 16rpx;
}

.profile-page__child-current-tag,
.profile-page__child-option-current {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6rpx 14rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #f26a21;
  background: #fff0bd;
  border: 2rpx solid rgba(242, 106, 33, 0.22);
  border-radius: 999rpx;
}

.profile-page__child-switch {
  padding: 8rpx 4rpx;
  font-size: 24rpx;
  font-weight: 900;
  color: #55753c;
}

.profile-page__child-state {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  align-items: flex-start;
  margin-top: 16rpx;
  font-size: 27rpx;
  line-height: 1.45;
  color: #6f5238;
}

.profile-page__child-state button,
.profile-page__child-edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 62rpx;
  padding: 0 22rpx;
  margin-top: 4rpx;
  font-size: 25rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.profile-page__child-empty-title {
  font-size: 30rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.profile-page__child-empty-desc {
  color: #6f5238;
}

.profile-page__interest-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 16rpx;
}

.profile-page__interest {
  padding: 10rpx 16rpx;
  font-size: 24rpx;
  color: #55753c;
  background: #dceecb;
  border-radius: 999rpx;
}

.profile-page__interest--active {
  color: #fff;
  background: #f26a21;
}

.profile-page__menu {
  padding: 0;
  overflow: hidden;
}

.profile-page__menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  height: 88rpx;
  padding: 0 24rpx;
  font-size: 29rpx;
  color: #4a2f1b;
  text-align: left;
}

.profile-page__menu-item + .profile-page__menu-item {
  border-top: 2rpx solid rgba(190, 142, 78, 0.18);
}

.profile-page__menu-icon {
  position: relative;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52rpx;
  height: 52rpx;
  margin-right: 18rpx;
  color: #f26a21;
  background: #fff0bd;
  border-radius: 16rpx;
}

.profile-page__menu-icon--child::before,
.profile-page__menu-icon--notice::before,
.profile-page__menu-icon--settings::before,
.profile-page__menu-icon--help::before {
  top: 11rpx;
  left: 14rpx;
  width: 20rpx;
  height: 20rpx;
  border: 3rpx solid currentColor;
  border-radius: 50%;
}

.profile-page__menu-icon--child::after {
  bottom: 8rpx;
  left: 10rpx;
  width: 28rpx;
  height: 14rpx;
  border: 3rpx solid currentColor;
  border-radius: 18rpx 18rpx 7rpx 7rpx;
}

.profile-page__menu-icon--favorites::before {
  top: 13rpx;
  left: 13rpx;
  width: 24rpx;
  height: 21rpx;
  border: 3rpx solid currentColor;
  border-radius: 14rpx 14rpx 8rpx 8rpx;
  transform: rotate(45deg);
}

.profile-page__menu-icon--notice::after {
  top: 31rpx;
  left: 18rpx;
  width: 16rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.profile-page__menu-icon--settings::after {
  top: 21rpx;
  left: 7rpx;
  width: 38rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
  transform: rotate(45deg);
}

.profile-page__menu-icon--help::after {
  top: 17rpx;
  left: 24rpx;
  width: 4rpx;
  height: 12rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.profile-page__menu-icon--logout::before {
  top: 12rpx;
  left: 9rpx;
  width: 25rpx;
  height: 28rpx;
  border: 3rpx solid currentColor;
  border-radius: 6rpx;
}

.profile-page__menu-icon--logout::after {
  top: 22rpx;
  right: 7rpx;
  width: 22rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.profile-page__menu-item .profile-page__arrow {
  margin-left: auto;
}

.profile-page__sheet {
  position: fixed;
  inset: 0;
  z-index: 88;
}

.profile-page__sheet-mask {
  position: absolute;
  inset: 0;
  background: rgba(74, 47, 27, 0.24);
}

.profile-page__sheet-panel {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 30rpx 34rpx calc(30rpx + env(safe-area-inset-bottom));
  background: #fff7e8;
  border-radius: 32rpx 32rpx 0 0;
}

.profile-page__sheet-panel--child {
  max-height: 78vh;
  overflow-y: auto;
}

.profile-page__sheet-panel--switcher {
  max-height: 62vh;
  overflow-y: auto;
}

.profile-page__sheet-head {
  margin-bottom: 22rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.profile-page__sheet-head button {
  font-size: 24rpx;
  color: #8a6d54;
}

.profile-page__setting-row {
  min-height: 70rpx;
  font-size: 28rpx;
  border-top: 2rpx solid rgba(190, 142, 78, 0.16);
}

.profile-page__child-option-list {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.profile-page__child-option {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 104rpx;
  padding: 20rpx 22rpx;
  color: #4a2f1b;
  text-align: left;
  background: #fffaf0;
  border: 2rpx solid rgba(190, 142, 78, 0.24);
  border-radius: 22rpx;
}

.profile-page__child-option--active {
  background: #fff0bd;
  border-color: rgba(242, 106, 33, 0.52);
}

.profile-page__child-option-copy {
  flex: 1;
  min-width: 0;
}

.profile-page__child-option-name,
.profile-page__child-option-meta {
  display: block;
}

.profile-page__child-option-name {
  font-size: 30rpx;
  font-weight: 900;
}

.profile-page__child-option-meta {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6f5238;
}

.profile-page__form-field {
  margin-bottom: 20rpx;
}

.profile-page__form-field > text:first-child {
  display: block;
  margin-bottom: 10rpx;
  font-size: 25rpx;
  font-weight: 800;
  color: #5e3c22;
}

.profile-page__form-field input {
  width: 100%;
  height: 72rpx;
  padding: 0 22rpx;
  font-size: 28rpx;
  color: #4a2f1b;
  background: #fffaf0;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 20rpx;
}

.profile-page__form-hint {
  display: block;
  margin-top: 8rpx;
  font-size: 23rpx;
  color: #8a6d54;
}

.profile-page__interest-list--form .profile-page__interest {
  border: 2rpx solid rgba(190, 142, 78, 0.26);
}

.profile-page__form-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 82rpx;
  margin-top: 8rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 26rpx;
  box-shadow: 0 12rpx 18rpx rgba(217, 75, 18, 0.2);
}

.profile-page__form-submit[disabled] {
  color: #8a6d54;
  background: #eadcc8;
  box-shadow: none;
}
.profile-page {
  width: 100%;
  max-width: var(--tl-content-max-width, 430px);
  padding-top: calc(30rpx + env(safe-area-inset-top));
  margin: 0 auto;
  background:
    radial-gradient(circle at 88% 18%, rgba(207, 231, 245, 0.84), transparent 20%),
    linear-gradient(180deg, #fff8e8 0%, #f8efd9 100%);
}

.profile-page__title-row {
  position: relative;
  z-index: 1;
  margin-top: 0;
}

.profile-page__title {
  font-size: 52rpx;
}

.profile-page__hero-art {
  height: 214rpx;
  margin: 12rpx -14rpx -74rpx;
  overflow: hidden;
  pointer-events: none;
  border-radius: 28rpx 28rpx 46rpx 46rpx;
  box-shadow: inset 0 -34rpx 42rpx rgba(255, 248, 232, 0.86);
}

.profile-page__hero-art image {
  width: 100%;
  height: 100%;
  opacity: 0.84;
}

.profile-page__user {
  position: relative;
  z-index: 1;
  padding: 22rpx;
  margin-top: 0;
  background: rgba(255, 250, 240, 0.92);
  border: 2rpx solid rgba(190, 142, 78, 0.24);
  border-radius: 28rpx;
  box-shadow: 0 12rpx 26rpx rgba(97, 63, 28, 0.08);
}

.profile-page__avatar {
  background: linear-gradient(135deg, #ffd782, #f5ad58);
  box-shadow: 0 0 0 5rpx rgba(255, 250, 240, 0.78), 0 12rpx 24rpx rgba(97, 63, 28, 0.12);
}

.profile-page__tabs {
  margin-top: 30rpx;
  box-shadow: inset 0 0 0 2rpx rgba(190, 142, 78, 0.12);
}

.profile-page__record,
.profile-page__favorite,
.profile-page__child-card,
.profile-page__menu {
  background-color: rgba(255, 250, 240, 0.9);
  box-shadow: 0 10rpx 20rpx rgba(97, 63, 28, 0.05);
}

.profile-page__record-thumb {
  border: 2rpx solid rgba(115, 172, 211, 0.28);
  transform: rotate(-3deg);
}

.profile-page__child-card {
  position: relative;
  overflow: hidden;
}

.profile-page__child-card::after {
  position: absolute;
  right: -8rpx;
  bottom: -12rpx;
  width: 76rpx;
  height: 42rpx;
  content: '';
  pointer-events: none;
  border: 5rpx solid rgba(123, 154, 80, 0.2);
  border-color: rgba(123, 154, 80, 0.2) transparent transparent rgba(123, 154, 80, 0.2);
  border-radius: 50%;
  transform: rotate(14deg);
}

.profile-page__sheet-panel {
  background: #fff8ea;
  box-shadow: 0 -16rpx 34rpx rgba(74, 47, 27, 0.12);
}

@media (max-width: 370px) {
  .profile-page {
    padding-right: 28rpx;
    padding-left: 28rpx;
  }

  .profile-page__hero-art {
    height: 190rpx;
  }

  .profile-page__user {
    gap: 18rpx;
    padding: 18rpx;
  }

  .profile-page__avatar {
    width: 118rpx;
    height: 118rpx;
  }
}
</style>
