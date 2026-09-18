<template>
  <div class="page-container admin-page">
    <div class="admin-header">
      <h2>🛠️ 后台管理</h2>
    </div>

    <div class="admin-tabs" role="tablist" aria-label="后台功能">
      <button
        class="admin-tab"
        :class="{ active: activeTab === 'users' }"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'users'"
        @click="activeTab = 'users'"
      >
        用户管理
      </button>
      <button
        class="admin-tab"
        :class="{ active: activeTab === 'logs' }"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'logs'"
        @click="activeTab = 'logs'"
      >
        操作日志
      </button>
    </div>

    <div v-if="activeTab === 'users'" class="admin-card">
      <p class="admin-label">用户管理</p>

      <div v-if="loading" class="status-box">正在加载用户列表...</div>
      <div v-else-if="users.length === 0" class="status-box empty">暂无用户数据。</div>

      <div v-else class="table-wrap">
        <table class="user-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>邮箱</th>
              <th>橙子数量</th>
              <th>角色</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td>
                <input
                  v-model.number="user.orange_balance"
                  type="number"
                  min="0"
                  class="balance-input"
                />
              </td>
              <td>
                <select v-model="user.role" class="role-select" :disabled="isProtectedUser(user)">
                  <option value="admin">管理员</option>
                  <option value="user">普通用户</option>
                </select>
              </td>
              <td>
                <button class="save-btn" @click="saveUser(user)">保存</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="activeTab === 'logs'" class="admin-card">
      <p class="admin-label">操作日志</p>
      <div v-if="logsLoading" class="status-box">正在加载操作日志...</div>
      <div v-else-if="logs.length === 0" class="status-box empty">暂无操作记录。</div>
      <div v-else class="table-wrap">
        <table class="user-table">
          <thead>
            <tr>
              <th>操作时间</th>
              <th>操作者</th>
              <th>操作</th>
              <th>详细说明</th>
              <th>接口</th>
              <th>结果</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ formatLogTime(log.created_at) }}</td>
              <td>{{ log.actor_username || log.actor_email || '未登录用户' }}</td>
              <td>{{ log.action }}</td>
              <td>{{ log.action_detail }}</td>
              <td>{{ log.path }}</td>
              <td>{{ log.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { currentUser } from '../store'

const users = ref([])
const loading = ref(true)
const logs = ref([])
const logsLoading = ref(true)
const activeTab = ref('users')

const isProtectedUser = (user) => Boolean(user?.is_protected)

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const formatLogTime = (value) => {
  if (!value) return '未知时间'
  const raw = String(value)
  const normalized = raw.includes('T') ? raw : `${raw.replace(' ', 'T')}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return raw
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(date).replace(/\//g, '-')
}

const loadLogs = async () => {
  if (!currentUser.info?.email) return

  logsLoading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/logs`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '日志加载失败')
    logs.value = result.logs || []
  } catch (error) {
    showToast(error.message || '日志加载失败', 'error')
  } finally {
    logsLoading.value = false
  }
}

const loadUsers = async () => {
  if (!currentUser.info?.email) return

  loading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()

    if (!res.ok) {
      throw new Error(result.error || '加载失败')
    }

    users.value = (result.users || []).map((user) => ({
      ...user,
      orange_balance: Number(user.orange_balance || 0)
    }))
  } catch (error) {
    showToast(error.message || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

const saveUser = async (user) => {
  if (!currentUser.info?.email) {
    showToast('未登录，无法更新用户信息', 'error')
    return
  }

  const protectedUser = isProtectedUser(user)
  const isSelf = user.email === currentUser.info.email

  if (protectedUser && user.role !== 'admin') {
    showToast('orange 账号禁止设置为普通用户', 'error')
    user.role = 'admin'
    return
  }

  if (isSelf && user.role !== 'admin') {
    showToast('管理员不能将自己设置为普通用户', 'error')
    user.role = 'admin'
    return
  }

  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({
        id: user.id,
        orange_balance: Number(user.orange_balance || 0),
        role: user.role
      })
    })

    const result = await res.json()
    if (!res.ok) {
      throw new Error(result.error || '更新失败')
    }

    showToast(result.message || '更新成功', 'success')
    await loadLogs()
  } catch (error) {
    showToast(error.message || '更新失败', 'error')
  }
}

onMounted(() => {
  loadUsers()
  loadLogs()
})
</script>

<style scoped>
.page-container { min-height: 100%; }
.admin-page { display: flex; flex-direction: column; gap: 16px; }
.admin-header { background: #fff; border-radius: 8px; padding: 20px 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.admin-header h2 { margin: 0; color: #333; }
.admin-tabs { display: flex; gap: 8px; padding: 4px; background: #fff7eb; border-radius: 8px; }
.admin-tab { flex: 1; padding: 11px 16px; border: none; border-radius: 6px; background: transparent; color: #8a5a00; font-size: 15px; cursor: pointer; }
.admin-tab.active { background: #ff9900; color: #fff; font-weight: 700; }
.admin-card { background: #fff; border-radius: 8px; padding: 28px 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); border-left: 4px solid #ff9900; }
.admin-label { margin: 0 0 18px; font-size: 18px; font-weight: 700; color: #333; }
.status-box { padding: 20px; border-radius: 8px; background: #fafafa; color: #606266; }
.status-box.empty { color: #909399; }
.table-wrap { overflow-x: auto; }
.user-table { width: 100%; border-collapse: collapse; }
.user-table th, .user-table td { padding: 14px 12px; border-bottom: 1px solid #f0f2f5; text-align: left; }
.user-table th { color: #606266; font-size: 14px; }
.user-table td { color: #333; }
.balance-input, .role-select { width: 120px; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 6px; font-size: 14px; }
.role-select { width: 110px; }
.save-btn { padding: 8px 16px; border: none; border-radius: 6px; background: #ff9900; color: #fff; cursor: pointer; }
.save-btn:hover { background: #f28b00; }
</style>
