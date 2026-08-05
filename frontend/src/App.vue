<script>
import { useUserStore } from './stores/user'
import { isAuthenticationError } from './utils/request'
import { endUserSession } from './utils/sessionBoundary'

export default {
  async onLaunch() {
    const userStore = useUserStore()
    const restored = await userStore.restoreSession()

    if (!restored && isAuthenticationError(userStore.authError)) {
      await endUserSession()
    }

    console.log('童旅记 App Launch')
  },
  onShow: function () {
    console.log('童旅记 App Show')
  },
  onHide: function () {
    console.log('童旅记 App Hide')
  },
}
</script>

<style lang="scss">
@use './styles/global.scss' as *;
</style>

