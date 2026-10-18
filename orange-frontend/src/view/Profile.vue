<template>
  <div class="page-container">
    <h2>👤 个人信息</h2>
    <div class="profile-card">
      <template v-if="currentUser.info">
        <p>当前状态：<span style="color: #ff9900; font-weight: bold;">已登录</span></p>
        <p>用户名：{{ currentUser.info.username }}</p>
        <p>邮箱：{{ currentUser.info.email }}</p>
        <p v-if="['admin', 'super_admin'].includes(currentUser.info.role)">
          角色：{{ currentUser.info.role === 'super_admin' ? '超级管理员' : '管理员' }}
        </p>
        <p>橙子余额：{{ currentUser.info.orange_balance ?? 0 }}</p>
        <p>签到记录：已签到 {{ currentUser.info.sign_in_count ?? 0 }} 次</p>
        <div class="referral-section">
          <p>拉新邀请码：{{ currentUser.info.referral_code || '尚未创建' }}</p>
          <p class="referral-hint">邀请链接用于普通邮箱注册并记录邀请关系，当前不含奖励。</p>
          <button
            v-if="!currentUser.info.referral_code"
            class="bind-btn"
            :disabled="creatingReferralCode"
            @click="createReferralCode"
          >{{ creatingReferralCode ? '创建中…' : '创建拉新邀请码' }}</button>
          <button
            v-else
            class="bind-btn"
            @click="copyReferralLink"
          >复制拉新链接</button>
        </div>
        <div class="github-bind">
          <span>GitHub：{{ currentUser.info.github_username ? ('已绑定 @' + currentUser.info.github_username) : '未绑定' }}</span>
          <button v-if="!currentUser.info.github_username" class="bind-btn" @click="bindGithub">绑定 GitHub</button>
          <button v-else class="unbind-btn" @click="unbindGithub">解绑</button>
        </div>
        <div class="github-bind">
          <span>CP OAuth：{{ currentUser.info.cpoauth_username ? ('已绑定 @' + currentUser.info.cpoauth_username) : '未绑定' }}</span>
          <button v-if="!currentUser.info.cpoauth_username" class="bind-btn" @click="bindCpoauth">绑定 CP OAuth</button>
          <button v-else class="unbind-btn" @click="unbindCpoauth">解绑</button>
        </div>
        <div class="github-bind">
          <span>邮箱：{{ currentUser.info.email || '未绑定' }}</span>
          <button v-if="!currentUser.info.email" class="bind-btn" @click="showEmailBind = !showEmailBind">绑定邮箱</button>
        </div>
        <div v-if="showEmailBind && !currentUser.info.email" class="email-bind-form">
          <input v-model="emailInput" placeholder="输入要绑定的邮箱" />
          <button class="bind-btn" :disabled="sendingCode" @click="sendEmailCode">{{ sendingCode ? '发送中…' : '发送验证码' }}</button>
          <input v-model="codeInput" placeholder="邮箱验证码" />
          <button class="bind-btn" :disabled="binding" @click="confirmBindEmail">{{ binding ? '绑定中…' : '确认绑定' }}</button>
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
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { currentUser } from '../store'

const route = useRoute()

const loadProfile = async () => {
  if (!currentUser.info?.username) return

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
  // 从“未绑定邮箱”提醒跳转过来时，自动展开绑定表单
  if (route.query.bind === '1') showEmailBind.value = true
})

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const creatingReferralCode = ref(false)

const createReferralCode = async () => {
  creatingReferralCode.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/referral-code`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (!res.ok) {
      showToast(result.error || '创建拉新邀请码失败', 'error')
      return
    }
    currentUser.setInfo({ ...currentUser.info, referral_code: result.code })
    showToast('拉新邀请码已创建', 'success')
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    creatingReferralCode.value = false
  }
}

const copyReferralLink = async () => {
  const link = `${window.location.origin}/?ref=${encodeURIComponent(currentUser.info.referral_code)}`
  try {
    await navigator.clipboard.writeText(link)
    showToast('拉新链接已复制', 'success')
  } catch {
    showToast(`请手动复制：${link}`, 'error')
  }
}

const bindGithub = async () => {
  if (!currentUser.info?.email) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/github?mode=bind&bindEmail=${encodeURIComponent(currentUser.info.email)}`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const data = await res.json()
    if (res.ok && data.authorize_url) {
      window.location.href = data.authorize_url
    } else {
      showToast(data.error || '绑定失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  }
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
      showToast(result.message || '已解绑 GitHub', 'success')
    } else {
      showToast(result.error || '解绑失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  }
}

const bindCpoauth = async () => {
  if (!currentUser.info?.email) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/cpoauth?mode=bind&bindEmail=${encodeURIComponent(currentUser.info.email)}`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const data = await res.json()
    if (res.ok && data.authorize_url) {
      window.location.href = data.authorize_url
    } else {
      showToast(data.error || '绑定失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  }
}

const unbindCpoauth = async () => {
  if (!currentUser.info?.email) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/cpoauth/unbind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, cpoauth_id: null, cpoauth_username: null })
      showToast(result.message || '已解绑 CP OAuth', 'success')
    } else {
      showToast(result.error || '解绑失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  }
}

const showEmailBind = ref(false)
const emailInput = ref('')
const codeInput = ref('')
const sendingCode = ref(false)
const binding = ref(false)

// 发送邮箱验证码（发送到目标邮箱，供无邮箱用户绑定用）
const sendEmailCode = async () => {
  const email = emailInput.value.trim()
  if (!email) { showToast('请先输入邮箱', 'error'); return }
  sendingCode.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/send-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, type: 'login' })
    })
    const result = await res.json()
    if (res.ok) {
      showToast(result.message || '验证码已发送', 'success')
    } else {
      showToast(result.error || '发送失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    sendingCode.value = false
  }
}

// 确认绑定邮箱（调用 /api/user/bind-email）
const confirmBindEmail = async () => {
  const email = emailInput.value.trim()
  const code = codeInput.value.trim()
  if (!email || !code) { showToast('请填写邮箱和验证码', 'error'); return }
  binding.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/bind-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({ email, code })
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, email, has_email: true })
      showEmailBind.value = false
      showToast(result.message || '邮箱绑定成功', 'success')
      loadProfile()
    } else {
      showToast(result.error || '绑定失败', 'error')
    }
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    binding.value = false
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
.referral-section { margin-top: 16px; }
.referral-hint { color: #909399; font-size: 13px; margin: 0 0 8px; }
.email-bind-form { margin-top: 10px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.email-bind-form input { padding: 6px 10px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 13px; min-width: 160px; }
.bind-btn { padding: 6px 16px; background-color: #24292e; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.bind-btn:hover { background-color: #000; }
.unbind-btn { padding: 6px 16px; background-color: #fff; color: #f56c6c; border: 1px solid #f56c6c; border-radius: 4px; cursor: pointer; font-size: 13px; }
.unbind-btn:hover { background-color: #fef0f0; }
</style>