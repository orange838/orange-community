<template>
  <div class="page-container">
    <h2>👤 个人中心</h2>
    <nav class="profile-tabs" aria-label="个人中心分类">
      <button type="button" :class="{ active: activeTab === 'overview' }" :aria-pressed="activeTab === 'overview'" @click="activeTab = 'overview'">个人信息</button>
      <button type="button" :class="{ active: activeTab === 'promotion' }" :aria-pressed="activeTab === 'promotion'" @click="activeTab = 'promotion'">推广中心</button>
      <button type="button" :class="{ active: activeTab === 'orange-log' }" :aria-pressed="activeTab === 'orange-log'" @click="activeTab = 'orange-log'">橙子日志</button>
    </nav>

    <section v-if="activeTab === 'overview'">
      <div class="profile-card">
      <template v-if="currentUser.info">
        <p>当前状态：<span style="color: #ff9900; font-weight: bold;">已登录</span></p>
        <p>用户名：{{ currentUser.info.username }}</p>
        <p>邮箱：{{ currentUser.info.email || '未绑定' }}</p>
        <p v-if="['admin', 'super_admin'].includes(currentUser.info.role)">
          角色：{{ currentUser.info.role === 'super_admin' ? '超级管理员' : '管理员' }}
        </p>
        <p>橙子余额：{{ currentUser.info.orange_balance ?? 0 }}</p>
        <p>签到记录：已签到 {{ currentUser.info.sign_in_count ?? 0 }} 次</p>
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
    </section>

    <section v-else-if="activeTab === 'promotion'" class="promotion-card">
      <h3>🔗 我的邀请链接</h3>
      <p class="promotion-description">好友使用你的邀请码注册，你获得 10 橙子币；好友每日签到，你再获得 2 橙子币。</p>
      <div v-if="currentUser.info" class="promotion-link">
        <code v-if="referralCode">{{ referralLink }}</code>
        <span v-else>{{ profileLoading || referralLoading ? '正在为你准备专属邀请链接…' : '邀请链接暂不可用，请稍后重试。' }}</span>
        <button type="button" class="bind-btn" :disabled="!referralCode || referralLoading" @click="copyReferralLink">复制链接</button>
      </div>
      <p v-else class="promotion-description">请先登录，系统会自动为你准备专属邀请链接。</p>
      <button
        v-if="currentUser.info && !referralCode && !profileLoading && !referralLoading"
        type="button"
        class="bind-btn"
        @click="ensureReferralCode"
      >重试</button>
      <p v-if="referralCode" class="promotion-code">你的拉新邀请码：<code>{{ referralCode }}</code></p>
    </section>

    <section v-else class="orange-log-card">
      <h3>橙子收支记录</h3>
      <p v-if="!currentUser.info" class="orange-log-message">请先登录后查看橙子日志。</p>
      <p v-else-if="orangeTransactionsLoading" class="orange-log-message">正在加载橙子日志…</p>
      <p v-else-if="!orangeTransactions.length" class="orange-log-message">暂无橙子变动记录。</p>
      <div v-else class="orange-log-table-wrap">
        <table class="orange-log-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>变动</th>
              <th>变动后余额</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="transaction in orangeTransactions" :key="transaction.id">
              <td>{{ formatOrangeTransactionDate(transaction.created_at) }}</td>
              <td :class="transaction.amount > 0 ? 'orange-log-credit' : 'orange-log-debit'">
                {{ transaction.amount > 0 ? '+' : '' }}{{ transaction.amount }}
              </td>
              <td>{{ transaction.balance_after ?? '—' }}</td>
              <td>{{ transaction.description }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { currentUser } from '../store'

const route = useRoute()
const activeTab = ref('overview')
const referralCode = ref('')
const referralLoading = ref(false)
const profileLoading = ref(false)
const orangeTransactions = ref([])
const orangeTransactionsLoading = ref(false)
const referralLink = computed(() => `${window.location.origin}/?ref=${encodeURIComponent(referralCode.value)}`)
const isMixedReferralCode = (code) => code.length === 6 && /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{6}$/.test(code)

const loadProfile = async () => {
  if (!currentUser.info?.username) {
    referralCode.value = ''
    return
  }

  profileLoading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, ...result })
      referralCode.value = result.referral_code || ''
      if (!isMixedReferralCode(referralCode.value)) await ensureReferralCode()
    } else {
      showToast(result.error || '加载个人信息失败', 'error')
    }
  } catch {
    showToast('加载个人信息失败，请稍后重试', 'error')
  } finally {
    profileLoading.value = false
  }
}

onMounted(() => {
  loadProfile()
  // 从“未绑定邮箱”提醒跳转过来时，自动展开绑定表单
  if (route.query.bind === '1') {
    activeTab.value = 'overview'
    showEmailBind.value = true
  }
})

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const ensureReferralCode = async () => {
  if (isMixedReferralCode(referralCode.value) || referralLoading.value || !currentUser.token) return
  referralLoading.value = true
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
    referralCode.value = result.code
    currentUser.setInfo({ ...currentUser.info, referral_code: result.code })
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    referralLoading.value = false
  }
}

const copyReferralLink = async () => {
  if (!referralCode.value) return
  try {
    await navigator.clipboard.writeText(referralLink.value)
    showToast('推广链接已复制', 'success')
  } catch {
    showToast(`请手动复制：${referralLink.value}`, 'error')
  }
}

const loadOrangeTransactions = async () => {
  if (!currentUser.token) {
    orangeTransactions.value = []
    return
  }
  orangeTransactionsLoading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/orange-transactions`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (!res.ok) {
      showToast(result.error || '加载橙子日志失败', 'error')
      return
    }
    orangeTransactions.value = result.transactions || []
  } catch {
    showToast('加载橙子日志失败，请稍后重试', 'error')
  } finally {
    orangeTransactionsLoading.value = false
  }
}

const formatOrangeTransactionDate = (value) => {
  if (!value) return '—'
  const timestamp = String(value)
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(timestamp)
    ? timestamp
    : `${timestamp.replace(' ', 'T')}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString()
}

watch([activeTab, () => currentUser.token], ([tab, token]) => {
  if (tab === 'orange-log' && token) {
    loadOrangeTransactions()
  } else if (!token) {
    orangeTransactions.value = []
  }
})

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

watch(() => [currentUser.info?.username, currentUser.info?.email], () => {
  loadProfile()
})
</script>

<style scoped>
.profile-tabs {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  overflow-x: auto;
  border-bottom: 1px solid #ebeef5;
}

.profile-tabs button {
  flex: 0 0 auto;
  padding: 12px 18px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: #606266;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.profile-tabs button:hover { color: #e68a00; }
.profile-tabs button.active { border-bottom-color: #ff9900; color: #d97900; }

.profile-card {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  margin-top: 15px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
  line-height: 1.8;
}

.promotion-card {
  margin-top: 15px;
  padding: 24px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
}

.promotion-card h3 { margin: 0; color: #303133; }
.promotion-description { margin: 8px 0 14px; color: #909399; }
.promotion-link { display: flex; align-items: center; gap: 10px; }
.promotion-link code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f5f7fa;
  color: #303133;
}
.promotion-code { margin: 14px 0 0; }
.promotion-code code { padding: 3px 7px; border-radius: 4px; background: #f5f7fa; color: #303133; }

.orange-log-card {
  margin-top: 15px;
  padding: 24px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
}

.orange-log-card h3 { margin: 0 0 14px; color: #303133; }
.orange-log-message { color: #909399; }
.orange-log-table-wrap { overflow-x: auto; }
.orange-log-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.orange-log-table th,
.orange-log-table td { padding: 12px; border-bottom: 1px solid #ebeef5; text-align: left; white-space: nowrap; }
.orange-log-table th { background: #f7f8fa; font-weight: 600; }
.orange-log-table tbody tr:last-child td { border-bottom: 0; }
.orange-log-credit { color: #31a56b; font-weight: 600; }
.orange-log-debit { color: #f56c6c; font-weight: 600; }

.github-bind { margin-top: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.email-bind-form { margin-top: 10px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.email-bind-form input { padding: 6px 10px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 13px; min-width: 160px; }
.bind-btn { padding: 6px 16px; background-color: #24292e; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.bind-btn:hover { background-color: #000; }
.unbind-btn { padding: 6px 16px; background-color: #fff; color: #f56c6c; border: 1px solid #f56c6c; border-radius: 4px; cursor: pointer; font-size: 13px; }
.unbind-btn:hover { background-color: #fef0f0; }

@media (max-width: 600px) {
  .promotion-link { align-items: stretch; flex-direction: column; }
}
</style>