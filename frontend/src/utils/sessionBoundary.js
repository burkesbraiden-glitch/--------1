import { useChildStore } from '../stores/child'
import { useGuideStore } from '../stores/guide'
import { usePlanStore } from '../stores/plan'
import { useRecordStore } from '../stores/record'
import { useRouteStore } from '../stores/route'
import { useTaskStore } from '../stores/task'
import { useUserStore } from '../stores/user'

let activeSessionEnd = null

export function getCurrentSession() {
  const userStore = useUserStore()
  return {
    epoch: userStore.sessionEpoch,
    userId: userStore.userInfo?.id ?? null,
    isLoggedIn: userStore.isLoggedIn,
  }
}

export function isCurrentSession(session) {
  const current = getCurrentSession()
  return Boolean(
    session
    && current.isLoggedIn
    && current.epoch === session.epoch
    && String(current.userId) === String(session.userId),
  )
}

export function endUserSession() {
  if (activeSessionEnd) return activeSessionEnd

  activeSessionEnd = (async () => {
    const childStore = useChildStore()
    const planStore = usePlanStore()
    const routeStore = useRouteStore()
    const guideStore = useGuideStore()
    const taskStore = useTaskStore()
    const recordStore = useRecordStore()
    const userStore = useUserStore()

    userStore.invalidateSession()
    childStore.resetSessionState()
    planStore.resetSessionState()
    routeStore.resetSessionState()
    guideStore.resetSessionState()
    taskStore.resetSessionState()
    recordStore.resetRecordState()

    try {
      await userStore.logout()
    } catch (error) {
      // logout() already clears local authentication in its finally branch.
    } finally {
      if (typeof uni !== 'undefined' && uni.reLaunch) {
        await uni.reLaunch({ url: '/pages/login/index' })
      }
    }
  })().finally(() => {
    activeSessionEnd = null
  })

  return activeSessionEnd
}
