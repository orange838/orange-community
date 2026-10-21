<template>
  <div class="login-page">
    <LoginModal mode="page" v-model:is-login="isLogin" @update:is-login="setMode" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import LoginModal from '../components/LoginModal.vue'

const route = useRoute()
const isLogin = ref(true)

// 从 URL query ?mode=login|register 初始切换
const setMode = (v) => { isLogin.value = v }

onMounted(() => {
  const m = String(route.query.mode || '')
  if (m === 'register') isLogin.value = false
  else if (m === 'login') isLogin.value = true
})

// 切换登录/注册时同步到 URL（可选，保持可分享）
watch(isLogin, (v) => {
  if (window.location.hash) {
    const q = v ? 'login' : 'register'
    // 更新 hash query，不触发整页刷新
    const base = window.location.hash.split('?')[0]
    window.history.replaceState(null, '', `${base}?mode=${q}`)
  }
})
</script>

<style scoped>
.login-page { min-height: 100vh; background: #f7f8fa; }
</style>
