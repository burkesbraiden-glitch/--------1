<template>
  <view class="task-detail">
    <view class="task-detail__paper">
      <view class="detail-header">
        <button class="detail-header__back" @click="goBack">‹</button>
        <view class="detail-header__title-wrap">
          <text class="detail-header__spark">任务</text>
          <text class="detail-header__title">任务详情</text>
        </view>
        <button class="detail-header__notice" @click="openPetChat">
          <text>铃</text>
          <view class="detail-header__dot"></view>
        </button>
      </view>

      <view class="detail-hero">
        <view class="detail-hero__copy">
          <text class="detail-hero__title">{{ currentTask.title || '观察任务' }}</text>
          <text class="detail-hero__number">观察任务 {{ formattedOrder }}</text>
          <text class="detail-hero__summary">{{ currentTask.summary || '正在加载任务内容' }}</text>
          <view class="detail-hero__tags">
            <view class="detail-hero__tag detail-hero__tag--orange">
              <text class="detail-hero__tag-icon">包</text>
              <text>{{ currentTask.ageGroup }}岁</text>
            </view>
            <view class="detail-hero__tag detail-hero__tag--blue">
              <text class="detail-hero__tag-icon">时</text>
              <text>{{ currentTask.duration }}</text>
            </view>
            <view class="detail-hero__tag detail-hero__tag--green">
              <text class="detail-hero__tag-icon">看</text>
              <text>{{ currentTask.type }}</text>
            </view>
          </view>
        </view>
        <view class="detail-hero__art">
          <view class="detail-hero__cloud detail-hero__cloud--one"></view>
          <view class="detail-hero__cloud detail-hero__cloud--two"></view>
          <view class="detail-roof">
            <view v-for="item in 7" :key="item" class="detail-roof__beast" :class="{ 'detail-roof__beast--lead': item === 7 }"></view>
          </view>
        </view>
      </view>

      <view class="detail-sections">
        <view v-for="section in detailSections" :key="section.title" class="detail-section">
          <view class="detail-section__icon" :class="`detail-section__icon--${section.theme}`">
            <view class="detail-section__mark"></view>
          </view>
          <view class="detail-section__content">
            <text class="detail-section__title">{{ section.title }}</text>
            <text class="detail-section__text">{{ section.text }}</text>
          </view>
          <text class="detail-section__arrow">›</text>
        </view>
      </view>

      <view class="detail-record">
        <view class="detail-record__head">
          <view>
            <text class="detail-record__title">我的观察记录</text>
            <text class="detail-record__desc">{{ recordHint }}</text>
          </view>
          <text class="detail-record__status">{{ saveStatusText || statusText }}</text>
        </view>

        <view v-if="isPlanReady" class="detail-record__gate">
          <text>开始探索后即可记录这个任务</text>
          <button :disabled="isStartingPlan" @click="startExploration">
            {{ isStartingPlan ? '启动中…' : '开始探索' }}
          </button>
        </view>

        <view v-else-if="isTaskNotStarted" class="detail-record__gate">
          <text>先开始任务，再记录观察发现</text>
          <button :disabled="submissionState.isStarting" @click="startTask">
            {{ submissionState.isStarting ? '开始中…' : '开始任务' }}
          </button>
        </view>

        <button class="detail-record__image-picker" :disabled="!canChooseImage || imageState.isUploading" @click="chooseImage">
          <image v-if="displayImagePath" class="detail-record__image" :src="displayImagePath" mode="aspectFill" />
          <view v-else-if="imageState.isUploading" class="detail-record__empty">
            <text>正在上传图片...</text>
          </view>
          <view v-else-if="imageState.loading" class="detail-record__empty">
            <text>正在加载图片...</text>
          </view>
          <view v-else class="detail-record__empty">
            <view class="detail-record__camera"></view>
            <text>拍照 / 选择照片</text>
          </view>
        </button>
        <button v-if="currentTask.record?.imageUrl && imageState.error && !imageState.isUploading" class="detail-record__image-retry" @click="retryTaskImage">
          图片加载失败，点击重试
        </button>

        <textarea
          class="detail-record__note"
          :value="noteDraft"
          :disabled="!canEditNote"
          maxlength="2000"
          placeholder="写一句孩子发现的细节"
          @input="updateNote"
          @blur="handleNoteBlur"
        />
      </view>

      <view class="detail-actions">
        <button class="detail-actions__back" @click="goTaskList">返回任务列表</button>
        <button
          class="detail-actions__complete"
          :class="{ 'detail-actions__complete--done': currentTask.status === 'completed' }"
          :disabled="!canComplete || submissionState.isCompleting"
          @click="completeTask"
        >
          {{ currentTask.status === 'completed' ? '已完成' : (submissionState.isCompleting ? '保存中…' : '标记为完成') }}
        </button>
      </view>
    </view>

    <AiPet />
    <AppTabbar active="tasks" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { usePetStore } from '../../stores/pet'
import { usePlanStore } from '../../stores/plan'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'

const statusMap = {
  'not-started': '未完成',
  'in-progress': '进行中',
  completed: '已完成',
}

export default {
  components: {
    AiPet,
    AppTabbar,
  },
  data() {
    return {
      routeTaskId: '',
      pendingPreviewPath: '',
      noteDraft: '',
      noteSaveTimer: null,
      noteSavePromise: null,
      noteRevision: 0,
      noteHasLocalEdits: false,
      isStartingPlan: false,
    }
  },
  computed: {
    task() {
      return useTaskStore()
    },
    plan() {
      return usePlanStore()
    },
    user() {
      return useUserStore()
    },
    currentTask() {
      return this.task.currentTask || {}
    },
    formattedOrder() {
      return String(this.currentTask.order || 1).padStart(2, '0')
    },
    statusText() {
      return statusMap[this.currentTask.status] || '未完成'
    },
    isPlanReady() {
      return this.plan.currentPlan?.status === 'ready'
    },
    isTaskNotStarted() {
      return this.currentTask.status === 'not-started'
    },
    canEditNote() {
      return this.plan.currentPlan?.status === 'in-progress' && !this.isTaskNotStarted && !this.submissionState.isCompleting
    },
    canChooseImage() {
      return this.plan.currentPlan?.status === 'in-progress' && !this.isTaskNotStarted
    },
    imageState() {
      return this.currentTask.id ? this.task.imageStateForTask(this.currentTask.id) : {}
    },
    displayImagePath() {
      return this.pendingPreviewPath || this.currentTask.record?.displayImagePath || ''
    },
    canComplete() {
      return this.canEditNote && this.currentTask.status !== 'completed'
    },
    submissionState() {
      return this.currentTask.id ? this.task.submissionStateForTask(this.currentTask.id) : {}
    },
    saveStatusText() {
      if (!this.canEditNote) {
        return ''
      }
      if (this.submissionState.isSaving) {
        return '正在保存…'
      }
      return this.noteHasLocalEdits ? '待保存' : '已保存'
    },
    recordHint() {
      if (this.isPlanReady) {
        return '开始探索后即可写下新的发现'
      }
      if (this.isTaskNotStarted) {
        return '开始任务后即可记录照片和发现'
      }
      return '文字会同步到这次探索记录里'
    },
    detailSections() {
      return [
        {
          title: '任务目标',
          text: this.currentTask.objective,
          theme: 'target',
        },
        {
          title: '怎么做',
          text: this.formatListText(this.currentTask.steps),
          theme: 'child',
        },
        {
          title: '提示问题',
          text: this.formatListText(this.currentTask.questions),
          theme: 'question',
        },
        {
          title: '记录方式',
          text: this.currentTask.recordMode,
          theme: 'camera',
        },
      ]
    },
  },
  onLoad(options) {
    this.routeTaskId = options?.id || ''
    this.task.setCurrentTask(this.routeTaskId)
    this.restoreRecord()
  },
    async onShow() {
      await this.restorePlanAndTasks()
      const task = await this.recoverCurrentTask()
      usePetStore().setPageContext('task-detail', task?.id)
      this.restoreRecord()
      await this.restoreTaskImage()
  },
  onHide() {
    this.flushNoteSave()
  },
  onUnload() {
    this.flushNoteSave()
  },
  methods: {
    formatListText(value) {
      return Array.isArray(value) ? value.join('；') : value
    },
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
    async recoverCurrentTask() {
      let task = await this.task.ensureCurrentTask(this.routeTaskId)
      if (!task && this.plan.currentPlan?.id && this.routeTaskId) {
        task = await this.task.fetchTaskDetail(this.plan.currentPlan.id, this.routeTaskId)
      }
      return task
    },
    restoreRecord() {
      if (!this.noteHasLocalEdits) {
        this.noteDraft = this.currentTask.record?.note || ''
      }
    },
    async restoreTaskImage() {
      if (!this.currentTask.id || !this.currentTask.record?.imageUrl) {
        return null
      }
      try {
        return await this.task.ensureTaskImageDisplay(this.currentTask.id)
      } catch (error) {
        return null
      }
    },
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    taskErrorText(error, fallback = '操作失败，请稍后重试') {
      const messages = {
        PLAN_NOT_FOUND: '没有找到这次探索计划',
        PLAN_NOT_READY: '这次探索暂时不能开始',
        PLAN_NOT_STARTED: '请先开始探索再记录任务',
        PLAN_ALREADY_COMPLETED: '这次探索已经结束了',
        TASK_NOT_FOUND: '没有找到这个任务，请返回任务列表重试',
        TASK_ALREADY_COMPLETED: '这个任务已经完成了',
        IMAGE_REQUIRED: '请选择图片',
        IMAGE_TOO_LARGE: '图片过大，请选择较小的图片',
        UNSUPPORTED_IMAGE_TYPE: '仅支持 JPG、PNG 或 WebP 图片',
        TASK_IMAGE_NOT_FOUND: '暂未找到任务图片',
        VALIDATION_ERROR: '记录内容不符合要求，请检查后重试',
        UNAUTHORIZED: '登录状态已失效，请重新登录',
        TOKEN_EXPIRED: '登录状态已失效，请重新登录',
        INVALID_TOKEN: '登录状态已失效，请重新登录',
        NETWORK_ERROR: '网络连接失败，请稍后重试',
      }
      return messages[error?.code] || fallback
    },
    async startExploration() {
      if (this.isStartingPlan || !this.plan.currentPlan) {
        return
      }
      this.isStartingPlan = true
      try {
        const startedPlan = await this.plan.startExploration(this.plan.currentPlan.id, this.user.userInfo?.id)
        await this.task.ensureTasks(startedPlan.id, startedPlan.status)
        this.showToast('探索已开始，可以记录任务了')
      } catch (error) {
        this.showToast(this.taskErrorText(error, '无法开始探索，请稍后重试'))
      } finally {
        this.isStartingPlan = false
      }
    },
    async startTask() {
      if (!this.currentTask.id || this.submissionState.isStarting || this.currentTask.status === 'completed') {
        return
      }
      try {
        const task = await this.task.startTaskSubmission(this.currentTask.id)
        if (task && !this.noteHasLocalEdits) {
          this.noteDraft = task.record?.note || ''
        }
      } catch (error) {
        this.showToast(this.taskErrorText(error, '任务开始失败，请稍后重试'))
      }
    },
    chooseImage() {
      if (!this.canChooseImage) {
        this.showToast(this.isPlanReady ? '请先开始探索' : '请先开始任务')
        return
      }
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const pendingPreviewPath = res.tempFilePaths?.[0] || ''
          if (!pendingPreviewPath) {
            return
          }
          this.uploadSelectedImage(pendingPreviewPath)
        },
      })
    },
    async uploadSelectedImage(pendingPreviewPath) {
      if (!this.currentTask.id || this.imageState.isUploading) {
        return
      }
      this.pendingPreviewPath = pendingPreviewPath
      try {
        await this.task.uploadTaskImage(this.currentTask.id, pendingPreviewPath)
        this.showToast('图片上传成功')
      } catch (error) {
        this.showToast(this.taskErrorText(error, '图片上传失败，请重试'))
      } finally {
        this.pendingPreviewPath = ''
      }
    },
    async retryTaskImage() {
      if (!this.currentTask.id) {
        return
      }
      try {
        await this.task.ensureTaskImageDisplay(this.currentTask.id, { force: true })
      } catch (error) {
        this.showToast(this.taskErrorText(error, '图片加载失败，请重试'))
      }
    },
    updateNote(event) {
      if (!this.canEditNote) {
        return
      }
      this.noteDraft = event.detail.value
      this.noteRevision += 1
      this.noteHasLocalEdits = true
      this.scheduleNoteSave()
    },
    scheduleNoteSave() {
      if (this.noteSaveTimer) {
        clearTimeout(this.noteSaveTimer)
      }
      this.noteSaveTimer = setTimeout(() => {
        this.noteSaveTimer = null
        this.saveNoteNow()
      }, 600)
    },
    async saveNoteNow() {
      if (!this.canEditNote || !this.currentTask.id || !this.noteHasLocalEdits) {
        return null
      }
      const revision = this.noteRevision
      const note = this.noteDraft
      const promise = this.task.saveTaskNote(this.currentTask.id, note)
      this.noteSavePromise = promise
      try {
        const task = await promise
        if (revision === this.noteRevision) {
          this.noteHasLocalEdits = false
        }
        return task
      } catch (error) {
        this.showToast(this.taskErrorText(error, '记录保存失败，请重试'))
        return null
      } finally {
        if (this.noteSavePromise === promise) {
          this.noteSavePromise = null
        }
      }
    },
    async flushNoteSave() {
      if (this.noteSaveTimer) {
        clearTimeout(this.noteSaveTimer)
        this.noteSaveTimer = null
      }
      if (this.noteSavePromise) {
        await this.noteSavePromise
      }
      if (this.noteHasLocalEdits) {
        return this.saveNoteNow()
      }
      return null
    },
    async handleNoteBlur() {
      await this.flushNoteSave()
    },
    async completeTask() {
      if (!this.canComplete || !this.currentTask.id || this.submissionState.isCompleting) {
        return
      }
      await this.flushNoteSave()
      try {
        const task = await this.task.completeTaskSubmission(this.currentTask.id, this.noteDraft)
        if (task) {
          this.noteDraft = task.record?.note || ''
          this.noteHasLocalEdits = false
        }
      } catch (error) {
        this.showToast(this.taskErrorText(error, '任务完成失败，请稍后重试'))
      }
    },
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('task-detail', this.currentTask.id)
      petStore.openChat()
    },
    goBack() {
      uni.navigateBack({
        fail: () => {
          this.goTaskList()
        },
      })
    },
    goTaskList() {
      uni.reLaunch({
        url: '/pages/tasks/index',
      })
    },
  },
}
</script>

<style scoped>
.task-detail {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.48) 0, rgba(255, 240, 189, 0) 112rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.task-detail__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(28rpx + env(safe-area-inset-top)) 34rpx calc(190rpx + env(safe-area-inset-bottom));
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

.detail-header__back,
.detail-header__notice {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.detail-header__back {
  font-size: 64rpx;
}

.detail-header__notice {
  position: relative;
  font-size: 24rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.detail-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.detail-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.detail-header__spark {
  position: absolute;
  top: -22rpx;
  left: 94rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #f4aa23;
  transform: rotate(-20deg);
}

.detail-header__title {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
}

.detail-hero {
  position: relative;
  min-height: 382rpx;
  margin-bottom: 22rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 4rpx solid rgba(223, 189, 131, 0.62);
  border-radius: 34rpx;
  box-shadow: 0 16rpx 28rpx rgba(97, 63, 28, 0.1);
}

.detail-hero__copy {
  position: relative;
  z-index: 2;
  width: 56%;
  padding: 58rpx 0 28rpx 28rpx;
}

.detail-hero__title {
  display: block;
  margin-bottom: 18rpx;
  font-size: 46rpx;
  font-weight: 900;
  line-height: 1.12;
}

.detail-hero__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 48rpx;
  padding: 0 20rpx;
  margin-bottom: 26rpx;
  font-size: 25rpx;
  font-weight: 800;
  color: #8a4a21;
  background: rgba(255, 250, 240, 0.72);
  border: 2rpx solid rgba(223, 189, 131, 0.56);
  border-radius: 999rpx;
}

.detail-hero__summary {
  display: block;
  margin-bottom: 34rpx;
  font-size: 28rpx;
  line-height: 1.65;
  color: #5e3c22;
}

.detail-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.detail-hero__tag {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 58rpx;
  padding: 0 18rpx;
  font-size: 24rpx;
  font-weight: 800;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 22rpx;
}

.detail-hero__tag-icon {
  margin-right: 8rpx;
  font-size: 20rpx;
}

.detail-hero__tag--orange {
  color: #d94b12;
  background: #fff1d8;
}

.detail-hero__tag--blue {
  color: #235b83;
  background: #dfeff8;
}

.detail-hero__tag--green {
  color: #55753c;
  background: #eef6dc;
}

.detail-hero__art {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 58%;
  background: #bfe1f5;
}

.detail-hero__cloud {
  position: absolute;
  height: 32rpx;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 999rpx;
}

.detail-hero__cloud--one {
  top: 66rpx;
  left: 34rpx;
  width: 158rpx;
}

.detail-hero__cloud--two {
  top: 122rpx;
  right: 26rpx;
  width: 96rpx;
}

.detail-roof {
  position: absolute;
  right: -12rpx;
  bottom: 72rpx;
  display: flex;
  gap: 14rpx;
  align-items: flex-start;
  width: 380rpx;
  height: 86rpx;
  padding: 0 32rpx;
  background: repeating-linear-gradient(90deg, #d28724 0 18rpx, #e7a33b 18rpx 36rpx);
  border: 5rpx solid rgba(126, 82, 35, 0.22);
  border-radius: 50rpx 50rpx 18rpx 18rpx;
  transform: rotate(-13deg);
}

.detail-roof__beast {
  width: 18rpx;
  height: 36rpx;
  margin-top: -28rpx;
  background: #b66b1f;
  border-radius: 16rpx 16rpx 5rpx 5rpx;
}

.detail-roof__beast--lead {
  width: 34rpx;
  height: 58rpx;
  margin-top: -48rpx;
  border-radius: 22rpx 22rpx 8rpx 8rpx;
}

.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.detail-section {
  display: flex;
  align-items: center;
  min-height: 124rpx;
  padding: 18rpx 24rpx;
  background: rgba(255, 250, 240, 0.84);
  border: 3rpx solid rgba(223, 189, 131, 0.54);
  border-radius: 26rpx;
}

.detail-section__icon {
  position: relative;
  flex-shrink: 0;
  width: 76rpx;
  height: 76rpx;
  margin-right: 24rpx;
  background: #fff0bd;
  border: 3rpx solid rgba(223, 189, 131, 0.54);
  border-radius: 50%;
}

.detail-section__mark {
  position: absolute;
  top: 20rpx;
  left: 20rpx;
  width: 30rpx;
  height: 30rpx;
  border-radius: 50%;
}

.detail-section__icon--target .detail-section__mark {
  background: #f26a21;
  border: 8rpx solid #fff7e8;
}

.detail-section__icon--child .detail-section__mark {
  background: #f0ad45;
  border-radius: 16rpx 16rpx 8rpx 8rpx;
}

.detail-section__icon--question .detail-section__mark {
  background: #7bb8d6;
}

.detail-section__icon--camera .detail-section__mark {
  background: #4a2f1b;
  border-radius: 8rpx;
}

.detail-section__content {
  flex: 1;
  min-width: 0;
}

.detail-section__title {
  display: block;
  margin-bottom: 8rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.detail-section__text {
  display: block;
  font-size: 26rpx;
  line-height: 1.38;
  color: #5e3c22;
}

.detail-section__arrow {
  flex-shrink: 0;
  margin-left: 18rpx;
  font-size: 58rpx;
  color: #6b482d;
}

.detail-record {
  margin-bottom: 24rpx;
  padding: 22rpx;
  background: rgba(255, 247, 232, 0.94);
  border: 3rpx dashed rgba(223, 189, 131, 0.66);
  border-radius: 28rpx;
}

.detail-record__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.detail-record__title {
  display: block;
  margin-bottom: 8rpx;
  font-size: 32rpx;
  font-weight: 900;
}

.detail-record__desc {
  display: block;
  font-size: 23rpx;
  color: #8a6d54;
}

.detail-record__status {
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  font-size: 24rpx;
  font-weight: 800;
  color: #d94b12;
  background: #fff1d8;
  border-radius: 999rpx;
}

.detail-record__gate {
  display: flex;
  gap: 16rpx;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
  padding: 16rpx;
  font-size: 25rpx;
  font-weight: 800;
  color: #55753c;
  background: #eef6dc;
  border: 2rpx dashed rgba(123, 154, 80, 0.56);
  border-radius: 18rpx;
}

.detail-record__gate text {
  flex: 1;
  min-width: 0;
}

.detail-record__gate button {
  flex-shrink: 0;
  height: 58rpx;
  padding: 0 20rpx;
  font-size: 24rpx;
  font-weight: 900;
  line-height: 58rpx;
  color: #fff;
  background: #7b9a50;
  border-radius: 18rpx;
}

.detail-record__image-picker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 210rpx;
  margin-bottom: 18rpx;
  overflow: hidden;
  color: #6b482d;
  background: rgba(255, 250, 240, 0.86);
  border: 2rpx solid rgba(223, 189, 131, 0.52);
  border-radius: 22rpx;
}

.detail-record__image {
  width: 100%;
  height: 100%;
}

.detail-record__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  font-size: 26rpx;
  font-weight: 800;
}

.detail-record__camera {
  width: 70rpx;
  height: 48rpx;
  background: #8a6d54;
  border-radius: 12rpx;
}

.detail-record__note {
  width: 100%;
  min-height: 132rpx;
  padding: 18rpx 20rpx;
  font-size: 27rpx;
  line-height: 1.45;
  color: #4a2f1b;
  background: rgba(255, 250, 240, 0.9);
  border: 2rpx solid rgba(223, 189, 131, 0.52);
  border-radius: 22rpx;
}

.detail-record__image-picker[disabled],
.detail-record__note[disabled],
.detail-actions__complete[disabled] {
  opacity: 0.58;
}

.detail-actions {
  display: grid;
  grid-template-columns: 1fr 1.14fr;
  gap: 24rpx;
}

.detail-actions__back,
.detail-actions__complete {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 86rpx;
  font-size: 31rpx;
  font-weight: 900;
  border-radius: 28rpx;
}

.detail-actions__back {
  color: #4a2f1b;
  background: rgba(255, 250, 240, 0.78);
  border: 3rpx solid #dfbd83;
}

.detail-actions__complete {
  color: #fff;
  background: #f26a21;
  box-shadow: 0 14rpx 18rpx rgba(217, 75, 18, 0.2);
}

.detail-actions__complete--done {
  background: #7b9a50;
  box-shadow: 0 14rpx 18rpx rgba(85, 117, 60, 0.18);
}

@media (min-width: 431px) {
  .task-detail__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(116px + env(safe-area-inset-bottom));
  }

  .detail-header {
    margin-bottom: 16px;
  }

  .detail-header__title {
    font-size: 28px;
  }

  .detail-hero {
    min-height: 218px;
    border-width: 2px;
    border-radius: 20px;
  }

  .detail-hero__title {
    font-size: 26px;
  }

  .detail-section__title,
  .detail-record__title {
    font-size: 18px;
  }

  .detail-section__text,
  .detail-record__note {
    font-size: 15px;
  }
}
</style>
