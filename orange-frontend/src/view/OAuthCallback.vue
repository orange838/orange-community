<template>
  <div class="oauth-callback">
    <div class="box">
      <h3>{{ message }}</h3>
      <p v-if="errorText" class="err">{{ errorText }}</p>
      <a href="#/checkin" v-if="!errorText">正在跳转…</a>
      <a href="#/" v-else>返回首页</a>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser } from '../store'

const route = useRoute()
const router = useRouter()
const message = ref('处理中...')
const errorText = ref('')

onMounted(() => {
  const error = route.query.error
  const token = route.query.token
  const userRaw = route.query.user

  if (error) {
    message.value = '操作未完成'
    if (error === 'unbound') {
      const src = route.query.src || 'github'
      const pn = src === 'cpoauth' ? 'CP OAuth' : 'GitHub'
      errorText.value = `该${pn}账号尚未绑定社区账号。请先注册或登录社区，再到「个人信息」页绑定${pn}后，即可用${pn}一键登录。`
    } else if (error === 'invalid_state') {
      errorText.value = '授权状态校验失败，请重新操作。'
    } else if (error === 'bind_email_not_found') {
      errorText.value = '绑定目标账号不存在，请重新登录后再试。'
    } else if (error === 'not_configured') {
      errorText.value = 'GitHub 登录暂未配置，请联系管理员。'
    } else if (error === 'github_error') {
      errorText.value = 'GitHub 授权失败，请重试。'
    } else {
      errorText.value = '授权失败，请重试。'
    }
    return
  }

  if (token && userRaw) {
    try {
      const user = JSON.parse(decodeURIComponent(userRaw))
      currentUser.setInfo({ ...user, token })
      message.value = `登录成功，欢迎${user.username || '你'}！`
      setTimeout(() => { router.replace('/checkin') }, 1200)
    } catch (e) {
      message.value = '处理失败'
      errorText.value = '返回数据异常，请重新登录。'
    }
  } else {
    message.value = '缺少回调参数'
    errorText.value = '未收到有效的授权信息，请重新操作。'
  }
})
</script>

<style scoped>
.oauth-callback { min-height: 70vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
.box { background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; max-width: 440px; }
.box h3 { color: #333; margin-bottom: 8px; }
.err { color: #f56c6c; margin-top: 12px; line-height: 1.6; }
a { color: #ff9900; text-decoration: none; margin-top: 16px; display: inline-block; }
a:hover { text-decoration: underline; }
</style>
