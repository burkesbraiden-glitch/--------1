<template>
  <button class="task-card" @click="$emit('select', task)">
    <view class="task-card__thumb" :class="`task-card__thumb--${task.theme}`">
      <view class="task-card__sky"></view>
      <view class="task-card__scene">
        <view v-if="task.theme === 'beasts'" class="task-card__roof">
          <view v-for="item in 5" :key="item" class="task-card__beast"></view>
        </view>
        <view v-else-if="task.theme === 'gate'" class="task-card__gate">
          <view class="task-card__gate-door"></view>
        </view>
        <view v-else class="task-card__story">
          <view class="task-card__person task-card__person--big"></view>
          <view class="task-card__person task-card__person--small"></view>
        </view>
      </view>
    </view>

    <view class="task-card__content">
      <view class="task-card__title-row">
        <view class="task-card__order" :class="{ 'task-card__order--done': task.status === 'completed' }">
          <text>{{ task.order }}</text>
        </view>
        <text class="task-card__title">{{ task.title }}</text>
      </view>
      <text class="task-card__subtitle">{{ task.subtitle }}</text>
    </view>

    <view class="task-card__action">
      <text class="task-card__status" :class="`task-card__status--${task.status}`">{{ statusText }}</text>
      <text class="task-card__arrow">›</text>
    </view>
  </button>
</template>

<script>
const statusMap = {
  'not-started': '未完成',
  'in-progress': '进行中',
  completed: '已完成',
}

export default {
  name: 'TaskCard',
  emits: ['select'],
  props: {
    task: {
      type: Object,
      default: () => ({}),
    },
  },
  computed: {
    statusText() {
      return statusMap[this.task.status] || '未完成'
    },
  },
}
</script>

<style scoped>
.task-card {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 160rpx;
  padding: 18rpx 18rpx;
  text-align: left;
  background: rgba(255, 247, 232, 0.94);
  border: 3rpx solid rgba(223, 189, 131, 0.58);
  border-radius: 28rpx;
  box-shadow: 0 8rpx 18rpx rgba(97, 63, 28, 0.07);
}

.task-card__thumb {
  position: relative;
  flex-shrink: 0;
  width: 156rpx;
  height: 106rpx;
  overflow: hidden;
  background: #cfe7f5;
  border: 3rpx solid rgba(255, 250, 240, 0.8);
  border-radius: 22rpx;
}

.task-card__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 32% 24%, rgba(255, 250, 240, 0.92) 0 24rpx, transparent 25rpx),
    radial-gradient(circle at 58% 20%, rgba(255, 250, 240, 0.72) 0 18rpx, transparent 19rpx),
    #bfe1f5;
}

.task-card__scene {
  position: absolute;
  inset: 0;
}

.task-card__roof {
  position: absolute;
  right: 8rpx;
  bottom: 14rpx;
  left: 8rpx;
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
  height: 42rpx;
  padding: 0 12rpx;
  background: repeating-linear-gradient(90deg, #d28724 0 12rpx, #e6a43a 12rpx 24rpx);
  border-radius: 20rpx 20rpx 8rpx 8rpx;
  transform: rotate(-5deg);
}

.task-card__beast {
  width: 13rpx;
  height: 22rpx;
  margin-top: -18rpx;
  background: #b66b1f;
  border-radius: 12rpx 12rpx 4rpx 4rpx;
}

.task-card__gate {
  position: absolute;
  right: 18rpx;
  bottom: 10rpx;
  left: 18rpx;
  height: 78rpx;
  background: #dc8e28;
  border-radius: 18rpx 18rpx 8rpx 8rpx;
}

.task-card__gate-door {
  position: absolute;
  right: 22rpx;
  bottom: 0;
  left: 22rpx;
  height: 58rpx;
  background:
    radial-gradient(circle at 34% 32%, #e8bd63 0 4rpx, transparent 5rpx),
    radial-gradient(circle at 66% 32%, #e8bd63 0 4rpx, transparent 5rpx),
    radial-gradient(circle at 34% 62%, #e8bd63 0 4rpx, transparent 5rpx),
    radial-gradient(circle at 66% 62%, #e8bd63 0 4rpx, transparent 5rpx),
    #a9472a;
  border-radius: 8rpx 8rpx 0 0;
}

.task-card__story {
  position: absolute;
  right: 10rpx;
  bottom: 8rpx;
  left: 10rpx;
  height: 70rpx;
  background: linear-gradient(0deg, rgba(231, 157, 42, 0.32), rgba(231, 157, 42, 0));
}

.task-card__person {
  position: absolute;
  bottom: 8rpx;
  width: 34rpx;
  height: 48rpx;
  background: #f0ad45;
  border-radius: 18rpx 18rpx 8rpx 8rpx;
}

.task-card__person::before {
  position: absolute;
  top: -20rpx;
  left: 6rpx;
  width: 22rpx;
  height: 22rpx;
  content: '';
  background: #f2c28f;
  border-radius: 50%;
}

.task-card__person--big {
  left: 32rpx;
  height: 56rpx;
  background: #4f87b8;
}

.task-card__person--small {
  left: 76rpx;
  width: 30rpx;
  height: 42rpx;
}

.task-card__order {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 54rpx;
  height: 54rpx;
  margin-right: 14rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border: 3rpx solid rgba(255, 250, 240, 0.88);
  border-radius: 50%;
  box-shadow: 0 6rpx 10rpx rgba(217, 75, 18, 0.2);
}

.task-card__order--done {
  background: #7b9a50;
}

.task-card__content {
  flex: 1;
  min-width: 0;
  padding: 0 12rpx 0 18rpx;
}

.task-card__title-row {
  display: flex;
  align-items: center;
  min-width: 0;
  margin-bottom: 14rpx;
}

.task-card__title {
  display: -webkit-box;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 31rpx;
  font-weight: 900;
  line-height: 1.22;
  color: #4a2f1b;
  overflow-wrap: normal;
  word-break: keep-all;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-card__subtitle {
  display: block;
  overflow: hidden;
  font-size: 24rpx;
  line-height: 1.35;
  color: #6b482d;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__action {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: flex-end;
  width: 154rpx;
}

.task-card__status {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  min-width: 102rpx;
  height: 54rpx;
  padding: 0 16rpx;
  font-size: 24rpx;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  border: 2rpx solid currentColor;
  border-radius: 24rpx;
}

.task-card__status--not-started {
  color: #d94b12;
  background: #fff7e8;
}

.task-card__status--in-progress {
  color: #235b83;
  background: #dfeff8;
}

.task-card__status--completed {
  color: #55753c;
  background: #eef6dc;
}

.task-card__arrow {
  flex-shrink: 0;
  width: 34rpx;
  margin-left: 12rpx;
  font-size: 58rpx;
  font-weight: 500;
  line-height: 1;
  text-align: right;
  color: #6b482d;
}

@media (min-width: 431px) {
  .task-card {
    min-height: 92px;
    padding: 10px 12px;
    border-width: 2px;
    border-radius: 16px;
  }

  .task-card__thumb {
    width: 96px;
    height: 64px;
    border-radius: 12px;
  }

  .task-card__order {
    width: 34px;
    height: 34px;
    margin-right: 8px;
    font-size: 19px;
  }

  .task-card__content {
    padding: 0 8px 0 10px;
  }

  .task-card__title {
    font-size: 18px;
  }

  .task-card__subtitle,
  .task-card__status {
    font-size: 14px;
  }

  .task-card__status {
    min-width: 64px;
    height: 34px;
  }

  .task-card__action {
    width: 86px;
  }
}
</style>
