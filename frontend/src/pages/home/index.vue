<template>
  <view class="home-page">
    <view class="home-page__paper">
      <view class="home-header">
        <view class="home-header__brand">
          <text class="home-header__title">童旅记</text>
          <text class="home-header__subtitle">在旅行中学习，在故事里成长</text>
        </view>

        <view class="home-header__tools">
          <view class="home-header__city" @click="noop">
            <text class="home-header__pin">定位</text>
            <text>北京</text>
            <text class="home-header__arrow">⌄</text>
          </view>
          <view class="home-header__notice" @click="noop">
            <text>铃</text>
            <view class="home-header__dot"></view>
          </view>
        </view>
      </view>

      <view class="home-search-row">
        <view class="home-search">
          <text class="home-search__icon">⌕</text>
          <input v-model="searchKeyword" placeholder="输入这次要去的地方" />
          <text class="home-search__send">›</text>
        </view>

        <view class="home-age">
          <view
            v-for="option in ageOptions"
            :key="option.value"
            class="home-age__item"
            :class="{ 'home-age__item--active': child.ageGroup === option.value }"
            @click="selectAge(option.value)"
          >
            {{ option.label }}
          </view>
        </view>
      </view>

      <view class="home-book-card">
        <view class="home-book-card__left">
          <text class="home-book-card__title">
            <text class="home-book-card__title-line">故宫亲子</text>
            <text class="home-book-card__title-line">探索</text>
          </text>
          <view class="home-book-card__underline"></view>
          <text class="home-book-card__desc">认识古代皇宫，边看边学</text>

          <view class="home-book-card__tags">
            <view class="home-book-card__tag home-book-card__tag--orange">
              <text class="home-book-card__tag-mark">包</text>
              <text>7-12岁</text>
            </view>
            <view class="home-book-card__tag home-book-card__tag--blue">
              <text class="home-book-card__tag-mark">时</text>
              <text>约3小时</text>
            </view>
          </view>

          <view class="home-book-card__button" @click="openPlanSheet">
            <text>创建探索计划</text>
            <text class="home-book-card__button-arrow">›</text>
          </view>
        </view>

        <view class="home-book-card__right">
          <view class="home-scene">
            <view class="home-scene__sky"></view>
            <view class="home-scene__palace">
              <view class="home-scene__roof"></view>
              <view class="home-scene__hall"></view>
              <view class="home-scene__rail"></view>
            </view>
            <view class="home-scene__walkway"></view>
            <view class="home-scene__ribbon">故宫</view>
          </view>
        </view>
      </view>

      <view class="home-entry-grid">
        <view
          v-for="entry in entries"
          :key="entry.title"
          class="home-entry"
          :class="`home-entry--${entry.theme}`"
          @click="goEntry(entry)"
        >
          <text class="home-entry__title">{{ entry.title }}</text>
          <text class="home-entry__desc">{{ entry.desc }}</text>
          <view class="home-entry__art">
            <view class="home-entry__paper"></view>
            <view class="home-entry__mark"></view>
          </view>
        </view>
      </view>

      <view class="home-learn">
        <view class="home-section-title">
          <text class="home-section-title__star">星</text>
          <text>这次孩子能学什么</text>
        </view>

        <view class="home-learn__grid">
          <view
            v-for="item in learningItems"
            :key="item.title"
            class="home-learn-card"
            :class="`home-learn-card--${item.theme}`"
          >
            <text class="home-learn-card__title">{{ item.title }}</text>
            <text class="home-learn-card__desc">{{ item.desc }}</text>
            <view class="home-learn-card__visual">
              <view class="home-learn-card__shape"></view>
              <view class="home-learn-card__tape"></view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view v-if="planSheetOpen" class="plan-sheet">
      <view class="plan-sheet__mask" @click="closePlanSheet"></view>
      <view class="plan-sheet__panel">
        <view class="plan-sheet__handle"></view>
        <view class="plan-sheet__header">
          <view>
            <text class="plan-sheet__title">创建探索计划</text>
            <text class="plan-sheet__subtitle">先用 Mock 生成一份故宫探索计划</text>
          </view>
          <view class="plan-sheet__close" @click="closePlanSheet">关闭</view>
        </view>

        <view class="plan-sheet__field">
          <text class="plan-sheet__label">目的地</text>
          <input v-model="planForm.destination" />
        </view>

        <view class="plan-sheet__field">
          <text class="plan-sheet__label">计划标题（选填）</text>
          <input v-model="planForm.title" maxlength="120" placeholder="给这次探索起个名字" />
        </view>

        <view class="plan-sheet__field">
          <text class="plan-sheet__label">孩子年龄</text>
          <view class="plan-sheet__age-list">
            <view
              v-for="option in ageOptions"
              :key="option.value"
              class="plan-sheet__age"
              :class="{ 'plan-sheet__age--active': planForm.ageGroup === option.value }"
              @click="planForm.ageGroup = option.value"
            >
              {{ option.label }}
            </view>
          </view>
        </view>

        <view class="plan-sheet__field">
          <text class="plan-sheet__label">预计时间</text>
          <input v-model="planForm.duration" />
        </view>

        <view class="plan-sheet__field">
          <text class="plan-sheet__label">兴趣主题</text>
          <view class="plan-sheet__interests">
            <view
              v-for="interest in interestOptions"
              :key="interest"
              class="plan-sheet__interest"
              :class="{ 'plan-sheet__interest--active': planForm.interests.includes(interest) }"
              @click="toggleInterest(interest)"
            >
              {{ interest }}
            </view>
          </view>
        </view>

        <view class="plan-sheet__submit" @click="submitPlan">{{ isCreatingPlan ? '生成中' : '生成探索计划' }}</view>
      </view>
    </view>

    <AppTabbar active="home" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useChildStore } from '../../stores/child'
import { usePlanStore } from '../../stores/plan'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: {
    AppTabbar,
  },
  data() {
    return {
      searchKeyword: '',
      planSheetOpen: false,
      isCreatingPlan: false,
      ageOptions: [
        { value: '3-6', label: '3-6岁' },
        { value: '7-12', label: '7-12岁' },
      ],
      interestOptions: ['古代生活', '建筑礼仪', '观察表达'],
      planForm: {
        title: '',
        destination: '故宫博物院',
        ageGroup: '7-12',
        duration: '3小时',
        interests: ['古代生活', '建筑礼仪', '观察表达'],
      },
      entries: [
        {
          title: '探索计划',
          desc: '规划行程与学习',
          theme: 'green',
          path: '/pages/plan/index',
          method: 'reLaunch',
        },
        {
          title: '讲解卡',
          desc: '家长轻松讲',
          theme: 'yellow',
          path: '/pages/guide/index',
          method: 'navigateTo',
        },
        {
          title: '观察任务',
          desc: '边看边完成',
          theme: 'blue',
          path: '/pages/tasks/index',
          method: 'reLaunch',
        },
      ],
      learningItems: [
        {
          title: '古代生活',
          desc: '了解皇宫里的衣食住行',
          theme: 'orange',
        },
        {
          title: '建筑礼仪',
          desc: '发现古建筑的智慧与礼仪',
          theme: 'yellow',
        },
        {
          title: '观察表达',
          desc: '学会观察，勇敢表达',
          theme: 'blue',
        },
      ],
    }
  },
  computed: {
    child() {
      return useChildStore()
    },
    plan() {
      return usePlanStore()
    },
    user() {
      return useUserStore()
    },
  },
  onShow() {
    this.planForm.ageGroup = this.child.ageGroup
  },
  methods: {
    noop() {},
    formatAgeGroup(ageGroup) {
      const option = this.ageOptions.find((item) => item.value === ageGroup)
      return option ? option.label : ageGroup
    },
    selectAge(ageGroup) {
      this.child.setAgeGroup(ageGroup)
      this.planForm.ageGroup = ageGroup
    },
    openPlanSheet() {
      this.planForm = {
        title: '',
        destination: this.searchKeyword.trim() || '故宫博物院',
        ageGroup: this.child.ageGroup,
        duration: '3小时',
        interests: ['古代生活', '建筑礼仪', '观察表达'],
      }
      this.planSheetOpen = true
    },
    closePlanSheet() {
      this.planSheetOpen = false
    },
    toggleInterest(interest) {
      if (this.planForm.interests.includes(interest)) {
        if (this.planForm.interests.length === 1) {
          return
        }
        this.planForm.interests = this.planForm.interests.filter((item) => item !== interest)
        return
      }
      this.planForm.interests = [...this.planForm.interests, interest]
    },
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    planErrorMessage(error) {
      const messages = {
        NETWORK_ERROR: '无法连接服务器，请稍后重试',
        UNAUTHORIZED: '登录状态已失效，请重新登录',
        TOKEN_EXPIRED: '登录状态已失效，请重新登录',
        INVALID_TOKEN: '登录状态已失效，请重新登录',
        CHILD_REQUIRED: '请先完善孩子档案',
        CHILD_NOT_FOUND: '请先完善孩子档案',
        VALIDATION_ERROR: '请检查探索计划信息',
      }
      return messages[error?.code] || error?.message || '创建失败，请稍后重试'
    },
    async handleAuthExpired() {
      await endUserSession()
    },
    async submitPlan() {
      if (this.isCreatingPlan) {
        return
      }

      this.isCreatingPlan = true
      this.child.setAgeGroup(this.planForm.ageGroup)

      try {
        if (!this.user.isAuthReady || this.user.isRestoring) {
          await this.user.restoreSession()
        }

        if (!this.user.isLoggedIn) {
          this.showToast('登录后才能创建探索计划')
          uni.reLaunch({
            url: '/pages/login/index',
          })
          return
        }

        await this.child.fetchChildren(this.user.userInfo.id)
        if (!this.child.hasRemoteChild) {
          this.showToast('请先完善孩子档案')
          uni.reLaunch({
            url: '/pages/profile/index',
          })
          return
        }

        if (this.planForm.ageGroup !== this.child.currentChild.ageGroup) {
          this.showToast(`当前孩子年龄组为 ${this.child.currentChild.ageGroup} 岁，请调整年龄选择或修改孩子档案`)
          return
        }

        const normalizedTitle = this.planForm.title.trim()
        const payload = {
          destination: this.planForm.destination.trim() || '故宫博物院',
          duration: this.planForm.duration.trim() || '3小时',
          interests: [...this.planForm.interests],
          childId: this.child.currentChild.id,
          ageGroup: this.child.currentChild.ageGroup,
        }
        if (normalizedTitle) {
          payload.title = normalizedTitle
        }
        const createdPlan = await this.plan.createPlan(
          payload,
          this.user.userInfo.id,
        )
        this.planSheetOpen = false

        uni.reLaunch({
          url: '/pages/plan/index',
        })
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(this.planErrorMessage(error))
      } finally {
        this.isCreatingPlan = false
      }
    },
    goEntry(entry) {
      uni[entry.method]({
        url: entry.path,
      })
    },
  },
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 8%, rgba(255, 238, 181, 0.6) 0, rgba(255, 238, 181, 0) 110rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.home-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(32rpx + env(safe-area-inset-top)) 34rpx calc(220rpx + env(safe-area-inset-bottom));
}

.home-header {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 34rpx;
}

.home-header__brand {
  position: relative;
  flex: 1;
  min-width: 0;
}

.home-header__title {
  display: block;
  padding-top: 20rpx;
  font-size: 72rpx;
  font-weight: 900;
  line-height: 1;
  color: #4a2f1b;
  letter-spacing: 0;
}

.home-header__subtitle {
  display: block;
  margin-top: 20rpx;
  font-size: 29rpx;
  line-height: 1.35;
  color: #5e3c22;
}

.home-header__tools {
  display: flex;
  gap: 18rpx;
  align-items: center;
  padding-top: 38rpx;
}

.home-header__city {
  display: flex;
  gap: 8rpx;
  align-items: center;
  justify-content: center;
  height: 60rpx;
  padding: 0 6rpx;
  font-size: 29rpx;
  font-weight: 700;
  color: #4a2f1b;
}

.home-header__pin {
  font-size: 20rpx;
  color: #7f4a20;
}

.home-header__arrow {
  font-size: 28rpx;
}

.home-header__notice {
  position: relative;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 58rpx;
  height: 58rpx;
  font-size: 24rpx;
  font-weight: 800;
  color: #4a2f1b;
  border: 3rpx solid #4a2f1b;
  border-radius: 28rpx 28rpx 22rpx 22rpx;
}

.home-header__dot {
  position: absolute;
  top: -4rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.home-search-row {
  display: flex;
  gap: 20rpx;
  align-items: center;
  margin-bottom: 28rpx;
}

.home-search {
  display: flex;
  flex: 1;
  align-items: center;
  min-width: 0;
  height: 86rpx;
  padding: 0 22rpx;
  background: rgba(255, 250, 240, 0.92);
  border: 4rpx solid rgba(220, 163, 75, 0.72);
  border-radius: 28rpx;
  box-shadow: 0 8rpx 18rpx rgba(97, 63, 28, 0.06);
}

.home-search__icon {
  margin-right: 14rpx;
  font-size: 48rpx;
  line-height: 1;
  color: #6e4b34;
}

.home-search input {
  flex: 1;
  min-width: 0;
  height: 78rpx;
  font-size: 29rpx;
  color: #4a2f1b;
}

.home-search__send {
  font-size: 56rpx;
  color: #e7a83d;
  transform: rotate(-28deg);
}

.home-age {
  display: flex;
  flex-shrink: 0;
  gap: 14rpx;
  align-items: center;
}

.home-age__item {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  min-width: 116rpx;
  height: 64rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #6b482d;
  background: #f6dfaf;
  border: 2rpx solid rgba(222, 172, 87, 0.3);
  border-radius: 24rpx;
}

.home-age__item--active {
  color: #fffaf0;
  background: #f26a21;
  border-color: #e65b17;
  box-shadow: 0 8rpx 14rpx rgba(242, 106, 33, 0.22);
}

.home-book-card {
  position: relative;
  display: flex;
  min-height: 352rpx;
  margin-bottom: 28rpx;
  overflow: hidden;
  background: #fff7e8;
  border: 4rpx solid rgba(126, 82, 35, 0.58);
  border-radius: 34rpx;
  box-shadow: 0 18rpx 30rpx rgba(97, 63, 28, 0.15);
}

.home-book-card::before {
  position: absolute;
  top: 18rpx;
  bottom: 18rpx;
  left: 52%;
  z-index: 1;
  width: 3rpx;
  content: '';
  background: rgba(126, 82, 35, 0.2);
  box-shadow: -10rpx 0 18rpx rgba(97, 63, 28, 0.08);
}

.home-book-card__left,
.home-book-card__right {
  position: relative;
  z-index: 2;
  width: 50%;
}

.home-book-card__left {
  width: 52%;
  padding: 38rpx 28rpx 28rpx;
}

.home-book-card__right {
  width: 48%;
}

.home-book-card__title {
  display: block;
  font-size: 46rpx;
  font-weight: 900;
  line-height: 1.08;
  color: #4a2f1b;
}

.home-book-card__title-line {
  display: block;
}

.home-book-card__underline {
  width: 82rpx;
  height: 8rpx;
  margin: 16rpx 0;
  background: #f26a21;
  border-radius: 999rpx;
}

.home-book-card__desc {
  display: block;
  margin-bottom: 20rpx;
  font-size: 28rpx;
  line-height: 1.5;
  color: #5d3b22;
}

.home-book-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  margin-bottom: 22rpx;
}

.home-book-card__tag {
  display: flex;
  gap: 8rpx;
  align-items: center;
  height: 50rpx;
  padding: 0 18rpx;
  font-size: 24rpx;
  font-weight: 700;
  border-radius: 999rpx;
}

.home-book-card__tag--orange {
  color: #d94b12;
  background: #fff1d8;
  border: 2rpx solid rgba(242, 106, 33, 0.2);
}

.home-book-card__tag--blue {
  color: #235b83;
  background: #dfeff8;
  border: 2rpx solid rgba(47, 111, 148, 0.18);
}

.home-book-card__tag-mark {
  font-size: 20rpx;
}

.home-book-card__button {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 282rpx;
  height: 76rpx;
  font-size: 29rpx;
  font-weight: 800;
  color: #fff;
  background: #f26a21;
  border-radius: 30rpx;
  box-shadow: 0 12rpx 18rpx rgba(217, 75, 18, 0.24);
}

.home-book-card__button-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42rpx;
  height: 42rpx;
  margin-left: 16rpx;
  font-size: 40rpx;
  color: #f26a21;
  background: #fffaf0;
  border-radius: 50%;
}

.home-book-card__right {
  padding: 14rpx 16rpx 14rpx 0;
}

.home-scene {
  position: relative;
  height: 100%;
  min-height: 316rpx;
  overflow: hidden;
  background: #cfe7f5;
  border-radius: 20rpx;
}

.home-scene__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 24% 22%, rgba(255, 255, 255, 0.92) 0 38rpx, transparent 40rpx),
    radial-gradient(circle at 42% 18%, rgba(255, 255, 255, 0.78) 0 28rpx, transparent 30rpx),
    #bfe1f5;
}

.home-scene__palace {
  position: absolute;
  right: 20rpx;
  bottom: 92rpx;
  left: 20rpx;
}

.home-scene__roof {
  height: 54rpx;
  background: #ee9d1f;
  border: 4rpx solid rgba(126, 82, 35, 0.26);
  border-radius: 60rpx 60rpx 16rpx 16rpx;
  transform: skewX(-8deg);
}

.home-scene__hall {
  height: 82rpx;
  margin: -4rpx 14rpx 0;
  background:
    repeating-linear-gradient(90deg, rgba(90, 51, 26, 0.28) 0 8rpx, transparent 8rpx 30rpx),
    #d45528;
  border: 4rpx solid rgba(126, 82, 35, 0.2);
  border-radius: 8rpx;
}

.home-scene__rail {
  height: 20rpx;
  margin: 8rpx 4rpx 0;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 999rpx;
}

.home-scene__walkway {
  position: absolute;
  right: -40rpx;
  bottom: -20rpx;
  left: -40rpx;
  height: 132rpx;
  background:
    linear-gradient(90deg, rgba(126, 82, 35, 0.12) 1rpx, transparent 1rpx 58rpx),
    linear-gradient(rgba(126, 82, 35, 0.1) 1rpx, transparent 1rpx 42rpx),
    #ead7b8;
  transform: perspective(220rpx) rotateX(24deg);
}

.home-scene__ribbon {
  position: absolute;
  top: 0;
  right: 0;
  width: 56rpx;
  padding: 16rpx 0;
  font-size: 25rpx;
  font-weight: 800;
  line-height: 1.1;
  color: #fff;
  text-align: center;
  background: #e85c2e;
  border-radius: 0 18rpx 0 18rpx;
}

.home-entry-grid {
  display: flex;
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.home-entry {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  min-height: 232rpx;
  padding: 28rpx 20rpx 18rpx;
  overflow: hidden;
  text-align: left;
  border: 3rpx solid rgba(190, 142, 78, 0.34);
  border-radius: 26rpx;
  box-shadow: 0 12rpx 22rpx rgba(97, 63, 28, 0.09);
}

.home-entry--green {
  background: #dceecb;
}

.home-entry--yellow {
  background: #fff0bd;
}

.home-entry--blue {
  background: #cfe7f5;
}

.home-entry__title {
  display: block;
  margin-bottom: 12rpx;
  font-size: 31rpx;
  font-weight: 900;
  color: #214b32;
}

.home-entry--yellow .home-entry__title {
  color: #5e3c22;
}

.home-entry--blue .home-entry__title {
  color: #17496e;
}

.home-entry__desc {
  display: block;
  font-size: 24rpx;
  line-height: 1.35;
  color: #4f3b28;
}

.home-entry__art {
  position: absolute;
  right: 18rpx;
  bottom: 16rpx;
  width: 122rpx;
  height: 84rpx;
}

.home-entry__paper {
  position: absolute;
  right: 12rpx;
  bottom: 0;
  width: 86rpx;
  height: 64rpx;
  background: rgba(255, 250, 240, 0.8);
  border: 2rpx solid rgba(126, 82, 35, 0.22);
  border-radius: 12rpx;
  transform: rotate(-6deg);
}

.home-entry__mark {
  position: absolute;
  right: 0;
  bottom: 14rpx;
  width: 38rpx;
  height: 38rpx;
  background: #f26a21;
  border: 4rpx solid rgba(255, 250, 240, 0.9);
  border-radius: 50%;
}

.home-section-title {
  display: flex;
  gap: 12rpx;
  align-items: center;
  margin-bottom: 18rpx;
  font-size: 34rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.home-section-title__star {
  font-size: 20rpx;
  font-weight: 800;
  color: #f4aa23;
  transform: rotate(-18deg);
}

.home-learn__grid {
  display: flex;
  gap: 18rpx;
}

.home-learn-card {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  min-height: 206rpx;
  padding: 22rpx 16rpx;
  overflow: hidden;
  background: #fff7e8;
  border: 3rpx solid rgba(190, 142, 78, 0.24);
  border-radius: 24rpx;
}

.home-learn-card--orange {
  background: #fff1d8;
}

.home-learn-card--yellow {
  background: #fff0bd;
}

.home-learn-card--blue {
  background: #dceef8;
}

.home-learn-card__title {
  display: block;
  margin-bottom: 10rpx;
  font-size: 26rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.home-learn-card__desc {
  position: relative;
  z-index: 2;
  display: block;
  font-size: 21rpx;
  line-height: 1.4;
  color: #5f4937;
}

.home-learn-card__visual {
  position: absolute;
  right: 8rpx;
  bottom: 8rpx;
  width: 86rpx;
  height: 66rpx;
  opacity: 0.86;
}

.home-learn-card__shape {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 70rpx;
  height: 52rpx;
  background: rgba(255, 250, 240, 0.72);
  border: 2rpx solid rgba(126, 82, 35, 0.16);
  border-radius: 20rpx 20rpx 12rpx 12rpx;
}

.home-learn-card__tape {
  position: absolute;
  top: 0;
  left: 4rpx;
  width: 44rpx;
  height: 18rpx;
  background: rgba(242, 106, 33, 0.35);
  border-radius: 8rpx;
  transform: rotate(-14deg);
}

.plan-sheet {
  position: fixed;
  inset: 0;
  z-index: 100;
}

.plan-sheet__mask {
  position: absolute;
  inset: 0;
  background: rgba(74, 47, 27, 0.3);
}

.plan-sheet__panel {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  max-width: 430px;
  margin: 0 auto;
  padding: 18rpx 32rpx calc(30rpx + env(safe-area-inset-bottom));
  background: #fff7e8;
  border: 3rpx solid rgba(190, 142, 78, 0.36);
  border-radius: 36rpx 36rpx 0 0;
  box-shadow: 0 -18rpx 36rpx rgba(74, 47, 27, 0.14);
}

.plan-sheet__handle {
  width: 84rpx;
  height: 8rpx;
  margin: 0 auto 22rpx;
  background: rgba(138, 109, 84, 0.35);
  border-radius: 999rpx;
}

.plan-sheet__header {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.plan-sheet__title {
  display: block;
  font-size: 36rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.plan-sheet__subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  line-height: 1.4;
  color: #8a6d54;
}

.plan-sheet__close {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  height: 56rpx;
  padding: 0 20rpx;
  font-size: 24rpx;
  color: #8a6d54;
  border: 2rpx solid rgba(190, 142, 78, 0.32);
  border-radius: 999rpx;
}

.plan-sheet__field {
  margin-bottom: 20rpx;
}

.plan-sheet__label {
  display: block;
  margin-bottom: 10rpx;
  font-size: 25rpx;
  font-weight: 800;
  color: #5e3c22;
}

.plan-sheet__field input {
  width: 100%;
  height: 72rpx;
  padding: 0 22rpx;
  font-size: 28rpx;
  color: #4a2f1b;
  background: #fffaf0;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 20rpx;
}

.plan-sheet__age-list,
.plan-sheet__interests {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.plan-sheet__age,
.plan-sheet__interest {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 62rpx;
  padding: 0 22rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: #6b482d;
  background: #f6dfaf;
  border: 2rpx solid rgba(190, 142, 78, 0.26);
  border-radius: 999rpx;
}

.plan-sheet__age--active,
.plan-sheet__interest--active {
  color: #fff;
  background: #f26a21;
  border-color: #f26a21;
}

.plan-sheet__submit {
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

@media (max-width: 360px) {
  .home-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .home-header__title {
    font-size: 62rpx;
  }

  .home-search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .home-age {
    justify-content: flex-end;
  }
}

@media (min-width: 431px) {
  .home-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(122px + env(safe-area-inset-bottom));
  }

  .home-header {
    gap: 10px;
    margin-bottom: 18px;
  }

  .home-header__title {
    padding-top: 10px;
    font-size: 42px;
  }

  .home-header__subtitle {
    margin-top: 10px;
    font-size: 17px;
  }

  .home-header__tools {
    gap: 8px;
    padding-top: 24px;
  }

  .home-header__city {
    height: 34px;
    font-size: 16px;
  }

  .home-header__notice {
    width: 34px;
    height: 34px;
    font-size: 13px;
    border-width: 2px;
  }

  .home-search-row {
    gap: 10px;
    margin-bottom: 16px;
  }

  .home-search {
    height: 48px;
    padding: 0 13px;
    border-width: 2px;
    border-radius: 16px;
  }

  .home-search__icon {
    margin-right: 8px;
    font-size: 24px;
  }

  .home-search input {
    height: 44px;
    font-size: 16px;
  }

  .home-search__send {
    font-size: 28px;
  }

  .home-age {
    gap: 8px;
  }

  .home-age__item {
    min-width: 64px;
    height: 36px;
    padding: 0 12px;
    font-size: 15px;
    border-radius: 14px;
  }

  .home-book-card {
    min-height: 206px;
    margin-bottom: 16px;
    border-width: 2px;
    border-radius: 20px;
  }

  .home-book-card__left {
    width: 52%;
    padding: 22px 16px 16px;
  }

  .home-book-card__right {
    width: 48%;
  }

  .home-book-card__title {
    font-size: 26px;
    line-height: 1.08;
  }

  .home-book-card__desc {
    margin-bottom: 12px;
    font-size: 16px;
  }

  .home-book-card__tags {
    gap: 8px;
    margin-bottom: 12px;
  }

  .home-book-card__tag {
    height: 28px;
    padding: 0 10px;
    font-size: 13px;
  }

  .home-book-card__button {
    width: 160px;
    height: 42px;
    font-size: 16px;
    border-radius: 18px;
  }

  .home-scene {
    min-height: 184px;
  }

  .home-entry-grid {
    gap: 11px;
    margin-bottom: 18px;
  }

  .home-entry {
    min-height: 132px;
    padding: 16px 11px 10px;
    border-width: 2px;
    border-radius: 15px;
  }

  .home-entry__title {
    font-size: 18px;
  }

  .home-entry__desc {
    font-size: 13px;
  }

  .home-section-title {
    margin-bottom: 10px;
    font-size: 20px;
  }

  .home-learn__grid {
    gap: 10px;
  }

  .home-learn-card {
    min-height: 118px;
    padding: 13px 9px;
    border-width: 2px;
    border-radius: 14px;
  }

  .home-learn-card__title {
    font-size: 15px;
  }

  .home-learn-card__desc {
    font-size: 12px;
  }

  .plan-sheet__panel {
    padding: 12px 18px calc(18px + env(safe-area-inset-bottom));
  }
}
</style>
