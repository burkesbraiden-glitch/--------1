import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { deleteAccount, exportAccountData } from '../../src/api/account.js'
import { useUserStore } from '../../src/stores/user.js'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')
const settings = sourceOf('src', 'pages', 'settings', 'index.vue')
const accountApi = sourceOf('src', 'api', 'account.js')
const profile = sourceOf('src', 'pages', 'profile', 'index.vue')

function login() {
  useUserStore().loginSuccess('p11-2c-token', { id: 9301, nickname: '监护人' })
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

describe('P11.2c account privacy settings', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps Profile focused while linking the existing Settings entry to privacy controls', () => {
    expect(profile).toContain('管理隐私与账户')
    expect(profile).not.toContain('导出数据')
    expect(profile).not.toContain('删除账户')
    expect(settings).toContain('账户与隐私')
    expect(settings).toContain('儿童隐私说明')
    expect(settings).toContain('导出数据')
    expect(settings).toContain('隐私政策')
    expect(settings).toContain('用户协议')
    expect(settings).toContain('删除账户')
  })

  test('states only implemented child privacy behavior and marks legal text as pending review', () => {
    expect(settings).toContain('儿童资料由监护人创建')
    expect(settings).toContain('预设头像')
    expect(settings).toContain('不会请求或保存精确位置')
    expect(settings).toContain('家庭共享路线会保留')
    expect(settings).toContain('上线前需完成正式法律审核与替换')
    expect(settings).not.toContain('已通过法律审核')
    expect(settings).not.toContain('ICP备')
  })

  test('uses authenticated account endpoints with no client-side identifier or cleanup payload', async () => {
    login()
    setRequestHandler((options) => {
      expect(options.header.Authorization).toBe('Bearer p11-2c-token')
      if (options.url.endsWith('/account/export')) {
        expect(options.method).toBe('GET')
        expect(options.data).toBeUndefined()
        respond(options, { export: { formatVersion: 'p11.2c', children: [] } })
        return
      }
      expect(options.url.endsWith('/account')).toBe(true)
      expect(options.method).toBe('DELETE')
      expect(options.data).toBeUndefined()
      respond(options, { deleted: true })
    })

    await expect(exportAccountData()).resolves.toEqual({ export: { formatVersion: 'p11.2c', children: [] } })
    await expect(deleteAccount()).resolves.toEqual({ deleted: true })
    expect(getRequestCalls()).toHaveLength(2)
    expect(accountApi).toContain("path: '/account/export'")
    expect(accountApi).toContain("path: '/account'")
    expect(accountApi).not.toContain('userId')
    expect(accountApi).not.toContain('childId')
  })

  test('presents export as a structured-data copy and displays it without a fake download', () => {
    expect(settings).toContain('这不是完整数据副本')
    expect(settings).toContain('账户结构化数据')
    expect(settings).toContain('不包含密码、令牌、存储路径或对象密钥')
    expect(settings).toContain('JSON.stringify(this.exportData, null, 2)')
    expect(settings).toContain('请长按内容后复制')
    expect(settings).not.toContain('下载完成')
    expect(settings).not.toContain('saveFile')
  })

  test('requires two account deletion confirmations and only ends the session after DELETE succeeds', () => {
    expect(settings).toContain("title: '删除账户？'")
    expect(settings).toContain('所有儿童资料、探索计划、任务与提交、探索记录、家庭共享路线及相关照片和音频')
    expect(settings).toContain('请输入“删除我的账户”继续')
    expect(settings).toContain("this.deletePhrase.trim() === '删除我的账户'")
    expect(settings).toContain('await deleteAccount()')
    expect(settings).toContain('await endUserSession()')
    expect(settings).toContain('A failed DELETE must preserve the active session and all local data for retry.')
    expect(settings).not.toContain('clearLocalAuth()')
  })
})
