import { useChildStore } from '../stores/child'
import { useGuideStore } from '../stores/guide'
import { usePlanStore } from '../stores/plan'
import { useRecordStore } from '../stores/record'
import { useTaskStore } from '../stores/task'
import { useUserStore } from '../stores/user'

let activeSessionEnd = null

export function endUserSession() {
  if (activeSessionEnd) return activeSessionEnd

  activeSessionEnd = (async () => {
    const childStore = useChildStore()
    const planStore = usePlanStore()
    const guideStore = useGuideStore()
    const taskStore = useTaskStore()
    const recordStore = useRecordStore()
    const userStore = useUserStore()

    childStore.resetSessionState()
    planStore.resetSessionState()
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
