<template>
  <view v-if="pet.chatOpen" class="ai-sheet">
    <view class="ai-sheet__mask" @click="pet.closeChat"></view>
    <view class="ai-sheet__panel">
      <view class="ai-sheet__header">
        <view>
          <text class="ai-sheet__name">小旅</text>
          <text class="ai-sheet__desc">陪你把旅行变成探索</text>
        </view>
        <button class="ai-sheet__close" @click="pet.closeChat">关闭</button>
      </view>

      <view class="ai-sheet__suggestions">
        <button
          v-for="suggestion in suggestions"
          :key="suggestion"
          class="ai-sheet__chip"
          @click="useSuggestion(suggestion)"
        >
          {{ suggestion }}
        </button>
      </view>

      <scroll-view scroll-y class="ai-sheet__messages">
        <view v-for="message in messages" :key="message.id" class="ai-sheet__message" :class="`ai-sheet__message--${message.role}`">
          <text>{{ message.text }}</text>
        </view>
      </scroll-view>

      <view class="ai-sheet__input">
        <input v-model="draft" placeholder="问问小旅" confirm-type="send" @confirm="send" />
        <button @click="send">发送</button>
      </view>
    </view>
  </view>
</template>

<script>
import { getMockAiReply, getMockAiSuggestions } from '../mock/ai'
import { usePetStore } from '../stores/pet'

export default {
  name: 'AiChatSheet',
  data() {
    return {
      draft: '',
      messages: [
        {
          id: 1,
          role: 'pet',
          text: '我是小旅，当前先用 Mock 对话陪你测试探索流程。',
        },
      ],
    }
  },
  computed: {
    pet() {
      return usePetStore()
    },
    suggestions() {
      return getMockAiSuggestions(this.pet.pageContext)
    },
  },
  methods: {
    useSuggestion(text) {
      this.draft = text
      this.send()
    },
    send() {
      const text = this.draft.trim()
      if (!text) {
        return
      }

      this.messages.push({
        id: Date.now(),
        role: 'user',
        text,
      })
      this.messages.push({
        id: Date.now() + 1,
        role: 'pet',
        text: getMockAiReply(text, this.pet.pageContext),
      })
      this.draft = ''
    },
  },
}
</script>

<style scoped>
.ai-sheet {
  position: fixed;
  inset: 0;
  z-index: 90;
}

.ai-sheet__mask {
  position: absolute;
  inset: 0;
  background: rgba(74, 47, 27, 0.24);
}

.ai-sheet__panel {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 28rpx 30rpx calc(28rpx + env(safe-area-inset-bottom));
  background: #fff7e8;
  border: 2rpx solid rgba(190, 142, 78, 0.34);
  border-radius: 36rpx 36rpx 0 0;
}

.ai-sheet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.ai-sheet__name {
  display: block;
  font-size: 34rpx;
  font-weight: 800;
  color: #4a2f1b;
}

.ai-sheet__desc {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #8a6d54;
}

.ai-sheet__close {
  padding: 14rpx 20rpx;
  font-size: 24rpx;
  color: #8a6d54;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 999rpx;
}

.ai-sheet__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  margin-bottom: 18rpx;
}

.ai-sheet__chip {
  padding: 14rpx 18rpx;
  font-size: 24rpx;
  color: #d94b12;
  background: #fff0bd;
  border: 2rpx solid rgba(242, 106, 33, 0.24);
  border-radius: 999rpx;
}

.ai-sheet__messages {
  height: 240rpx;
  padding: 12rpx 0;
}

.ai-sheet__message {
  max-width: 82%;
  padding: 16rpx 18rpx;
  margin-bottom: 14rpx;
  font-size: 25rpx;
  line-height: 1.5;
  border-radius: 20rpx;
}

.ai-sheet__message--pet {
  color: #4a2f1b;
  background: #cfe7f5;
}

.ai-sheet__message--user {
  margin-left: auto;
  color: #fff;
  background: #f26a21;
}

.ai-sheet__input {
  display: flex;
  gap: 14rpx;
  align-items: center;
  padding-top: 12rpx;
}

.ai-sheet__input input {
  flex: 1;
  height: 72rpx;
  padding: 0 22rpx;
  font-size: 26rpx;
  color: #4a2f1b;
  background: #fffaf0;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 999rpx;
}

.ai-sheet__input button {
  width: 104rpx;
  height: 72rpx;
  font-size: 26rpx;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}
</style>

