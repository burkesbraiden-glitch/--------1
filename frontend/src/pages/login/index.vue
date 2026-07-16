<template>
  <view class="login-page">
    <view class="login-page__top">
      <text class="login-page__time">9:41</text>
      <text class="login-page__notice">铃</text>
    </view>

    <view class="login-page__header">
      <text class="login-page__title">我的</text>
      <text class="login-page__brand">童旅记</text>
    </view>

    <view class="login-page__scene">
      <view class="login-page__leaf">叶</view>
      <view class="login-page__family">
        <view class="login-page__adult">家长</view>
        <view class="login-page__child">孩子</view>
        <view class="login-page__bot">小旅</view>
      </view>
      <view class="login-page__palace">故宫</view>
      <view class="login-page__book">探索手册</view>
    </view>

    <view class="login-page__copy">
      <text class="login-page__headline">登录后记录孩子的每一次成长</text>
      <text class="login-page__subtitle">保存探索计划、任务进度和珍贵的学习记录</text>
    </view>

    <view class="login-page__form">
      <view class="login-page__field">
        <text class="login-page__field-label">手机号码</text>
        <input v-model="phone" type="number" maxlength="11" placeholder="请输入手机号码" />
      </view>

      <view class="login-page__field login-page__field--code">
        <view class="login-page__code-input">
          <text class="login-page__field-label">验证码</text>
          <input v-model="code" type="number" maxlength="6" placeholder="请输入验证码" />
        </view>
        <button class="login-page__code-button" :disabled="countdown > 0 || isSendingCode" @click="requestCode">
          {{ countdown > 0 ? `${countdown}s` : isSendingCode ? '发送中' : '获取验证码' }}
        </button>
      </view>

      <button class="login-page__primary" :disabled="isPhoneLoggingIn" @click="submitPhoneLogin">
        <text class="login-page__button-icon">机</text>
        <text>{{ isPhoneLoggingIn ? '登录中' : '手机号登录' }}</text>
      </button>

      <button class="login-page__wechat" :disabled="isWechatLoggingIn" @click="submitWechatLogin">
        <text class="login-page__wechat-icon">微</text>
        <text>{{ isWechatLoggingIn ? '登录中' : '微信登录' }}</text>
      </button>

      <button class="login-page__agreement" @click="agreed = !agreed">
        <text class="login-page__check" :class="{ 'login-page__check--active': agreed }">{{ agreed ? '✓' : '' }}</text>
        <text>我已阅读并同意</text>
        <text class="login-page__link">《用户协议》</text>
        <text>和</text>
        <text class="login-page__link">《隐私政策》</text>
      </button>
    </view>

    <view class="login-page__value-card">
      <view class="login-page__value-title">
        <text>登录后你可以</text>
      </view>
      <view class="login-page__values">
        <view v-for="item in values" :key="item.title" class="login-page__value">
          <view class="login-page__value-art">{{ item.icon }}</view>
          <text class="login-page__value-name">{{ item.title }}</text>
          <text class="login-page__value-desc">{{ item.desc }}</text>
        </view>
      </view>
    </view>

    <AiPet />
    <AppTabbar active="profile" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { usePetStore } from '../../stores/pet'
import { useUserStore } from '../../stores/user'

export default {
  components: {
    AiPet,
    AppTabbar,
  },
  data() {
    return {
      phone: '',
      code: '',
      agreed: false,
      countdown: 0,
      countdownTimer: null,
      isSendingCode: false,
      isPhoneLoggingIn: false,
      isWechatLoggingIn: false,
      values: [
        { title: '同步探索计划', desc: '随时查看和继续探索', icon: '图' },
        { title: '保存学习记录', desc: '珍藏每一次学习收获', icon: '册' },
        { title: '获得成长徽章', desc: '见证孩子的点滴进步', icon: '章' },
      ],
    }
  },
  computed: {
    user() {
      return useUserStore()
    },
  },
  async onShow() {
    usePetStore().setPageContext('login')
    const restored = await this.user.restoreSession()
    if (restored && this.user.isLoggedIn) {
      uni.reLaunch({
        url: '/pages/profile/index',
      })
    }
  },
  onUnload() {
    this.clearCountdown()
  },
  beforeUnmount() {
    this.clearCountdown()
  },
  methods: {
    mapAuthError(error) {
      const messages = {
        NETWORK_ERROR: '无法连接服务器，请确认后端已启动',
        VALIDATION_ERROR: '请检查输入信息',
        INVALID_PHONE: '手机号格式不正确',
        INVALID_VERIFICATION_CODE: '验证码不正确',
        SMS_NOT_CONFIGURED: '短信服务暂未配置',
        UNAUTHORIZED: '登录状态已失效，请重新登录',
      }
      return messages[error?.code] || error?.message || '操作失败，请稍后再试'
    },
    validatePhoneOnly() {
      const phone = this.phone.trim()
      if (!phone) {
        uni.showToast({
          title: '请输入手机号码',
          icon: 'none',
        })
        return false
      }

      if (!/^1[3-9]\d{9}$/.test(phone)) {
        uni.showToast({
          title: '手机号格式不正确',
          icon: 'none',
        })
        return false
      }

      return true
    },
    async requestCode() {
      if (this.countdown > 0 || this.isSendingCode) {
        return
      }

      if (!this.validatePhoneOnly()) {
        return
      }

      this.isSendingCode = true
      try {
        const data = await this.user.requestLoginCode(this.phone.trim())
        this.countdown = data.cooldownSeconds || 60
        this.clearCountdown()
        this.countdownTimer = setInterval(() => {
          this.countdown -= 1
          if (this.countdown <= 0) {
            this.clearCountdown()
          }
        }, 1000)

        uni.showToast({
          title: '验证码已发送',
          icon: 'none',
        })
      } catch (error) {
        uni.showToast({
          title: this.mapAuthError(error),
          icon: 'none',
        })
      } finally {
        this.isSendingCode = false
      }
    },
    clearCountdown() {
      if (this.countdownTimer) {
        clearInterval(this.countdownTimer)
        this.countdownTimer = null
      }
      if (this.countdown < 0) {
        this.countdown = 0
      }
    },
    validateAgreement() {
      if (!this.agreed) {
        uni.showToast({
          title: '请先勾选用户协议',
          icon: 'none',
        })
        return false
      }

      return true
    },
    validatePhoneLogin() {
      const phone = this.phone.trim()
      const code = this.code.trim()

      if (!this.validatePhoneOnly()) {
        return false
      }

      if (!code) {
        uni.showToast({
          title: '请输入验证码',
          icon: 'none',
        })
        return false
      }

      return this.validateAgreement()
    },
    goProfile() {
      uni.reLaunch({
        url: '/pages/profile/index',
      })
    },
    async submitPhoneLogin() {
      if (this.isPhoneLoggingIn || !this.validatePhoneLogin()) {
        return
      }

      this.isPhoneLoggingIn = true
      try {
        await this.user.loginWithPhone(this.phone.trim(), this.code.trim())
        this.goProfile()
      } catch (error) {
        uni.showToast({
          title: this.mapAuthError(error),
          icon: 'none',
        })
      } finally {
        this.isPhoneLoggingIn = false
      }
    },
    async submitWechatLogin() {
      if (this.isWechatLoggingIn || !this.validateAgreement()) {
        return
      }

      this.isWechatLoggingIn = true
      try {
        await this.user.loginWithWechat('tonglvji-h5-dev')
        this.goProfile()
      } catch (error) {
        uni.showToast({
          title: this.mapAuthError(error),
          icon: 'none',
        })
      } finally {
        this.isWechatLoggingIn = false
      }
    },
  },
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 40rpx 44rpx calc(170rpx + env(safe-area-inset-bottom));
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 16% 8%, rgba(255, 240, 189, 0.72), transparent 28%),
    linear-gradient(180deg, #fff4da 0%, #f8efd9 100%);
}

.login-page__top,
.login-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.login-page__time {
  font-size: 32rpx;
  font-weight: 800;
}

.login-page__notice {
  width: 54rpx;
  height: 54rpx;
  font-size: 24rpx;
  font-weight: 900;
  line-height: 54rpx;
  text-align: center;
  color: #4a2f1b;
  border: 4rpx solid #4a2f1b;
  border-radius: 50%;
}

.login-page__header {
  margin-top: 22rpx;
}

.login-page__title {
  font-size: 66rpx;
  font-weight: 900;
  letter-spacing: 0;
}

.login-page__brand {
  padding: 10rpx 20rpx;
  font-size: 24rpx;
  font-weight: 800;
  color: #d94b12;
  background: #fff0bd;
  border: 2rpx solid rgba(242, 106, 33, 0.24);
  border-radius: 999rpx;
}

.login-page__scene {
  position: relative;
  height: 360rpx;
  margin: 28rpx 0 26rpx;
  overflow: hidden;
  background: rgba(255, 250, 240, 0.34);
  border-radius: 30rpx;
}

.login-page__leaf,
.login-page__palace,
.login-page__book,
.login-page__adult,
.login-page__child,
.login-page__bot {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4a2f1b;
  border: 3rpx solid rgba(190, 142, 78, 0.24);
  box-shadow: 0 10rpx 22rpx rgba(97, 63, 28, 0.08);
}

.login-page__leaf {
  top: 16rpx;
  left: 18rpx;
  width: 92rpx;
  height: 56rpx;
  color: #55753c;
  background: #dceecb;
  border-radius: 60% 38% 58% 42%;
  transform: rotate(-12deg);
}

.login-page__family {
  position: absolute;
  inset: 0;
}

.login-page__adult {
  left: 84rpx;
  bottom: 88rpx;
  width: 150rpx;
  height: 178rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #2f6f94;
  background: #cfe7f5;
  border-radius: 78rpx 78rpx 48rpx 48rpx;
}

.login-page__child {
  left: 224rpx;
  bottom: 76rpx;
  width: 122rpx;
  height: 142rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #d94b12;
  background: #ffd782;
  border-radius: 70rpx 70rpx 42rpx 42rpx;
}

.login-page__bot {
  right: 98rpx;
  bottom: 82rpx;
  width: 124rpx;
  height: 112rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #2f6f94;
  background: #e9f6fb;
  border-radius: 46rpx;
}

.login-page__palace {
  right: 6rpx;
  top: 66rpx;
  width: 190rpx;
  height: 96rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #d94b12;
  background: #ffdca4;
  border-radius: 28rpx 28rpx 18rpx 18rpx;
}

.login-page__book {
  left: 206rpx;
  bottom: 20rpx;
  width: 190rpx;
  height: 64rpx;
  font-size: 24rpx;
  color: #8a6d54;
  background: #fffaf0;
  border-radius: 18rpx;
}

.login-page__copy {
  text-align: center;
}

.login-page__headline {
  display: block;
  font-size: 46rpx;
  font-weight: 900;
  line-height: 1.2;
}

.login-page__subtitle {
  display: block;
  margin-top: 18rpx;
  font-size: 27rpx;
  line-height: 1.45;
  color: #6f5238;
}

.login-page__form {
  margin-top: 30rpx;
}

.login-page__field {
  box-sizing: border-box;
  min-height: 94rpx;
  padding: 14rpx 26rpx;
  margin-bottom: 18rpx;
  background: rgba(255, 250, 240, 0.9);
  border: 2rpx solid rgba(190, 142, 78, 0.3);
  border-radius: 999rpx;
}

.login-page__field--code {
  display: flex;
  gap: 14rpx;
  align-items: center;
  padding-right: 14rpx;
}

.login-page__code-input {
  flex: 1;
  min-width: 0;
}

.login-page__field-label {
  display: block;
  margin-bottom: 2rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: #8a6d54;
}

.login-page__field input {
  height: 42rpx;
  font-size: 28rpx;
  color: #4a2f1b;
}

.login-page__code-button {
  width: 166rpx;
  height: 66rpx;
  font-size: 23rpx;
  color: #d94b12;
  background: #fff0bd;
  border-radius: 999rpx;
}

.login-page__code-button[disabled] {
  color: #8a6d54;
  background: #eadcc8;
}

.login-page__primary,
.login-page__wechat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  width: 100%;
  height: 88rpx;
  margin-top: 18rpx;
  font-size: 33rpx;
  font-weight: 900;
  border-radius: 999rpx;
}

.login-page__primary {
  color: #fff;
  background: #f26a21;
  box-shadow: 0 12rpx 24rpx rgba(242, 106, 33, 0.2);
}

.login-page__wechat {
  color: #4a2f1b;
  background: rgba(255, 250, 240, 0.84);
  border: 2rpx solid rgba(190, 142, 78, 0.32);
}

.login-page__button-icon,
.login-page__wechat-icon {
  font-size: 28rpx;
}

.login-page__agreement {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  margin-top: 22rpx;
  font-size: 24rpx;
  line-height: 1.4;
  color: #6f5238;
}

.login-page__check {
  width: 34rpx;
  height: 34rpx;
  font-size: 24rpx;
  line-height: 34rpx;
  text-align: center;
  color: #fff;
  border: 3rpx solid #8a6d54;
  border-radius: 50%;
}

.login-page__check--active {
  background: #f26a21;
  border-color: #f26a21;
}

.login-page__link {
  color: #f26a21;
}

.login-page__value-card {
  padding: 30rpx 24rpx 28rpx;
  margin-top: 30rpx;
  background: rgba(255, 250, 240, 0.62);
  border: 2rpx solid rgba(190, 142, 78, 0.24);
  border-radius: 26rpx;
  box-shadow: 0 12rpx 26rpx rgba(97, 63, 28, 0.06);
}

.login-page__value-title {
  margin-bottom: 24rpx;
  font-size: 36rpx;
  font-weight: 900;
  text-align: center;
}

.login-page__values {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
}

.login-page__value {
  min-width: 0;
  text-align: center;
}

.login-page__value-art {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92rpx;
  height: 92rpx;
  margin: 0 auto 14rpx;
  font-size: 30rpx;
  font-weight: 900;
  color: #d94b12;
  background: #fff0bd;
  border: 3rpx solid rgba(244, 170, 35, 0.22);
  border-radius: 30rpx;
}

.login-page__value-name {
  display: block;
  font-size: 25rpx;
  font-weight: 900;
  line-height: 1.2;
}

.login-page__value-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 20rpx;
  line-height: 1.3;
  color: #6f5238;
}
</style>
