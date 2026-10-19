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

    <section class="task-list-wrap">
      <table class="task-list">
        <thead>
          <tr>
            <th class="task-icon-column">图标</th>
            <th>任务名称</th>
            <th>任务描述</th>
            <th>奖励</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody v-if="activeCategory === 'daily'">
          <tr>
            <td class="task-icon-cell"><span class="task-icon checkin-icon">📅</span></td>
            <td class="task-name">
              每日签到
              <span v-if="isCheckedIn" class="task-status">已签到</span>
            </td>
            <td>每天签到获得 5 橙子币。</td>
            <td class="task-reward">+5 / 天</td>
            <td>
              <button
                class="task-btn"
                :disabled="!hasEmailAccount || isCheckedIn || checkinLoading"
                @click="handleCheckIn"
              >{{ checkinLoading ? '签到中…' : isCheckedIn ? '已签到' : '签到' }}</button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td class="task-icon-cell"><span class="task-icon referral-icon">🔗</span></td>
            <td class="task-name">拉新邀请码</td>
            <td>
              分享专属链接邀请新用户邮箱注册；目前只记录邀请关系，暂无奖励。
              <p v-if="referralLoading" class="referral-note">正在为你准备专属邀请码…</p>
              <code v-else-if="referralCode" class="referral-code">{{ referralCode }}</code>
              <p v-else-if="!isAuthenticated" class="referral-note">请先登录，系统会自动为你准备邀请码。</p>
            </td>
            <td class="task-reward">暂无</td>
            <td>
              <button
                v-if="referralCode"
                class="task-btn"
                @click="copyReferralLink"
              >复制链接</button>
              <button
                v-else-if="isAuthenticated"
                class="task-btn"
                :disabled="referralLoading"
                @click="ensureReferralCode"
              >重试</button>
              <span v-else class="task-action-muted">登录后可用</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { currentUser } from '../store'

const activeCategory = ref('daily')
const checkinLoading = ref(false)
const isCheckedIn = ref(false)
const referralLoading = ref(false)
const referralCode = ref(currentUser.info?.referral_code || '')
const isAuthenticated = computed(() => Boolean(currentUser.token))
const hasEmailAccount = computed(() => Boolean(currentUser.info?.email))

const selectCategory = (category) => {
  activeCategory.value = category
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
.task-categories {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  border-bottom: 1px solid #ebeef5;
}

.task-categories { margin-top: 16px; }
.task-category {
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
.task-category:hover { color: #e68a00; }
.task-category.active { border-bottom-color: #ff9900; color: #d97900; }

.task-list-wrap {
  margin-top: 14px;
  overflow-x: auto;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
.task-list {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
  color: #606266;
  font-size: 14px;
}
.task-list th,
.task-list td {
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  text-align: left;
  vertical-align: middle;
}
.task-list th { background: #f7f8fa; color: #606266; font-weight: 600; }
.task-list tbody tr:last-child td { border-bottom: 0; }
.task-icon-column { width: 64px; }
.task-icon-cell { width: 64px; }
.task-icon {
  display: inline-flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 20px;
}
.checkin-icon { background: #fff2d8; }
.referral-icon { background: #f0eaff; }
.task-name { min-width: 150px; color: #303133; font-weight: 600; }
.task-status {
  display: inline-block;
  margin-left: 8px;
  padding: 3px 7px;
  border-radius: 12px;
  background: #e8f7ef;
  color: #31a56b;
  font-size: 12px;
  white-space: nowrap;
}
.task-reward { min-width: 90px; color: #d97900; font-weight: 600; white-space: nowrap; }
.referral-code {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f5f7fa;
  color: #303133;
}
.task-btn {
  padding: 8px 14px;
  border: 0;
  border-radius: 4px;
  background: #ff9900;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}
.task-btn:hover:not(:disabled) { background: #e68a00; }
.task-btn:disabled { background: #dcdfe6; cursor: not-allowed; }
.referral-note { margin: 8px 0; color: #909399; font-size: 13px; }
.task-action-muted { color: #909399; white-space: nowrap; }

@media (max-width: 700px) {
  .task-category { padding: 11px 14px; }
  .task-list { min-width: 640px; }
  .task-list th,
  .task-list td { padding: 12px 10px; }
}
</style>
