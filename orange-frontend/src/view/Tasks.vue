<template>
  <div class="page-container tasks-page">
    <h2>📋 任务中心</h2>

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
        <tbody>
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
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { currentUser } from '../store'

const checkinLoading = ref(false)
const isCheckedIn = ref(false)
const hasEmailAccount = computed(() => Boolean(currentUser.info?.email))

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const fetchProfile = async () => {
  if (!currentUser.token) {
    isCheckedIn.value = false
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

onMounted(fetchProfile)
watch(() => currentUser.token, fetchProfile)
</script>

<style scoped>
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
@media (max-width: 700px) {
  .task-list { min-width: 640px; }
  .task-list th,
  .task-list td { padding: 12px 10px; }
}
</style>
