<template>
  <div class="page-container">
    <h2>📅 每日签到</h2>
    <div class="sign-card">
      <p>
        今日签到状态：
        <span :style="{ color: isCheckedIn ? '#52c41a' : '#ff9900', fontWeight: 'bold' }">
          {{ isCheckedIn ? '已签到' : '未签到' }}
        </span>
      </p>

      <button
        class="sign-btn"
        :disabled="!isLoggedIn || isCheckedIn || loading"
        @click="handleCheckIn"
      >
        {{ loading ? '签到中...' : isCheckedIn ? '已签到' : '点击签到' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { currentUser } from '../store'

const loading = ref(false)
const isCheckedIn = ref(false)
const isLoggedIn = computed(() => Boolean(currentUser.info?.email))

const fetchProfile = async () => {
  if (!currentUser.info?.email) {
    isCheckedIn.value = false
    return
  }

  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/profile?email=${encodeURIComponent(currentUser.info.email)}`)
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, ...result })
      isCheckedIn.value = Boolean(result.has_checked_in_today)
    } else {
      isCheckedIn.value = false
    }
  } catch {
    isCheckedIn.value = false
  }
}

const handleCheckIn = async () => {
  if (!currentUser.info?.email) {
    window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: '请先登录后再签到', type: 'error' } }))
    return
  }

  if (isCheckedIn.value) {
    window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: '今日已签到，请明天再来', type: 'error' } }))
    return
  }

  loading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: currentUser.info.email })
    })
    const result = await res.json()

    if (!res.ok) {
      throw new Error(result.error || '签到失败')
    }

    currentUser.setInfo({ ...currentUser.info, orange_balance: result.orange_balance, last_sign_in_date: result.last_sign_in_date, sign_in_count: result.sign_in_count })
    isCheckedIn.value = true
    window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: `签到成功，获得 ${result.points} 橙子币`, type: 'success' } }))
  } catch (error) {
    window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: error.message || '签到失败', type: 'error' } }))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProfile()
})
</script>

<style scoped>
.sign-card {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  margin-top: 15px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
}
.sign-btn {
  margin-top: 20px;
  padding: 10px 30px;
  background: #ff9900;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}
.sign-btn:hover:not(:disabled) { background: #e68a00; }
.sign-btn:disabled {
  background: #dcdfe6;
  cursor: not-allowed;
}
</style>