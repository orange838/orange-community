<template>
  <div class="page-container admin-page">
    <div class="admin-header">
      <h2>🛠️ 后台管理</h2>
    </div>

    <div class="admin-card">
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { currentUser } from '../store'

const users = ref([])
const loading = ref(true)

const isProtectedUser = (user) => {
  const email = (user?.email || '').trim()
  const username = (user?.username || '').trim()
  return email === '3659793158@qq.com' || username === 'orange'
}

const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

const loadUsers = async () => {
  if (!currentUser.info?.email) return

  loading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users?email=${encodeURIComponent(currentUser.info.email)}`)
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_email: currentUser.info.email,
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
  } catch (error) {
    showToast(error.message || '更新失败', 'error')
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.page-container { min-height: 100%; }
.admin-page { display: flex; flex-direction: column; gap: 16px; }
.admin-header { background: #fff; border-radius: 8px; padding: 20px 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.admin-header h2 { margin: 0; color: #333; }
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
