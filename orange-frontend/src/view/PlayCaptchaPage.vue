<template>
  <div class="captcha-page">
    <h2>🤖 人机验证</h2>
    <p class="captcha-tip">抓中正确的玩具并投入舱口，证明你是真人。完成后会自动返回。</p>
    <PlayCaptcha @verified="onVerified" />
    <button v-if="verified" class="back-btn" @click="goBack">已完成验证，返回</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PlayCaptcha from '../components/PlayCaptcha.vue'

const router = useRouter()
const verified = ref(false)

const onVerified = () => {
  verified.value = true
  localStorage.setItem('captcha_verified', String(Date.now()))
  // 短暂停留后自动返回
  setTimeout(() => goBack(), 800)
}

const goBack = () => {
  if (window.history.length > 1) router.back()
  else router.push('/')
}
</script>

<style scoped>
.captcha-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  box-sizing: border-box;
  padding: 8px 16px 32px;
  overflow-x: hidden;
  text-align: center;
}
.captcha-tip { color: #909399; margin-bottom: 20px; }
.back-btn {
  margin-top: 20px;
  padding: 10px 28px;
  background: #ff9900;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  cursor: pointer;
}
</style>
