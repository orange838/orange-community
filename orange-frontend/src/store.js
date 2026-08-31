// src/store.js
import { reactive } from 'vue'

const readSavedUser = () => {
  try {
    const raw = localStorage.getItem('orange_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const currentUser = reactive({
  info: readSavedUser(),

  setInfo(userData) {
    this.info = { ...(this.info || {}), ...(userData || {}) }
    try {
      localStorage.setItem('orange_user', JSON.stringify(this.info))
    } catch {}
  },

  clearInfo() {
    this.info = null
    try {
      localStorage.removeItem('orange_user')
    } catch {}
  },

  refreshFromStorage() {
    this.info = readSavedUser()
  }
})

if (typeof window !== 'undefined') {
  window.addEventListener('storage', () => {
    currentUser.refreshFromStorage()
  })
}