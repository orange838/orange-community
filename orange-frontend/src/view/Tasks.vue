<template>
  <div class="page-container tasks-page">
    <h2>📋 任务中心</h2>

    <nav class="task-categories" aria-label="任务类别">
      <button
        type="button"
        class="task-category"
        :class="{ active: activeCategory === 'daily' }"
        :aria-pressed="activeCategory === 'daily'"
        @click="selectCategory('daily')"
      >日常任务</button>
      <button
        type="button"
        class="task-category"
        :class="{ active: activeCategory === 'promotion' }"
        :aria-pressed="activeCategory === 'promotion'"
        @click="selectCategory('promotion')"
      >推广任务</button>
    </nav>

    <section v-if="activeCategory" class="task-category-content">
      <nav class="task-options" aria-label="具体任务">
        <button
          v-if="activeCategory === 'daily'"
          type="button"
          class="task-option"
          :class="{ active: activeTask === 'checkin' }"
          :aria-pressed="activeTask === 'checkin'"
          @click="activeTask = 'checkin'"
        >每日签到</button>
        <button
          v-else
          type="button"
          class="task-option"
          :class="{ active: activeTask === 'referral' }"
          :aria-pressed="activeTask === 'referral'"
          @click="activeTask = 'referral'"
        >拉新邀请码</button>
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

        <template v-else-if="activeTask === 'referral'">
          <h3>📨 拉新邀请码</h3>
          <div class="task-card">
            <p>分享专属邀请链接，邀请新用户使用邮箱注册。</p>
            <p class="referral-note">目前只记录邀请关系，暂不发放奖励或其他权益。</p>
            <p v-if="referralLoading" class="referral-note">正在为你准备专属邀请码…</p>
            <div v-else-if="referralCode" class="referral-code-row">
              <span>我的邀请码</span>
              <code>{{ referralCode }}</code>
              <button class="task-btn" @click="copyReferralLink">复制拉新链接</button>
            </div>
            <button
              v-else-if="isAuthenticated"
              class="task-btn"
              :disabled="referralLoading"
              @click="ensureReferralCode"
            >重试加载邀请码</button>
            <p v-if="!isAuthenticated" class="referral-note">请先登录，系统会自动为你准备拉新邀请码。</p>
          </div>
        </template>
        <div v-else class="task-card task-prompt">请选择此类别下的具体任务。</div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { currentUser } from '../store'

const activeCategory = ref('daily')
const activeTask = ref(null)
const checkinLoading = ref(false)
const isCheckedIn = ref(false)
const referralLoading = ref(false)
const referralCode = ref(currentUser.info?.referral_code || '')
const isAuthenticated = computed(() => Boolean(currentUser.token))
const hasEmailAccount = computed(() => Boolean(currentUser.info?.email))

const selectCategory = (category) => {
  activeCategory.value = category
  activeTask.value = null
}

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
      if (!referralCode.value) await ensureReferralCode()
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

const ensureReferralCode = async () => {
  if (referralCode.value || referralLoading.value) return
  if (!currentUser.token) {
    return
  }

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
.task-categories,
.task-options {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  border-bottom: 1px solid #ebeef5;
}

.task-categories { margin-top: 16px; }
.task-category,
.task-option {
  flex: 0 0 auto;
  padding: 12px 18px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: #606266;
  cursor: pointer;
  white-space: nowrap;
}
.task-category { font-size: 16px; font-weight: 600; }
.task-option { padding: 10px 14px; font-size: 14px; }
.task-category:hover,
.task-option:hover { color: #e68a00; }
.task-category.active,
.task-option.active { border-bottom-color: #ff9900; color: #d97900; }

.task-category-content { margin-top: 12px; }
.task-options { border-bottom-color: #f2f3f5; }

.tasks-content { min-width: 0; margin-top: 14px; }
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
.referral-code-row .task-btn { margin-top: 0; }
.task-prompt { color: #909399; }

@media (max-width: 700px) {
  .task-category { padding: 11px 14px; }
  .task-card { padding: 20px; }
}
</style>
