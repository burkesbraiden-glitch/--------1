<script>
import { useUserStore } from './stores/user'

export default {
  onLaunch: function () {
    useUserStore().restoreSession()
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

