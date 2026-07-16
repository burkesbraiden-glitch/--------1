import { defineStore } from 'pinia'

export const usePetStore = defineStore('pet', {
  state: () => ({
    mode: 'peek',
    pageContext: 'home',
    contextId: '',
    chatOpen: false,
  }),
  actions: {
    setMode(mode) {
      if (['hidden', 'peek', 'open'].includes(mode)) {
        this.mode = mode
      }
    },
    setPageContext(pageContext, contextId = '') {
      this.pageContext = pageContext
      this.contextId = contextId
    },
    openChat() {
      this.mode = 'open'
      this.chatOpen = true
    },
    closeChat() {
      this.chatOpen = false
      this.mode = 'peek'
    },
    hidePet() {
      this.chatOpen = false
      this.mode = 'hidden'
    },
    peekPet() {
      this.mode = 'peek'
    },
  },
})

