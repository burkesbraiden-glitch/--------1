<template>
  <view class="polaroid-card" :style="cardStyle">
    <view class="polaroid-card__tape" :class="`polaroid-card__tape--${tapeTheme}`"></view>
    <view class="polaroid-card__photo">
      <image
        v-if="shouldShowImage"
        class="polaroid-card__image"
        :src="imagePath"
        mode="aspectFill"
        @error="handleImageError"
      />
      <slot v-else name="photo">
        <view class="polaroid-card__placeholder" :class="`polaroid-card__placeholder--${placeholderTheme}`">
          <view class="polaroid-card__sky"></view>
          <view class="polaroid-card__sun"></view>
          <view class="polaroid-card__hill polaroid-card__hill--back"></view>
          <view class="polaroid-card__hill polaroid-card__hill--front"></view>
        </view>
      </slot>
    </view>
    <text v-if="title" class="polaroid-card__title">{{ title }}</text>
    <text v-if="description" class="polaroid-card__description">{{ description }}</text>
    <text v-if="dateLabel || caption" class="polaroid-card__caption">{{ dateLabel || caption }}</text>
  </view>
</template>

<script>
export default {
  name: 'PolaroidCard',
  props: {
    caption: {
      type: String,
      default: '',
    },
    dateLabel: {
      type: String,
      default: '',
    },
    description: {
      type: String,
      default: '',
    },
    imagePath: {
      type: String,
      default: '',
    },
    placeholderTheme: {
      type: String,
      default: 'roof',
    },
    rotation: {
      type: [Number, String],
      default: 0,
    },
    tapeTheme: {
      type: String,
      default: 'green',
    },
    title: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      imageFailed: false,
    }
  },
  computed: {
    shouldShowImage() {
      return Boolean(this.imagePath && !this.imageFailed)
    },
    cardStyle() {
      return `transform: rotate(${Number(this.rotation) || 0}deg);`
    },
  },
  watch: {
    imagePath() {
      this.imageFailed = false
    },
  },
  methods: {
    handleImageError() {
      this.imageFailed = true
    },
  },
}
</script>

<style scoped>
.polaroid-card {
  position: relative;
  padding: 16rpx 16rpx 26rpx;
  background: #fffaf0;
  border: 2rpx solid rgba(190, 142, 78, 0.3);
  border-radius: 12rpx;
  box-shadow: 0 10rpx 20rpx rgba(97, 63, 28, 0.12);
  transform-origin: center;
}

.polaroid-card__photo {
  position: relative;
  height: 248rpx;
  overflow: hidden;
  background: #cfe7f5;
  border-radius: 8rpx;
}

.polaroid-card__image {
  width: 100%;
  height: 100%;
}

.polaroid-card__placeholder {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #cfe7f5;
}

.polaroid-card__placeholder--gate {
  background: #f1c68b;
}

.polaroid-card__placeholder--dialogue {
  background: #dceecb;
}

.polaroid-card__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 24%, rgba(255, 250, 240, 0.92) 0 22rpx, transparent 23rpx),
    radial-gradient(circle at 32% 20%, rgba(255, 250, 240, 0.82) 0 30rpx, transparent 31rpx),
    linear-gradient(180deg, rgba(255, 250, 240, 0.2), transparent);
}

.polaroid-card__sun {
  position: absolute;
  top: 28rpx;
  right: 34rpx;
  width: 48rpx;
  height: 48rpx;
  background: #fff0bd;
  border: 4rpx solid rgba(244, 170, 35, 0.56);
  border-radius: 50%;
}

.polaroid-card__hill {
  position: absolute;
  right: -30rpx;
  bottom: -34rpx;
  left: -30rpx;
  height: 132rpx;
  border-radius: 50% 50% 0 0;
}

.polaroid-card__hill--back {
  bottom: 12rpx;
  background: rgba(123, 154, 80, 0.46);
}

.polaroid-card__hill--front {
  background: rgba(210, 135, 36, 0.72);
}

.polaroid-card__tape {
  position: absolute;
  top: -20rpx;
  left: 22rpx;
  z-index: 2;
  width: 96rpx;
  height: 42rpx;
  opacity: 0.82;
  border-radius: 8rpx;
  transform: rotate(-8deg);
}

.polaroid-card__tape--green {
  background: rgba(194, 209, 129, 0.74);
}

.polaroid-card__tape--pink {
  background: rgba(245, 151, 132, 0.62);
}

.polaroid-card__tape--blue {
  background: rgba(115, 172, 211, 0.62);
}

.polaroid-card__title {
  display: block;
  margin-top: 18rpx;
  font-size: 30rpx;
  font-weight: 900;
  line-height: 1.25;
  color: #4a2f1b;
}

.polaroid-card__description {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: #5e3c22;
}

.polaroid-card__caption {
  display: block;
  margin-top: 16rpx;
  font-size: 24rpx;
  color: #8a6d54;
}
</style>

