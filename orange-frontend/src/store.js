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

const readSavedToken = () => {
  try {
    return localStorage.getItem('orange_token')
  } catch {
    return null
  }
}

export const currentUser = reactive({
  info: readSavedUser(),
  token: readSavedToken(),

  setInfo(userData) {
    // 兼容后端返回 { token, user } 的形式：token 单独持久化，user 数据存入 info
    if (userData && userData.token) {
      this.token = userData.token
      try {
        localStorage.setItem('orange_token', this.token)
      } catch {}
      const { token, ...rest } = userData
      userData = rest
    }
    this.info = { ...(this.info || {}), ...(userData || {}) }
    try {
      localStorage.setItem('orange_user', JSON.stringify(this.info))
    } catch {}
  },

  clearInfo() {
    this.info = null
    this.token = null
    try {
      localStorage.removeItem('orange_user')
      localStorage.removeItem('orange_token')
    } catch {}
  },

  refreshFromStorage() {
    this.info = readSavedUser()
    this.token = readSavedToken()
  }
})

if (typeof window !== 'undefined') {
  window.addEventListener('storage', () => {
    currentUser.refreshFromStorage()
  })
}
