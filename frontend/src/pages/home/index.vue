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
            <view class="home-header__pin" aria-hidden="true"></view>
            <text>北京</text>
            <view class="home-header__arrow" aria-hidden="true"></view>
          </view>
          <view class="home-header__notice" @click="noop">
            <view class="home-header__notice-icon" aria-hidden="true"></view>
            <view class="home-header__dot"></view>
          </view>
        </view>
      </view>

      <view class="home-search-row">
        <view class="home-search">
          <view class="home-search__icon" aria-hidden="true"></view>
          <input v-model="searchKeyword" placeholder="输入这次要去的地方" />
          <view class="home-search__send" aria-hidden="true"></view>
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

      <view class="home-hero">
        <view class="home-hero__book">
          <view class="home-hero__content">
            <text class="home-hero__eyebrow">故宫文化探索</text>
            <text class="home-hero__title">故宫亲子探索</text>
            <view class="home-hero__underline"></view>
            <text class="home-hero__desc">认识古代皇宫，边看边学</text>

            <view class="home-hero__tags">
              <view class="home-hero__tag home-hero__tag--orange">
                <view class="home-hero__tag-icon home-hero__tag-icon--age" aria-hidden="true"></view>
                <text>7-12岁</text>
              </view>
              <view class="home-hero__tag home-hero__tag--blue">
                <view class="home-hero__tag-icon home-hero__tag-icon--time" aria-hidden="true"></view>
                <text>约3小时</text>
              </view>
            </view>

            <view class="home-hero__cta" @click="openPlanSheet">
              <text>创建探索计划</text>
              <view class="home-hero__cta-arrow" aria-hidden="true"></view>
            </view>
          </view>

          <view class="home-hero__illustration" aria-hidden="true">
            <image
              class="home-hero__image"
              src="../../assets/home/home-hero-watercolor.webp"
              mode="aspectFill"
            />
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
          <image
            class="home-entry__art"
            :class="`home-entry__art--${entry.theme}`"
            :src="entry.art"
            mode="aspectFit"
            aria-hidden="true"
          />
        </view>
      </view>

      <view class="home-learn">
        <view class="home-section-title">
          <view class="home-section-title__star" aria-hidden="true"></view>
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
            <image
              class="home-learn-card__art"
              :class="`home-learn-card__art--${item.theme}`"
              :src="item.art"
              mode="aspectFit"
              aria-hidden="true"
            />
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

    <AudioGuideSheet v-model:open="audioGuideOpen" :plan-id="audioGuidePlanId" />
    <AppTabbar active="home" />
  </view>
</template>

<script>
import AudioGuideSheet from '../../components/AudioGuideSheet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { useChildStore } from '../../stores/child'
import { usePlanStore } from '../../stores/plan'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'
import { endUserSession } from '../../utils/sessionBoundary'
import entryPlanMap from '../../assets/home/home-entry-plan-map.webp'
import entryGuideCards from '../../assets/home/home-entry-guide-cards.webp'
import entryObservationNotebook from '../../assets/home/home-entry-observation-notebook.webp'
import learningAncientLife from '../../assets/home/home-learning-ancient-life.webp'
import learningArchitectureRitual from '../../assets/home/home-learning-architecture-ritual.webp'
import learningObservationExpression from '../../assets/home/home-learning-observation-expression.webp'

export default {
  components: {
    AudioGuideSheet,
    AppTabbar,
  },
  data() {
    return {
      searchKeyword: '',
      planSheetOpen: false,
      audioGuideOpen: false,
      audioGuidePlanId: null,
      isOpeningAudioGuide: false,
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
          art: entryPlanMap,
          path: '/pages/plan/index',
          method: 'reLaunch',
        },
        {
          title: '景点讲解',
          desc: '家长轻松讲',
          theme: 'yellow',
          art: entryGuideCards,
          action: 'audio-guide',
        },
        {
          title: '观察任务',
          desc: '边看边完成',
          theme: 'blue',
          art: entryObservationNotebook,
          path: '/pages/tasks/index',
          method: 'reLaunch',
        },
      ],
      learningItems: [
        {
          title: '古代生活',
          desc: '了解皇宫里的衣食住行',
          theme: 'orange',
          art: learningAncientLife,
        },
        {
          title: '建筑礼仪',
          desc: '发现古建筑的智慧与礼仪',
          theme: 'yellow',
          art: learningArchitectureRitual,
        },
        {
          title: '观察表达',
          desc: '学会观察，勇敢表达',
          theme: 'blue',
          art: learningObservationExpression,
        },
      ],
    }
  },
  computed: {
    activeChild() {
      return this.child.activeChild
    },
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
    this.planForm.ageGroup = this.activeChild?.ageGroup || this.child.ageGroup
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
      const activeChild = this.activeChild
      this.planForm = {
        title: '',
        destination: this.searchKeyword.trim() || '故宫博物院',
        ageGroup: activeChild?.ageGroup || this.child.ageGroup,
        duration: '3小时',
        interests: activeChild?.interests?.length
          ? [...activeChild.interests]
          : ['古代生活', '建筑礼仪', '观察表达'],
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
        const activeChild = this.child.activeChild
        if (!this.child.hasRemoteChild || !activeChild) {
          this.showToast('请先完善孩子档案')
          uni.reLaunch({
            url: '/pages/profile/index',
          })
          return
        }

        if (this.planForm.ageGroup !== activeChild.ageGroup) {
          this.showToast(`当前孩子年龄组为 ${activeChild.ageGroup} 岁，请调整年龄选择或修改孩子档案`)
          return
        }

        const normalizedTitle = this.planForm.title.trim()
        const payload = {
          destination: this.planForm.destination.trim() || '故宫博物院',
          duration: this.planForm.duration.trim() || '3小时',
          interests: [...this.planForm.interests],
          childId: activeChild.id,
          ageGroup: activeChild.ageGroup,
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
    async openAudioGuide() {
      if (this.isOpeningAudioGuide) {
        return
      }

      this.isOpeningAudioGuide = true
      try {
        const result = await ensureCurrentPlanReady({ withTasks: false })
        if (result.currentPlan?.id !== null && result.currentPlan?.id !== undefined) {
          this.audioGuidePlanId = result.currentPlan.id
        } else {
          this.audioGuidePlanId = null
        }
        this.audioGuideOpen = true
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
          return
        }
        this.audioGuidePlanId = null
        this.audioGuideOpen = true
      } finally {
        this.isOpeningAudioGuide = false
      }
    },
    goEntry(entry) {
      if (entry.action === 'audio-guide') {
        this.openAudioGuide()
        return
      }
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

/* FE-R5B Stage A: local picture-book visual layer. */
.home-page {
  color: var(--tl-text-main);
  background:
    radial-gradient(circle at 12% 7%, rgba(255, 238, 181, 0.54) 0, rgba(255, 238, 181, 0) 116rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.045) 0 1rpx, transparent 1rpx 24rpx),
    var(--tl-bg);
}

.home-page__paper {
  max-width: var(--tl-content-max-width);
  padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 72rpx);
}

.home-header {
  position: relative;
  gap: 16rpx;
  margin-bottom: 30rpx;
}

.home-header__title {
  padding-top: 16rpx;
  font-size: 74rpx;
  letter-spacing: 2rpx;
  color: var(--tl-text-main);
  text-shadow: 1rpx 2rpx 0 rgba(255, 255, 255, 0.78);
}

.home-header__title::after {
  display: inline-block;
  width: 18rpx;
  height: 18rpx;
  margin: 0 0 18rpx 10rpx;
  content: '';
  background: var(--tl-yellow);
  border: 3rpx solid var(--tl-primary);
  border-radius: 4rpx 12rpx;
  transform: rotate(28deg);
}

.home-header__subtitle {
  margin-top: 16rpx;
  font-size: 27rpx;
  color: var(--tl-text-secondary);
  letter-spacing: 1rpx;
}

.home-header__tools {
  gap: 10rpx;
  padding-top: 34rpx;
}

.home-header__city {
  gap: 7rpx;
  height: 54rpx;
  font-size: 26rpx;
  color: var(--tl-text-secondary);
}

.home-header__pin {
  position: relative;
  width: 23rpx;
  height: 29rpx;
  border: 4rpx solid var(--tl-primary-deep);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
}

.home-header__pin::after {
  position: absolute;
  top: 6rpx;
  left: 6rpx;
  width: 7rpx;
  height: 7rpx;
  content: '';
  background: var(--tl-paper);
  border-radius: 50%;
}

.home-header__arrow {
  width: 12rpx;
  height: 12rpx;
  margin: 0 4rpx 7rpx 2rpx;
  border-right: 3rpx solid var(--tl-text-secondary);
  border-bottom: 3rpx solid var(--tl-text-secondary);
  transform: rotate(45deg);
}

.home-header__notice {
  width: 54rpx;
  height: 54rpx;
  color: var(--tl-text-main);
  background: var(--tl-paper);
  border: 2rpx solid rgba(190, 142, 78, 0.52);
  border-radius: 20rpx 20rpx 16rpx 16rpx;
  box-shadow: 0 6rpx 12rpx rgba(97, 63, 28, 0.08);
}

.home-header__notice-icon {
  position: relative;
  width: 24rpx;
  height: 26rpx;
  border: 3rpx solid currentColor;
  border-bottom: 0;
  border-radius: 15rpx 15rpx 8rpx 8rpx;
}

.home-header__notice-icon::before,
.home-header__notice-icon::after {
  position: absolute;
  left: 50%;
  content: '';
  transform: translateX(-50%);
}

.home-header__notice-icon::before {
  bottom: -5rpx;
  width: 32rpx;
  border-bottom: 3rpx solid currentColor;
}

.home-header__notice-icon::after {
  bottom: -10rpx;
  width: 6rpx;
  height: 6rpx;
  background: currentColor;
  border-radius: 50%;
}

.home-header__dot {
  background: var(--tl-primary);
}

.home-search-row {
  gap: 16rpx;
  margin-bottom: 34rpx;
}

.home-search {
  height: 88rpx;
  padding: 0 24rpx;
  background: var(--tl-paper);
  border: 3rpx solid rgba(190, 142, 78, 0.64);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 8rpx 16rpx rgba(97, 63, 28, 0.055);
}

.home-search__icon {
  position: relative;
  flex: 0 0 auto;
  width: 29rpx;
  height: 29rpx;
  margin-right: 18rpx;
  border: 4rpx solid var(--tl-text-secondary);
  border-radius: 50%;
}

.home-search__icon::after {
  position: absolute;
  right: -12rpx;
  bottom: -8rpx;
  width: 15rpx;
  content: '';
  border-bottom: 4rpx solid var(--tl-text-secondary);
  transform: rotate(48deg);
  transform-origin: left center;
}

.home-search input {
  color: var(--tl-text-main);
}

.home-search__send {
  width: 18rpx;
  height: 18rpx;
  margin-left: 12rpx;
  border-top: 4rpx solid #e7a83d;
  border-right: 4rpx solid #e7a83d;
  transform: rotate(45deg);
}

.home-age {
  gap: 10rpx;
}

.home-age__item {
  min-width: 108rpx;
  height: 60rpx;
  padding: 0 20rpx;
  color: var(--tl-text-secondary);
  background: var(--tl-yellow);
  border: 2rpx solid rgba(190, 142, 78, 0.24);
  border-radius: var(--tl-radius-sm);
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.home-age__item--active {
  color: var(--tl-paper);
  background: var(--tl-primary);
  border-color: var(--tl-primary-deep);
  box-shadow: 0 8rpx 14rpx rgba(242, 106, 33, 0.2);
}

.home-age__item:active,
.home-hero__cta:active,
.home-entry:active,
.plan-sheet__submit:active {
  transform: translateY(2rpx);
}

.home-hero {
  position: relative;
  margin-bottom: 36rpx;
}

.home-hero__book {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 416rpx;
  overflow: hidden;
  background: var(--tl-paper-deep);
  border: 4rpx solid rgba(126, 82, 35, 0.54);
  border-radius: 34rpx 40rpx 32rpx 38rpx;
  box-shadow: 0 18rpx 28rpx rgba(97, 63, 28, 0.14);
}

.home-hero__illustration {
  position: relative;
  box-sizing: border-box;
  width: calc(50% - 26rpx);
  min-height: 376rpx;
  margin: 18rpx 8rpx 18rpx 18rpx;
  overflow: hidden;
  background: #f1e0b8;
  border-radius: 24rpx 10rpx 12rpx 24rpx;
}

.home-hero__image {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: block;
  width: 100%;
  height: 100%;
}

.home-hero__content {
  position: relative;
  box-sizing: border-box;
  width: 50%;
  padding: 30rpx 24rpx 24rpx 28rpx;
  background: var(--tl-paper);
  box-shadow: inset 16rpx 0 24rpx rgba(97, 63, 28, 0.045);
}

.home-hero__eyebrow {
  display: block;
  margin-bottom: 10rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-primary-deep);
  letter-spacing: 2rpx;
}

.home-hero__title {
  display: block;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.1;
  color: var(--tl-text-main);
}

.home-hero__title-line {
  display: block;
}

.home-hero__underline {
  width: 68rpx;
  height: 7rpx;
  margin: 14rpx 0;
  background: var(--tl-primary);
  border-radius: 999rpx;
  transform: rotate(-3deg);
}

.home-hero__desc {
  display: block;
  min-height: 74rpx;
  margin-bottom: 16rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: var(--tl-text-secondary);
}

.home-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 18rpx;
}

.home-hero__tag {
  display: flex;
  gap: 7rpx;
  align-items: center;
  height: 46rpx;
  padding: 0 13rpx;
  font-size: 22rpx;
  font-weight: 700;
  border-radius: 999rpx;
}

.home-hero__tag--orange {
  color: var(--tl-primary-deep);
  background: #fff1d8;
  border: 2rpx solid rgba(242, 106, 33, 0.2);
}

.home-hero__tag--blue {
  color: #235b83;
  background: #dfeff8;
  border: 2rpx solid rgba(47, 111, 148, 0.18);
}

.home-hero__tag-icon {
  position: relative;
  width: 22rpx;
  height: 22rpx;
  flex: 0 0 auto;
}

.home-hero__tag-icon--age {
  border: 3rpx solid currentColor;
  border-radius: 6rpx;
}

.home-hero__tag-icon--age::after {
  position: absolute;
  right: 2rpx;
  bottom: 3rpx;
  width: 9rpx;
  height: 5rpx;
  content: '';
  border-bottom: 3rpx solid currentColor;
  border-left: 3rpx solid currentColor;
  transform: rotate(-45deg);
}

.home-hero__tag-icon--time {
  border: 3rpx solid currentColor;
  border-radius: 50%;
}

.home-hero__tag-icon--time::after {
  position: absolute;
  top: 3rpx;
  left: 9rpx;
  width: 6rpx;
  height: 8rpx;
  content: '';
  border-bottom: 3rpx solid currentColor;
  border-left: 3rpx solid currentColor;
}

.home-hero__cta {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 70rpx;
  font-size: 26rpx;
  font-weight: 900;
  color: var(--tl-paper);
  background: var(--tl-primary);
  border: 2rpx solid var(--tl-primary-deep);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 10rpx 16rpx rgba(217, 75, 18, 0.2);
  transition: transform 160ms ease;
}

.home-hero__cta-arrow,
.home-entry__arrow {
  width: 12rpx;
  height: 12rpx;
  border-top: 3rpx solid currentColor;
  border-right: 3rpx solid currentColor;
  transform: rotate(45deg);
}

.home-hero__cta-arrow {
  margin-left: 14rpx;
  color: var(--tl-primary);
  background: var(--tl-paper);
  border: 9rpx solid var(--tl-paper);
  border-left-width: 7rpx;
  border-bottom-width: 7rpx;
  border-radius: 50%;
}

.home-entry-grid,
.home-learn__grid {
  gap: 16rpx;
}

.home-entry {
  min-height: 242rpx;
  padding: 26rpx 18rpx 20rpx;
  border: 2rpx solid rgba(190, 142, 78, 0.4);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 10rpx 18rpx rgba(97, 63, 28, 0.075);
  transition: transform 160ms ease;
}

.home-entry--green { background: var(--tl-green); }
.home-entry--yellow { background: var(--tl-yellow); }
.home-entry--blue { background: var(--tl-blue); }

.home-entry__title {
  position: relative;
  z-index: 2;
  margin-bottom: 10rpx;
  font-size: 30rpx;
  color: var(--tl-text-main);
}

.home-entry__desc {
  position: relative;
  z-index: 2;
  font-size: 22rpx;
  color: var(--tl-text-secondary);
}

.home-entry__art {
  right: 12rpx;
  bottom: 14rpx;
  width: 96rpx;
  height: 76rpx;
  pointer-events: none;
}

.home-section-title {
  gap: 14rpx;
  color: var(--tl-text-main);
}

.home-section-title__star {
  width: 22rpx;
  height: 22rpx;
  background: #f4aa23;
  border-radius: 7rpx;
  transform: rotate(-18deg);
}

.home-learn-card {
  min-height: 218rpx;
  padding: 22rpx 16rpx;
  background: var(--tl-paper);
  border: 2rpx solid rgba(190, 142, 78, 0.3);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 8rpx 14rpx rgba(97, 63, 28, 0.055);
}

.home-learn-card--orange { background: #fff1d8; }
.home-learn-card--yellow { background: var(--tl-yellow); }
.home-learn-card--blue { background: var(--tl-blue); }

.home-learn-card__title { color: var(--tl-text-main); }
.home-learn-card__desc { color: var(--tl-text-secondary); }

.plan-sheet__panel {
  max-width: var(--tl-content-max-width);
  max-height: calc(100vh - 28rpx - var(--tl-safe-top));
  overflow-y: auto;
  padding-bottom: calc(30rpx + var(--tl-safe-bottom));
  background: var(--tl-paper);
  border-color: rgba(190, 142, 78, 0.42);
}

.plan-sheet__title,
.plan-sheet__label { color: var(--tl-text-main); }
.plan-sheet__subtitle,
.plan-sheet__close { color: var(--tl-text-secondary); }
.plan-sheet__field input { color: var(--tl-text-main); background: #fffaf0; }
.plan-sheet__submit { background: var(--tl-primary); }

@media (max-width: 360px) {
  .home-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .home-header__title { font-size: 62rpx; }
  .home-search-row { flex-direction: column; align-items: stretch; }
  .home-age { justify-content: flex-end; }
  .home-hero__book { min-height: 0; }
  .home-hero__content { padding: 24rpx 18rpx 20rpx 22rpx; }
  .home-hero__title { font-size: 38rpx; }
  .home-hero__desc { font-size: 22rpx; }
  .home-hero__cta { font-size: 23rpx; }
  .home-entry { min-height: 220rpx; padding: 22rpx 14rpx 18rpx; }
  .home-entry__title { font-size: 27rpx; }
  .home-entry__desc { font-size: 20rpx; }
  .home-entry__art { transform: scale(0.84); transform-origin: right bottom; }
  .home-learn-card { min-height: 202rpx; }
}

@media (min-width: 431px) {
  .home-page__paper {
    padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 34px);
  }

  .home-hero__book { min-height: 252px; }
  .home-hero__illustration { min-height: 230px; margin: 10px 4px 10px 10px; }
  .home-hero__content { padding: 18px 14px 14px 18px; }
  .home-hero__eyebrow { font-size: 12px; margin-bottom: 5px; }
  .home-hero__title { font-size: 26px; }
  .home-hero__underline { width: 40px; height: 4px; margin: 8px 0; }
  .home-hero__desc { min-height: 42px; margin-bottom: 9px; font-size: 14px; }
  .home-hero__tags { gap: 5px; margin-bottom: 9px; }
  .home-hero__tag { height: 28px; padding: 0 8px; font-size: 12px; }
  .home-hero__tag-icon { width: 13px; height: 13px; }
  .home-hero__cta { height: 42px; font-size: 16px; }
  .home-entry { min-height: 142px; padding: 15px 11px 10px; }
  .home-entry__title { font-size: 18px; }
  .home-entry__desc { font-size: 13px; }
  .home-entry__art { transform: scale(0.75); transform-origin: right bottom; }
  .home-learn-card { min-height: 126px; padding: 13px 9px; }
}

/* Home Visual Implementation: real watercolor illustrations and restrained paper texture. */
.home-page {
  position: relative;
  isolation: isolate;
  background: #f8efd9;
}

.home-page::before {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  content: '';
  background-image: url('../../assets/home/home-paper-fiber.webp');
  background-repeat: repeat;
  background-size: 512rpx 512rpx;
  opacity: 0.13;
}

.home-page__paper {
  position: relative;
  z-index: 1;
}

.home-hero__book {
  min-height: 500rpx;
  border-color: rgba(126, 82, 35, 0.58);
  border-radius: 38rpx 44rpx 36rpx 42rpx;
}

.home-hero__book::after {
  position: absolute;
  top: 18rpx;
  bottom: 18rpx;
  left: 55%;
  z-index: 3;
  width: 2rpx;
  pointer-events: none;
  content: '';
  background: rgba(126, 82, 35, 0.24);
  box-shadow: 8rpx 0 14rpx rgba(97, 63, 28, 0.08);
}

.home-hero__content {
  order: 1;
  width: 55%;
  padding: 28rpx 20rpx 24rpx 28rpx;
  background: var(--tl-paper);
  box-shadow: inset -10rpx 0 22rpx rgba(97, 63, 28, 0.035);
}

.home-hero__illustration {
  order: 2;
  width: 45%;
  min-height: 0;
  margin: 0;
  background: #d9edf5;
  border-radius: 0 38rpx 32rpx 0;
}

.home-hero__title {
  font-size: 46rpx;
  line-height: 1.12;
  white-space: normal;
  word-break: normal;
}

.home-hero__desc {
  min-height: 0;
  margin-bottom: 14rpx;
}

.home-entry-grid,
.home-learn__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.home-entry {
  min-height: 306rpx;
  padding: 24rpx 18rpx 18rpx;
}

.home-entry__title,
.home-entry__desc,
.home-learn-card__title,
.home-learn-card__desc {
  position: relative;
  z-index: 2;
}

.home-entry__desc {
  max-width: 88%;
}

.home-entry__art {
  position: absolute;
  z-index: 1;
  display: block;
  pointer-events: none;
}

.home-entry__art--green {
  right: -18rpx;
  bottom: -12rpx;
  width: 182rpx;
  height: 162rpx;
}

.home-entry__art--yellow {
  right: -30rpx;
  bottom: -24rpx;
  width: 188rpx;
  height: 190rpx;
}

.home-entry__art--blue {
  right: -22rpx;
  bottom: -20rpx;
  width: 188rpx;
  height: 184rpx;
}

.home-learn-card {
  min-height: 278rpx;
  padding: 18rpx 16rpx;
}

.home-learn-card__title {
  margin-bottom: 7rpx;
  font-size: 26rpx;
}

.home-learn-card__desc {
  font-size: 19rpx;
  line-height: 1.38;
}

.home-learn-card__art {
  position: absolute;
  z-index: 1;
  display: block;
  pointer-events: none;
}

.home-learn-card__art--orange {
  right: -18rpx;
  bottom: -14rpx;
  width: 140rpx;
  height: 138rpx;
}

.home-learn-card__art--yellow {
  bottom: -18rpx;
  left: -20rpx;
  width: 182rpx;
  height: 126rpx;
}

.home-learn-card__art--blue {
  right: -15rpx;
  bottom: -17rpx;
  width: 146rpx;
  height: 134rpx;
}

@media (max-width: 360px) {
  .home-hero__book {
    min-height: 460rpx;
  }

  .home-hero__content {
    padding: 24rpx 16rpx 20rpx 22rpx;
  }

  .home-hero__title {
    font-size: 42rpx;
  }

  .home-entry-grid,
  .home-learn__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18rpx;
  }

  .home-entry {
    min-height: 310rpx;
  }

  .home-entry:last-child,
  .home-learn-card:last-child {
    grid-column: span 2;
  }

  .home-learn-card {
    min-height: 286rpx;
  }

  .home-entry__art--green,
  .home-entry__art--yellow,
  .home-entry__art--blue {
    width: 210rpx;
    height: 194rpx;
  }

  .home-learn-card__art--orange,
  .home-learn-card__art--blue {
    width: 176rpx;
    height: 160rpx;
  }

  .home-learn-card__art--yellow {
    width: 208rpx;
    height: 150rpx;
  }
}

@media (min-width: 431px) {
  .home-page::before {
    background-size: 320px 320px;
  }

  .home-hero__book {
    min-height: 278px;
  }

  .home-hero__book::after {
    top: 10px;
    bottom: 10px;
    left: 55%;
    width: 1px;
  }

  .home-hero__content {
    padding: 18px 12px 14px 17px;
  }

  .home-hero__title {
    font-size: 26px;
  }

  .home-entry-grid,
  .home-learn__grid {
    gap: 11px;
  }

  .home-entry {
    min-height: 164px;
    padding: 14px 11px 10px;
  }

  .home-entry__title {
    font-size: 18px;
  }

  .home-entry__desc {
    font-size: 13px;
  }

  .home-entry__art--green {
    right: -10px;
    bottom: -7px;
    width: 98px;
    height: 88px;
  }

  .home-entry__art--yellow,
  .home-entry__art--blue {
    right: -16px;
    bottom: -12px;
    width: 102px;
    height: 102px;
  }

  .home-learn-card {
    min-height: 148px;
    padding: 11px 9px;
  }

  .home-learn-card__title {
    font-size: 15px;
  }

  .home-learn-card__desc {
    font-size: 11px;
  }

  .home-learn-card__art--orange,
  .home-learn-card__art--blue {
    width: 76px;
    height: 74px;
  }

  .home-learn-card__art--yellow {
    width: 96px;
    height: 66px;
  }
}
</style>
