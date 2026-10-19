<template>
  <div class="page-container tasks-page">
    <h2>📋 任务中心</h2>

    <div class="tasks-layout">
      <nav class="tasks-nav" aria-label="任务分类">
        <div class="tasks-nav-group">
          <p class="tasks-nav-heading">日常任务</p>
          <button
            type="button"
            class="tasks-nav-item"
            :class="{ active: activeTask === 'checkin' }"
            :aria-current="activeTask === 'checkin' ? 'page' : undefined"
            @click="activeTask = 'checkin'"
          >每日签到</button>
        </div>
        <div class="tasks-nav-group">
          <p class="tasks-nav-heading">推广任务</p>
          <button
            type="button"
            class="tasks-nav-item"
            :class="{ active: activeTask === 'referral' }"
            :aria-current="activeTask === 'referral' ? 'page' : undefined"
            @click="activeTask = 'referral'"
          >拉新邀请码</button>
        </div>
      </nav>

      <section class="tasks-content">
        <template v-if="activeTask === 'checkin'">
          <h3>📅 每日签到</h3>
          <div class="task-card">
            <p>
              今日签到状态：
              <span :class="['checkin-state', { complete: isCheckedIn }]">
                {{ isCheckedIn ? '已签到' : '未签到' }}
              </span>
            </p>
            <button
              class="task-btn"
              :disabled="!hasEmailAccount || isCheckedIn || checkinLoading"
              @click="handleCheckIn"
            >
              {{ checkinLoading ? '签到中...' : isCheckedIn ? '已签到' : '点击签到' }}
            </button>
          </div>
        </template>

        <template v-else>
          <h3>📨 拉新邀请码</h3>
          <div class="task-card">
            <p>创建专属邀请链接，邀请新用户使用邮箱注册。</p>
            <p class="referral-note">目前只记录邀请关系，暂不发放奖励或其他权益。</p>
            <div v-if="referralCode" class="referral-code-row">
              <span>我的邀请码</span>
              <code>{{ referralCode }}</code>
            </div>
            <button
              v-if="!referralCode"
              class="task-btn"
              :disabled="!isAuthenticated || creatingReferralCode"
              @click="createReferralCode"
            >
              {{ creatingReferralCode ? '创建中...' : '创建拉新邀请码' }}
            </button>
            <button
              v-else
              class="task-btn"
              @click="copyReferralLink"
            >复制拉新链接</button>
            <p v-if="!isAuthenticated" class="referral-note">请先登录后创建和分享拉新邀请码。</p>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { currentUser } from '../store'

const activeTask = ref('checkin')
const checkinLoading = ref(false)
const isCheckedIn = ref(false)
const creatingReferralCode = ref(false)
const referralCode = ref(currentUser.info?.referral_code || '')
const isAuthenticated = computed(() => Boolean(currentUser.token))
const hasEmailAccount = computed(() => Boolean(currentUser.info?.email))

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const fetchProfile = async () => {
  if (!currentUser.token) {
    isCheckedIn.value = false
    referralCode.value = ''
    return
  }

  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (res.ok) {
      currentUser.setInfo({ ...currentUser.info, ...result })
      isCheckedIn.value = Boolean(result.has_checked_in_today)
      referralCode.value = result.referral_code || ''
    } else {
      showToast(result.error || '加载任务信息失败', 'error')
    }
  } catch {
    showToast('加载任务信息失败，请稍后重试', 'error')
  }
}

const handleCheckIn = async () => {
  if (!currentUser.info?.email) {
    showToast('请先登录后再签到', 'error')
    return
  }

  if (isCheckedIn.value) {
    showToast('今日已签到，请明天再来', 'error')
    return
  }

  checkinLoading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '签到失败')

    currentUser.setInfo({
      ...currentUser.info,
      orange_balance: result.orange_balance,
      last_sign_in_date: result.last_sign_in_date,
      sign_in_count: result.sign_in_count
    })
    isCheckedIn.value = true
    showToast(`签到成功，获得 ${result.points} 橙子币`, 'success')
  } catch (error) {
    showToast(error.message || '签到失败', 'error')
  } finally {
    checkinLoading.value = false
  }
}

const createReferralCode = async () => {
  if (!currentUser.token) {
    showToast('请先登录后创建拉新邀请码', 'error')
    return
  }

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

    referralCode.value = result.code
    currentUser.setInfo({ ...currentUser.info, referral_code: result.code })
    showToast('拉新邀请码已创建', 'success')
  } catch {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    creatingReferralCode.value = false
  }
}

const copyReferralLink = async () => {
  const link = `${window.location.origin}/?ref=${encodeURIComponent(referralCode.value)}`
  try {
    await navigator.clipboard.writeText(link)
    showToast('拉新链接已复制', 'success')
  } catch {
    showToast(`请手动复制：${link}`, 'error')
  }
}

onMounted(fetchProfile)
watch(() => currentUser.token, fetchProfile)
</script>

<style scoped>
.tasks-layout {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 20px;
  margin-top: 18px;
}

.tasks-nav {
  align-self: start;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.tasks-nav-group + .tasks-nav-group { margin-top: 18px; }
.tasks-nav-heading { margin: 4px 8px 8px; color: #909399; font-size: 13px; }
.tasks-nav-item {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #606266;
  text-align: left;
  cursor: pointer;
}
.tasks-nav-item:hover { background: #fff7eb; color: #e68a00; }
.tasks-nav-item.active { background: #fff0d6; color: #d97900; font-weight: 600; }

.tasks-content { min-width: 0; }
.tasks-content h3 { margin: 2px 0 14px; color: #303133; font-size: 19px; }
.task-card {
  padding: 26px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  color: #606266;
}
.checkin-state { color: #ff9900; font-weight: 700; }
.checkin-state.complete { color: #52c41a; }
.task-btn {
  margin-top: 16px;
  padding: 10px 22px;
  border: 0;
  border-radius: 4px;
  background: #ff9900;
  color: #fff;
  cursor: pointer;
  font-size: 15px;
}
.task-btn:hover:not(:disabled) { background: #e68a00; }
.task-btn:disabled { background: #dcdfe6; cursor: not-allowed; }
.referral-note { margin: 8px 0; color: #909399; font-size: 13px; }
.referral-code-row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
.referral-code-row code { padding: 6px 10px; border-radius: 4px; background: #f5f7fa; color: #303133; }

@media (max-width: 700px) {
  .tasks-layout { grid-template-columns: 1fr; gap: 14px; }
  .tasks-nav { display: flex; flex-wrap: wrap; gap: 10px 18px; }
  .tasks-nav-group + .tasks-nav-group { margin-top: 0; }
  .tasks-nav-group { flex: 1 1 130px; }
  .task-card { padding: 20px; }
}
</style>
