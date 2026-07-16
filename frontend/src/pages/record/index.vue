<template>
  <view class="record-page">
    <view class="record-page__paper">
      <view class="record-header">
        <view class="record-header__title-wrap">
          <text class="record-header__spark">记</text>
          <text class="record-header__title">记录</text>
          <text class="record-header__star">星</text>
        </view>
        <button class="record-header__notice" @click="openPetChat">
          <text>铃</text>
          <view class="record-header__dot"></view>
        </button>
      </view>

      <view class="record-summary">
        <view class="record-summary__tape"></view>
        <view class="record-summary__sun"></view>
        <view class="record-summary__leaf"></view>
        <text class="record-summary__title">{{ journey.summary.title }}</text>
        <view class="record-summary__location">
          <text class="record-summary__pin">地</text>
          <text>{{ journey.summary.destination }}</text>
        </view>
        <view class="record-summary__stats">
          <view v-for="stat in summaryStats" :key="stat.label" class="record-stat" :class="`record-stat--${stat.theme}`">
            <view class="record-stat__icon">{{ stat.icon }}</view>
            <view>
              <text class="record-stat__label">{{ stat.label }}</text>
              <text class="record-stat__value">{{ stat.value }}<text class="record-stat__unit">{{ stat.unit }}</text></text>
            </view>
          </view>
        </view>
      </view>

      <view class="section-title">
        <view class="section-title__camera"></view>
        <text>探索相册</text>
        <view class="section-title__line"></view>
        <text class="section-title__star">星</text>
      </view>

      <view class="album-list">
        <view
          v-for="(item, index) in journey.albumItems"
          :key="item.id"
          class="album-entry"
          :class="[`album-entry--${item.type}`, { 'album-entry--reverse': index % 2 === 1 }]"
        >
          <PolaroidCard
            class="album-entry__photo"
            :image-path="item.displayImagePath"
            :title="item.type === 'dialogue' ? '' : item.title"
            :description="item.type === 'dialogue' ? '' : photoDescription(item)"
            :date-label="item.type === 'dialogue' ? '' : item.dateLabel"
            :rotation="item.rotation"
            :placeholder-theme="placeholderTheme(item, index)"
            :tape-theme="tapeTheme(index)"
          >
            <template v-if="item.type === 'dialogue'" #photo>
              <view class="dialogue-photo">
                <text class="dialogue-photo__bubble">问</text>
                <text class="dialogue-photo__line">孩子的问题</text>
                <text class="dialogue-photo__quote">为什么屋顶这么高？</text>
              </view>
            </template>
          </PolaroidCard>

          <view class="album-note">
            <view class="album-note__sticker" :class="`album-note__sticker--${tapeTheme(index)}`"></view>
            <text class="album-note__title">{{ item.title }}</text>
            <view class="album-note__dash"></view>
            <text class="album-note__description">{{ item.description }}</text>
            <text class="album-note__date">{{ item.dateLabel }}</text>
            <text class="album-note__source">{{ item.source === 'task' ? '来自任务记录' : 'Mock 回忆' }}</text>
          </view>
        </view>
      </view>

      <view class="section-title section-title--growth">
        <text class="section-title__star">星</text>
        <text>成长收获</text>
        <view class="section-title__line"></view>
        <text class="section-title__star">星</text>
      </view>

      <view class="growth-grid">
        <GrowthBadge
          v-for="skill in growthItems"
          :key="skill.key"
          :label="skill.label"
          :value="skill.value"
          :description="skill.description"
          :icon="skill.icon"
          :theme="skill.theme"
        />
      </view>
    </view>

    <AiPet />
    <AppTabbar active="record" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import GrowthBadge from '../../components/GrowthBadge.vue'
import PolaroidCard from '../../components/PolaroidCard.vue'
import { usePetStore } from '../../stores/pet'
import { usePlanStore } from '../../stores/plan'
import { useRecordStore } from '../../stores/record'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'

export default {
  components: {
    AiPet,
    AppTabbar,
    GrowthBadge,
    PolaroidCard,
  },
  computed: {
    journey() {
      return this.record.currentJourneyRecord
    },
    plan() {
      return usePlanStore()
    },
    record() {
      return useRecordStore()
    },
    summaryStats() {
      return [
        {
          label: '完成任务',
          value: this.journey.summary.completedTaskCount,
          unit: '个',
          icon: '勾',
          theme: 'orange',
        },
        {
          label: '记录发现',
          value: this.journey.summary.discoveryCount,
          unit: '条',
          icon: '说',
          theme: 'blue',
        },
        {
          label: '获得勋章',
          value: this.journey.summary.badgeCount,
          unit: '枚',
          icon: '章',
          theme: 'green',
        },
      ]
    },
    task() {
      return useTaskStore()
    },
    user() {
      return useUserStore()
    },
    growthItems() {
      const skills = this.journey.growthSkills

      return [
        {
          key: 'observation',
          label: '会观察',
          value: skills.observation,
          description: '我能认真观察细节',
          icon: '看',
          theme: 'yellow',
        },
        {
          key: 'expression',
          label: '会表达',
          value: skills.expression,
          description: '我能说出自己的发现',
          icon: '说',
          theme: 'blue',
        },
        {
          key: 'initiative',
          label: '更主动',
          value: skills.initiative,
          description: '我愿意提问和探索',
          icon: '芽',
          theme: 'green',
        },
      ]
    },
  },
  async onShow() {
    usePetStore().setPageContext('record')
    await this.restorePlanAndTasks()
    await this.restoreTaskImages()
    this.refreshJourneyRecord()
  },
  methods: {
    async restorePlanAndTasks() {
      try {
        await ensureCurrentPlanReady({ withTasks: true })
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          this.plan.resetSessionState()
          this.task.resetSessionState()
        }
      }
    },
    async restoreTaskImages() {
      const imageTasks = this.task.currentPlanTasks.filter((task) =>
        task.record?.imageUrl && !task.record?.displayImagePath,
      )
      await Promise.all(imageTasks.map((task) =>
        this.task.ensureTaskImageDisplay(task.id).catch(() => null),
      ))
    },
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('record')
      petStore.openChat()
    },
    photoDescription(item) {
      return item.description.replace(/^发现：/, '')
    },
    placeholderTheme(item, index) {
      if (item.type === 'dialogue') {
        return 'dialogue'
      }

      return item.sourceTaskId === 'palace-gate' || index === 1 ? 'gate' : 'roof'
    },
    refreshJourneyRecord() {
      this.record.generateJourneyRecord({
        plan: this.plan.currentPlan,
        tasks: this.task.currentPlanTasks,
      })
    },
    tapeTheme(index) {
      return ['green', 'pink', 'blue'][index % 3]
    },
  },
}
</script>

<style scoped>
.record-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.44) 0, rgba(255, 240, 189, 0) 126rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.record-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  padding: calc(30rpx + env(safe-area-inset-top)) 30rpx calc(190rpx + env(safe-area-inset-bottom));
  margin: 0 auto;
}

.record-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  margin-bottom: 22rpx;
}

.record-header__title-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.record-header__title {
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1;
}

.record-header__spark,
.record-header__star {
  position: absolute;
  font-size: 24rpx;
  font-weight: 900;
  color: #f4aa23;
}

.record-header__spark {
  left: -44rpx;
  transform: rotate(-22deg);
}

.record-header__star {
  right: -48rpx;
  transform: rotate(16deg);
}

.record-header__notice {
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62rpx;
  height: 62rpx;
  font-size: 24rpx;
  font-weight: 900;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.record-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.record-summary {
  position: relative;
  padding: 46rpx 28rpx 28rpx;
  margin-bottom: 34rpx;
  background: rgba(255, 247, 232, 0.9);
  border: 3rpx solid rgba(223, 189, 131, 0.72);
  border-radius: 28rpx;
  box-shadow: 10rpx 12rpx 0 rgba(223, 189, 131, 0.16);
}

.record-summary__tape {
  position: absolute;
  top: -18rpx;
  left: 34rpx;
  width: 64rpx;
  height: 42rpx;
  background: rgba(255, 208, 119, 0.72);
  border-radius: 8rpx;
  transform: rotate(10deg);
}

.record-summary__sun {
  position: absolute;
  top: 40rpx;
  right: 58rpx;
  width: 64rpx;
  height: 64rpx;
  border: 5rpx solid #f4aa23;
  border-radius: 50%;
}

.record-summary__leaf {
  position: absolute;
  right: 18rpx;
  bottom: 30rpx;
  width: 58rpx;
  height: 104rpx;
  border-left: 6rpx solid #7b9a50;
  transform: rotate(28deg);
}

.record-summary__leaf::before,
.record-summary__leaf::after {
  position: absolute;
  left: -4rpx;
  width: 34rpx;
  height: 20rpx;
  content: '';
  background: #9eb469;
  border-radius: 30rpx 4rpx 30rpx 4rpx;
}

.record-summary__leaf::before {
  top: 18rpx;
  transform: rotate(-30deg);
}

.record-summary__leaf::after {
  top: 50rpx;
  transform: rotate(24deg);
}

.record-summary__title {
  display: block;
  margin-bottom: 16rpx;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.2;
}

.record-summary__location {
  display: inline-flex;
  align-items: center;
  height: 54rpx;
  padding: 0 22rpx;
  margin-bottom: 28rpx;
  font-size: 26rpx;
  color: #6b482d;
  background: #fff0bd;
  border: 2rpx solid rgba(223, 189, 131, 0.48);
  border-radius: 999rpx;
}

.record-summary__pin {
  margin-right: 10rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #d94b12;
}

.record-summary__stats {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.record-stat {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 112rpx;
  padding: 16rpx 14rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 2rpx solid rgba(223, 189, 131, 0.42);
  border-radius: 18rpx;
}

.record-stat__icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 48rpx;
  height: 48rpx;
  margin-right: 10rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 14rpx;
}

.record-stat--blue .record-stat__icon {
  background: #73acd3;
}

.record-stat--green .record-stat__icon {
  background: #7b9a50;
}

.record-stat__label {
  display: block;
  margin-bottom: 8rpx;
  font-size: 22rpx;
  font-weight: 800;
}

.record-stat__value {
  display: block;
  font-size: 34rpx;
  font-weight: 900;
  color: #d94b12;
}

.record-stat--blue .record-stat__value {
  color: #2f6f94;
}

.record-stat--green .record-stat__value {
  color: #55753c;
}

.record-stat__unit {
  margin-left: 4rpx;
  font-size: 22rpx;
  color: #4a2f1b;
}

.section-title {
  display: flex;
  align-items: center;
  margin: 26rpx 0 22rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.section-title--growth {
  margin-top: 30rpx;
}

.section-title__camera {
  width: 54rpx;
  height: 38rpx;
  margin-right: 14rpx;
  background: #8a6d54;
  border: 4rpx solid #fff0bd;
  border-radius: 10rpx;
  box-shadow: 0 -8rpx 0 -2rpx #8a6d54;
}

.section-title__line {
  flex: 1;
  height: 2rpx;
  margin: 0 18rpx;
  border-top: 3rpx dashed rgba(244, 170, 35, 0.52);
}

.section-title__star {
  font-size: 24rpx;
  color: #f4aa23;
}

.album-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.album-entry {
  display: grid;
  grid-template-columns: minmax(0, 0.98fr) minmax(0, 1fr);
  gap: 22rpx;
  align-items: center;
}

.album-entry--reverse {
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.98fr);
}

.album-entry--reverse .album-entry__photo {
  order: 2;
}

.album-entry--reverse .album-note {
  order: 1;
}

.album-entry__photo {
  min-width: 0;
}

.album-note {
  position: relative;
  min-width: 0;
  min-height: 228rpx;
  padding: 34rpx 24rpx 24rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 2rpx solid rgba(223, 189, 131, 0.48);
  border-radius: 16rpx;
  box-shadow: 8rpx 8rpx 0 rgba(223, 189, 131, 0.12);
}

.album-note__sticker {
  position: absolute;
  right: 22rpx;
  bottom: 22rpx;
  width: 44rpx;
  height: 44rpx;
  opacity: 0.72;
  border: 4rpx solid #f26a21;
  border-radius: 50% 50% 50% 12rpx;
  transform: rotate(-18deg);
}

.album-note__sticker--green {
  border-color: #7b9a50;
}

.album-note__sticker--blue {
  border-color: #73acd3;
}

.album-note__title {
  display: block;
  margin-bottom: 12rpx;
  font-size: 32rpx;
  font-weight: 900;
  line-height: 1.24;
}

.album-note__dash {
  width: 100%;
  height: 2rpx;
  margin-bottom: 18rpx;
  border-top: 3rpx dashed rgba(223, 189, 131, 0.5);
}

.album-note__description {
  display: block;
  padding-right: 16rpx;
  margin-bottom: 24rpx;
  font-size: 25rpx;
  line-height: 1.55;
  color: #5e3c22;
}

.album-note__date {
  display: block;
  font-size: 23rpx;
  color: #8a6d54;
}

.album-note__source {
  display: inline-flex;
  height: 38rpx;
  padding: 0 14rpx;
  margin-top: 14rpx;
  font-size: 20rpx;
  line-height: 38rpx;
  color: #8a4a21;
  background: #fff0bd;
  border-radius: 999rpx;
}

.dialogue-photo {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 28rpx;
  background:
    radial-gradient(circle at 84% 22%, rgba(255, 250, 240, 0.74) 0 26rpx, transparent 27rpx),
    #dceecb;
}

.dialogue-photo__bubble {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 82rpx;
  height: 66rpx;
  margin-bottom: 18rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #fff;
  background: #7b9a50;
  border-radius: 28rpx 28rpx 28rpx 8rpx;
}

.dialogue-photo__line {
  margin-bottom: 12rpx;
  font-size: 23rpx;
  font-weight: 900;
  color: #55753c;
}

.dialogue-photo__quote {
  font-size: 24rpx;
  line-height: 1.45;
  text-align: center;
}

.growth-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

@media (max-width: 380px) {
  .record-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .record-summary__stats,
  .growth-grid {
    gap: 12rpx;
  }

  .record-stat {
    padding: 14rpx 10rpx;
  }
}

@media (min-width: 431px) {
  .record-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(116px + env(safe-area-inset-bottom));
  }

  .record-header__title {
    font-size: 28px;
  }

  .record-summary__title {
    font-size: 25px;
  }

  .album-note__title,
  .section-title {
    font-size: 19px;
  }

  .album-note__description {
    font-size: 14px;
  }
}
</style>
