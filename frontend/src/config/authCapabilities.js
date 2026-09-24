const viteEnv = import.meta.env || {}

export const isMockWechatLoginEnabled = viteEnv.VITE_ENABLE_MOCK_WECHAT_LOGIN === 'true'
