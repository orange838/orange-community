// src/store.js
import { reactive } from 'vue'

// 尝试从浏览器缓存读取上次登录的信息
const savedUser = localStorage.getItem('orange_user')

export const currentUser = reactive({
  // 如果有缓存就解析出来，没有就是 null
  info: savedUser ? JSON.parse(savedUser) : null,

  // 登录成功时调用这个方法
  setInfo(userData) {
    this.info = userData
    // 同步存到本地，防止刷新页面丢失
    localStorage.setItem('orange_user', JSON.stringify(userData))
  },

  // 退出登录时调用
  clearInfo() {
    this.info = null
    localStorage.removeItem('orange_user')
  }
})