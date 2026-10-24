<template>
  <div class="login-page">
    <LoginModal mode="page" v-model:is-login="isLogin" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoginModal from '../components/LoginModal.vue'

const route = useRoute()
const router = useRouter()
const isLogin = ref(true)

// 从 URL query ?mode=login|register 初始切换
onMounted(() => {
  const m = String(route.query.mode || '')
  if (m === 'register') isLogin.value = false
  else if (m === 'login') isLogin.value = true
})

// 切换登录/注册时同步到 URL（replace，不新增历史记录）
watch(isLogin, (v) => {
  const q = v ? 'login' : 'register'
  if (route.query.mode === q) return
  router.replace({ path: '/login', query: { ...route.query, mode: q } })
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: clamp(12px, 3vh, 48px) 16px 16px;
  background: #f7f8fa;
}
</style>
