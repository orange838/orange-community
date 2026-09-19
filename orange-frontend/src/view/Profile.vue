<template>
  <div class="page-container">
    <h2>👤 个人信息</h2>
    <div class="profile-card">
      <template v-if="currentUser.info">
        <p>当前状态：<span style="color: #ff9900; font-weight: bold;">已登录</span></p>
        <p>用户名：{{ currentUser.info.username }}</p>
        <p>邮箱：{{ currentUser.info.email }}</p>
        <p v-if="currentUser.info.role === 'admin'">角色：管理员</p>
        <p>橙子余额：{{ currentUser.info.orange_balance ?? 0 }}</p>
        <p>签到记录：已签到 {{ currentUser.info.sign_in_count ?? 0 }} 次</p>
        <div class="github-bind">
          <span>GitHub：{{ currentUser.info.github_username ? ('已绑定 @' + currentUser.info.github_username) : '未绑定' }}</span>
          <button v-if="!currentUser.info.github_username" class="bind-btn" @click="bindGithub">绑定 GitHub</button>
          <button v-else class="unbind-btn" @click="unbindGithub">解绑</button>
        </div>
      </template>
      <template v-else>
        <p>当前状态：<span style="color: #909399;">未登录</span></p>
        <p style="margin-top: 10px; color: #909399;">
          请先点击右上角【登录】按钮，登录后查看您的橙子余额和签到记录。
        </p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { currentUser } from '../store'

const loadProfile = async () => {
  if (!currentUser.info?.email) return

  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, ...result })
    }
  } catch {
    // ignore profile fetch errors and retain the logged-in shell state
  }
}

onMounted(() => {
  loadProfile()
})

const bindGithub = () => {
  if (!currentUser.info?.email) return
  window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/github?mode=bind&bindEmail=${encodeURIComponent(currentUser.info.email)}`
}

const unbindGithub = async () => {
  if (!currentUser.info?.email) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/github/unbind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, github_id: null, github_username: null })
      alert(result.message || '已解绑 GitHub')
    } else {
      alert(result.error || '解绑失败')
    }
  } catch {
    alert('网络异常，请稍后再试')
  }
}

watch(() => currentUser.info?.email, () => {
  loadProfile()
})
</script>

<style scoped>
.profile-card {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  margin-top: 15px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
  line-height: 1.8;
}

.github-bind { margin-top: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.bind-btn { padding: 6px 16px; background-color: #24292e; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.bind-btn:hover { background-color: #000; }
.unbind-btn { padding: 6px 16px; background-color: #fff; color: #f56c6c; border: 1px solid #f56c6c; border-radius: 4px; cursor: pointer; font-size: 13px; }
.unbind-btn:hover { background-color: #fef0f0; }
</style>