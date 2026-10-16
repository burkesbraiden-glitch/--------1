<template>
  <view class="settings-page">
    <view class="settings-page__paper">
      <PageHeader class="settings-page__header" title="账号与设置" @back="goBack" />

      <view class="settings-section">
        <text class="settings-section__title">账户与隐私</text>
        <view class="settings-list">
          <button class="settings-row" @click="showAccountInfo">
            <view class="settings-row__icon settings-row__icon--account" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>账号信息</text><text>{{ accountLabel }}</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
          <button class="settings-row" @click="openNotice('child')">
            <view class="settings-row__icon settings-row__icon--shield" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>儿童资料与隐私</text><text>了解儿童资料的保存与删除范围</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
          <button class="settings-row" :disabled="isExporting" @click="requestExport">
            <view class="settings-row__icon settings-row__icon--export" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>{{ isExporting ? '正在生成数据…' : '导出我的数据' }}</text><text>生成当前账户的结构化数据副本</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
          <button class="settings-row" @click="openNotice('privacy')">
            <view class="settings-row__icon settings-row__icon--document" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>隐私政策</text><text>查看当前功能说明</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
          <button class="settings-row" @click="openNotice('terms')">
            <view class="settings-row__icon settings-row__icon--document" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>用户协议</text><text>查看当前功能说明</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view class="settings-section">
        <text class="settings-section__title">应用</text>
        <view class="settings-list">
          <button class="settings-row" @click="showUnavailable('关于童旅记')">
            <view class="settings-row__icon settings-row__icon--about" aria-hidden="true"></view>
            <view class="settings-row__copy"><text>关于童旅记</text><text>亲子旅行学习 App</text></view>
            <text class="settings-row__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view class="settings-section settings-section--danger">
        <text class="settings-section__title">危险操作</text>
        <button class="settings-delete" :disabled="isDeletingAccount" @click="requestDeleteAccount">删除账户</button>
        <text class="settings-delete__hint">删除后无法恢复，请谨慎操作。</text>
      </view>

      <button class="settings-logout" @click="logout"><text aria-hidden="true">↪</text>退出登录</button>
    </view>
    <AppTabbar active="profile" />

    <view v-if="noticeType" class="settings-dialog-mask" @click.self="closeNotice">
      <view class="settings-dialog" role="dialog">
        <view class="settings-dialog__header"><text>{{ noticeTitle }}</text><button aria-label="关闭" @click="closeNotice">×</button></view>
        <scroll-view scroll-y class="settings-dialog__body">
          <template v-if="noticeType === 'child'">
            <text>儿童资料由监护人创建。我们仅保存创建儿童资料和开展探索所需的昵称、年龄、可选城市、兴趣及预设头像。</text>
            <text>儿童头像仅能从预设头像中选择，不上传或保存儿童真实头像；不会请求或保存精确位置。</text>
            <text>删除儿童资料会删除该儿童的探索计划、任务提交、记录及受控资产；家庭共享路线会保留，其他孩子不受影响。</text>
          </template>
          <template v-else-if="noticeType === 'privacy'">
            <text>本页仅说明当前产品功能：账号可创建儿童资料、生成探索内容、保存任务提交和探索记录，并可导出或删除自己的账户数据。</text>
            <text class="settings-dialog__pending">上线前需完成正式法律审核与替换</text>
          </template>
          <template v-else>
            <text>使用童旅记时，请由监护人确认儿童资料创建，并在需要时通过设置中的导出或删除功能管理当前账户数据。</text>
            <text class="settings-dialog__pending">上线前需完成正式法律审核与替换</text>
          </template>
        </scroll-view>
        <button class="settings-dialog__close" @click="closeNotice">我知道了</button>
      </view>
    </view>

    <view v-if="exportData" class="settings-dialog-mask" @click.self="closeExport">
      <view class="settings-dialog settings-dialog--export" role="dialog">
        <view class="settings-dialog__header"><text>账户结构化数据</text><button aria-label="关闭" @click="closeExport">×</button></view>
        <text class="settings-dialog__lead">这是当前账户的结构化数据副本，不包含密码、令牌、存储路径或对象密钥。</text>
        <scroll-view scroll-y class="settings-export__content"><text user-select>{{ exportText }}</text></scroll-view>
        <view class="settings-dialog__actions"><button class="settings-dialog__secondary" @click="copyExport">复制内容</button><button class="settings-dialog__close" @click="closeExport">关闭</button></view>
      </view>
    </view>

    <view v-if="isDeleteConfirming" class="settings-dialog-mask" @click.self="cancelDeleteAccount">
      <view class="settings-dialog" role="dialog">
        <view class="settings-dialog__header"><text>确认删除账户</text><button aria-label="关闭" :disabled="isDeletingAccount" @click="cancelDeleteAccount">×</button></view>
        <text class="settings-dialog__lead">将永久删除所有儿童资料、探索计划、任务与提交、探索记录、家庭共享路线及相关照片和音频。此操作不可恢复。</text>
        <text class="settings-dialog__instruction">请输入“删除我的账户”继续</text>
        <input v-model="deletePhrase" class="settings-dialog__input" :disabled="isDeletingAccount" placeholder="删除我的账户" maxlength="20" />
        <text v-if="deleteError" class="settings-dialog__error">{{ deleteError }}</text>
        <view class="settings-dialog__actions"><button class="settings-dialog__secondary" :disabled="isDeletingAccount" @click="cancelDeleteAccount">取消</button><button class="settings-dialog__danger" :disabled="!canDeleteAccount" @click="deleteCurrentAccount">{{ isDeletingAccount ? '正在删除…' : '永久删除' }}</button></view>
      </view>
    </view>
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import PageHeader from '../../components/ui/PageHeader.vue'
import { deleteAccount, exportAccountData } from '../../api/account.js'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'
import { isAuthenticationError } from '../../utils/request.js'

export default {
  components: { AppTabbar, PageHeader },
  data() {
    return {
      noticeType: '',
      isExporting: false,
      exportData: null,
      exportError: '',
      isDeleteConfirming: false,
      deletePhrase: '',
      isDeletingAccount: false,
      deleteError: '',
    }
  },
  computed: {
    user() { return useUserStore() },
    accountLabel() { return this.user.userInfo?.nickname || '当前已登录账号' },
    noticeTitle() { return { child: '儿童隐私说明', privacy: '隐私政策', terms: '用户协议' }[this.noticeType] || '' },
    exportText() { return this.exportData ? JSON.stringify(this.exportData, null, 2) : '' },
    canDeleteAccount() { return this.deletePhrase.trim() === '删除我的账户' && !this.isDeletingAccount },
  },
  async onShow() {
    await this.user.restoreSession()
    if (!this.user.isLoggedIn) uni.reLaunch({ url: '/pages/login/index' })
  },
  methods: {
    goBack() { uni.navigateBack() },
    showUnavailable(title) { uni.showToast({ title, icon: 'none' }) },
    showAccountInfo() { this.showUnavailable('当前登录账号：' + this.accountLabel) },
    openNotice(type) { this.noticeType = type },
    closeNotice() { this.noticeType = '' },
    requestExport() {
      if (this.isExporting) return
      uni.showModal({
        title: '导出账户数据',
        content: '将生成当前账户的结构化数据副本，供你查看或自行保存。这不是完整数据副本。',
        cancelText: '取消',
        confirmText: '生成',
        success: (result) => { if (result.confirm) this.loadExport() },
      })
    },
    async loadExport() {
      this.isExporting = true
      this.exportError = ''
      try {
        const data = await exportAccountData()
        this.exportData = data?.export || null
        if (!this.exportData) throw new Error('Export payload is missing')
      } catch (error) {
        this.exportError = error?.message || '导出失败，请稍后重试'
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        this.showUnavailable(this.exportError)
      } finally {
        this.isExporting = false
      }
    },
    closeExport() { this.exportData = null },
    copyExport() {
      if (typeof uni.setClipboardData !== 'function') {
        this.showUnavailable('请长按内容后复制')
        return
      }
      uni.setClipboardData({
        data: this.exportText,
        success: () => this.showUnavailable('已复制结构化数据'),
        fail: () => this.showUnavailable('复制失败，请长按内容后复制'),
      })
    },
    requestDeleteAccount() {
      if (this.isDeletingAccount) return
      uni.showModal({
        title: '删除账户？',
        content: '将永久删除所有儿童资料、探索计划、任务与提交、探索记录、家庭共享路线及相关照片和音频。此操作不可恢复。',
        cancelText: '取消',
        confirmText: '继续',
        success: (result) => {
          if (result.confirm) {
            this.deletePhrase = ''
            this.deleteError = ''
            this.isDeleteConfirming = true
          }
        },
      })
    },
    cancelDeleteAccount() {
      if (this.isDeletingAccount) return
      this.isDeleteConfirming = false
      this.deletePhrase = ''
      this.deleteError = ''
    },
    async deleteCurrentAccount() {
      if (!this.canDeleteAccount) return
      this.isDeletingAccount = true
      this.deleteError = ''
      try {
        await deleteAccount()
        await endUserSession()
      } catch (error) {
        // A failed DELETE must preserve the active session and all local data for retry.
        this.deleteError = error?.message || '删除失败，请稍后重试'
      } finally {
        this.isDeletingAccount = false
      }
    },
    async logout() { await endUserSession() },
  },
}
</script>

<style scoped>
.settings-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }.settings-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; box-sizing: border-box; padding: 0 var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 40rpx); margin: 0 auto; }.settings-page__header { margin-bottom: 40rpx; }
.settings-section { margin-top: 40rpx; }.settings-section:first-of-type { margin-top: 0; }.settings-section__title { display: block; margin: 0 0 14rpx; font-size: var(--tl-type-meta); font-weight: 600; color: var(--tl-text-secondary); }.settings-list { overflow: hidden; background: var(--tl-surface); border-top: 1rpx solid var(--tl-divider); border-bottom: 1rpx solid var(--tl-divider); }.settings-row { display: flex; align-items: center; width: 100%; min-height: 126rpx; padding: 20rpx 4rpx; color: var(--tl-text-main); text-align: left; }.settings-row:disabled { opacity: .6; }.settings-row + .settings-row { border-top: 1rpx solid var(--tl-divider); }.settings-row__icon { position: relative; flex: 0 0 54rpx; width: 54rpx; height: 54rpx; margin-right: 20rpx; color: #315248; }.settings-row__icon::before,.settings-row__icon::after { position: absolute; box-sizing: border-box; content: ''; }.settings-row__icon--account::before { top: 2rpx; left: 16rpx; width: 20rpx; height: 20rpx; border: 3rpx solid currentColor; border-radius: 50%; }.settings-row__icon--account::after { bottom: 2rpx; left: 7rpx; width: 38rpx; height: 24rpx; border: 3rpx solid currentColor; border-bottom: 0; border-radius: 24rpx 24rpx 0 0; }.settings-row__icon--shield::before { top: 2rpx; left: 9rpx; width: 35rpx; height: 43rpx; border: 3rpx solid currentColor; border-radius: 20rpx 20rpx 14rpx 14rpx; }.settings-row__icon--shield::after { top: 18rpx; left: 20rpx; width: 12rpx; height: 7rpx; border-bottom: 3rpx solid currentColor; border-left: 3rpx solid currentColor; transform: rotate(-45deg); }.settings-row__icon--export::before { top: 3rpx; left: 22rpx; width: 3rpx; height: 30rpx; background: currentColor; }.settings-row__icon--export::after { bottom: 3rpx; left: 10rpx; width: 30rpx; height: 15rpx; border: 3rpx solid currentColor; border-top: 0; }.settings-row__icon--document::before,.settings-row__icon--about::before { width: 38rpx; height: 46rpx; margin: 4rpx 8rpx; border: 3rpx solid currentColor; border-radius: 6rpx; }.settings-row__icon--document::after,.settings-row__icon--about::after { top: 15rpx; left: 18rpx; width: 18rpx; height: 3rpx; background: currentColor; box-shadow: 0 10rpx 0 currentColor; }.settings-row__copy { flex: 1; min-width: 0; }.settings-row__copy text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.settings-row__copy text:first-child { font-size: var(--tl-type-body); font-weight: 600; }.settings-row__copy text:last-child { margin-top: 7rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.settings-row__arrow { margin-left: 16rpx; font-size: 42rpx; font-weight: 300; color: var(--tl-text-secondary); }.settings-section--danger { padding-top: 6rpx; }.settings-delete { width: 100%; min-height: var(--tl-control-min-height); color: #b43d31; background: transparent; border: 1rpx solid #dfab9f; border-radius: var(--tl-radius-control); }.settings-delete:disabled { opacity: .55; }.settings-delete__hint { display: block; margin: 12rpx 0 0; font-size: var(--tl-type-meta); line-height: 1.5; color: var(--tl-text-secondary); }.settings-logout { display: flex; gap: 12rpx; align-items: center; justify-content: center; width: 100%; min-height: var(--tl-control-min-height); margin-top: 38rpx; font-size: var(--tl-type-primary-action); font-weight: 600; color: #c94b3b; background: #fff0ed; border-radius: var(--tl-radius-control); }.settings-logout text { font-size: 36rpx; }
.settings-dialog-mask { position: fixed; z-index: 20; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding: 24rpx 24rpx calc(24rpx + var(--tl-safe-bottom)); box-sizing: border-box; background: rgba(43, 38, 31, .42); }.settings-dialog { width: 100%; max-width: var(--tl-content-max-width); max-height: 78vh; padding: 28rpx; box-sizing: border-box; background: var(--tl-surface); border-radius: var(--tl-radius-sheet); }.settings-dialog--export { max-height: 84vh; }.settings-dialog__header { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }.settings-dialog__header text { font-size: var(--tl-type-section-title); font-weight: 700; }.settings-dialog__header button { width: 58rpx; min-width: 58rpx; height: 58rpx; font-size: 42rpx; line-height: 1; color: var(--tl-text-secondary); }.settings-dialog__body { max-height: 52vh; margin-top: 22rpx; }.settings-dialog__body text,.settings-dialog__lead,.settings-dialog__instruction { display: block; font-size: var(--tl-type-body); line-height: 1.7; color: var(--tl-text-main); }.settings-dialog__body text + text { margin-top: 18rpx; }.settings-dialog__pending { color: #a75b28 !important; }.settings-dialog__lead { margin-top: 20rpx; color: var(--tl-text-secondary); }.settings-dialog__instruction { margin-top: 22rpx; font-weight: 600; }.settings-dialog__input { width: 100%; height: 80rpx; padding: 0 20rpx; margin-top: 14rpx; box-sizing: border-box; font-size: var(--tl-type-body); color: var(--tl-text-main); background: var(--tl-bg); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); }.settings-dialog__error { display: block; margin-top: 12rpx; font-size: var(--tl-type-meta); color: #b43d31; }.settings-export__content { max-height: 50vh; padding: 18rpx; margin-top: 18rpx; box-sizing: border-box; background: var(--tl-bg); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-control); }.settings-export__content text { font-family: monospace; font-size: 22rpx; line-height: 1.55; color: var(--tl-text-main); white-space: pre-wrap; word-break: break-all; }.settings-dialog__actions { display: flex; gap: 16rpx; margin-top: 26rpx; }.settings-dialog__actions button,.settings-dialog__close { flex: 1; min-height: var(--tl-control-min-height); font-size: var(--tl-type-body); border-radius: var(--tl-radius-control); }.settings-dialog__close { width: 100%; margin-top: 26rpx; color: #fff; background: #1f7b47; }.settings-dialog__actions .settings-dialog__close { margin-top: 0; }.settings-dialog__secondary { color: #315248; background: transparent; border: 1rpx solid var(--tl-divider); }.settings-dialog__danger { color: #fff; background: #b43d31; }.settings-dialog__danger:disabled { opacity: .55; }
@media (min-width: 431px) { .settings-page__paper { padding: 0 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 22px); }.settings-page__header { margin-bottom: 20px; }.settings-section { margin-top: 20px; }.settings-section__title { margin-bottom: 7px; }.settings-row { min-height: 63px; padding: 10px 2px; }.settings-row__icon { flex-basis: 27px; width: 27px; height: 27px; margin-right: 10px; }.settings-delete,.settings-logout,.settings-dialog__actions button,.settings-dialog__close { min-height: 44px; }.settings-logout { margin-top: 19px; }.settings-dialog-mask { padding: 12px 12px calc(12px + var(--tl-safe-bottom)); }.settings-dialog { padding: 14px; }.settings-dialog__header button { width: 29px; min-width: 29px; height: 29px; }.settings-dialog__input { height: 40px; padding: 0 10px; }.settings-export__content text { font-size: 11px; } }
</style>
