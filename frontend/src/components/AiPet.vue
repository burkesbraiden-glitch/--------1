<template>
  <view class="ai-pet" :class="[`ai-pet--${pet.mode}`, { 'ai-pet--record': pet.pageContext === 'record' }]">
    <button v-if="pet.mode === 'hidden'" class="ai-pet__edge" @click="pet.peekPet">
      <text>小旅</text>
    </button>

    <view v-else class="ai-pet__body">
      <button class="ai-pet__hide" @click.stop="pet.hidePet">‹</button>
      <button class="ai-pet__avatar" @click="pet.openChat">
        <text class="ai-pet__face">小旅</text>
      </button>
    </view>

    <AiChatSheet />
  </view>
</template>

<script>
import AiChatSheet from './AiChatSheet.vue'
import { usePetStore } from '../stores/pet'

export default {
  name: 'AiPet',
  components: {
    AiChatSheet,
  },
  computed: {
    pet() {
      return usePetStore()
    },
  },
}
</script>

<style scoped>
.ai-pet {
  position: fixed;
  right: 0;
  bottom: calc(132rpx + 92rpx);
  z-index: 70;
}

.ai-pet__body {
  display: flex;
  align-items: center;
  transition: transform 0.2s ease;
}

.ai-pet--peek .ai-pet__body {
  transform: translateX(72rpx);
}

.ai-pet--record.ai-pet--peek .ai-pet__body {
  transform: translateX(88rpx);
}

.ai-pet--open .ai-pet__body {
  transform: translateX(8rpx);
}

.ai-pet__hide {
  width: 44rpx;
  height: 86rpx;
  font-size: 42rpx;
  color: #4a2f1b;
  background: #fff0bd;
  border: 2rpx solid rgba(190, 142, 78, 0.34);
  border-right: 0;
  border-radius: 28rpx 0 0 28rpx;
}

.ai-pet__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 112rpx;
  height: 112rpx;
  color: #2f6f94;
  background: #cfe7f5;
  border: 4rpx solid #fffaf0;
  border-radius: 34rpx 0 0 34rpx;
  box-shadow: 0 10rpx 20rpx rgba(97, 63, 28, 0.16);
}

.ai-pet__face {
  font-size: 26rpx;
  font-weight: 800;
}

.ai-pet__edge {
  width: 34rpx;
  height: 118rpx;
  font-size: 20rpx;
  color: #4a2f1b;
  background: #fff0bd;
  border: 2rpx solid rgba(190, 142, 78, 0.36);
  border-right: 0;
  border-radius: 22rpx 0 0 22rpx;
}
</style>

