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
      <button
        class="admin-tab"
        :class="{ active: activeTab === 'invites' }"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'invites'"
        @click="activeTab = 'invites'"
      >
        邀请码
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
              <th>封禁状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.username }}</td>
              <td>{{ user.email || '未绑定' }}</td>
              <td>
                <input
                  v-model.number="user.orange_balance"
                  type="number"
                  min="0"
                  class="balance-input"
                />
              </td>
              <td>
                <select
                  v-model="user.role"
                  class="role-select"
                  :disabled="(isProtectedUser(user) && !canManageSuperAdmins) || (user.role === 'super_admin' && !canManageSuperAdmins)"
                >
                  <option v-if="!isProtectedUser(user)" value="admin">管理员</option>
                  <option v-if="!isProtectedUser(user)" value="user">普通用户</option>
                  <option v-if="canManageSuperAdmins || user.role === 'super_admin'" value="super_admin">超级管理员</option>
                </select>
              </td>
              <td>
                <span :class="user.is_banned ? 'ban-state banned' : 'ban-state'">
                  {{ user.is_banned ? (user.banned_until ? `临时封禁 ${user.ban_duration_days} 天，至 ${formatLogTime(user.banned_until)}` : '永久封禁') : '正常' }}
                </span>
                <small v-if="user.is_banned && user.ban_reason" class="ban-reason">原因：{{ user.ban_reason }}</small>
              </td>
              <td>
                <button class="save-btn" @click="saveUser(user)">保存</button>
                <button v-if="canBan(user) && !user.is_banned" class="ban-btn" @click="openBanDialog(user)">封禁</button>
                <button v-if="canBan(user) && user.is_banned" class="unban-btn" @click="unbanUser(user)">解封</button>
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

    <div v-if="activeTab === 'invites'" class="admin-card">
      <p class="admin-label">邀请码管理</p>

      <div class="invite-create">
        <span>有效期</span>
        <input v-model.number="inviteDays" type="number" min="1" max="365" class="balance-input" />
        <span>天</span>
        <button class="save-btn" :disabled="generating" @click="createInvite">{{ generating ? '生成中…' : '生成邀请码' }}</button>
        <p class="invite-hint">邀请码一次性使用，无邮箱用户可凭邀请码注册（以用户名记录，之后可绑定邮箱）。</p>
      </div>

      <div v-if="invitesLoading" class="status-box">正在加载邀请码...</div>
      <div v-else-if="invites.length === 0" class="status-box empty">暂无邀请码，点击上方按钮生成。</div>
      <div v-else class="table-wrap">
        <table class="user-table">
          <thead>
            <tr>
              <th>邀请码</th>
              <th>创建人</th>
              <th>创建时间</th>
              <th>过期时间</th>
              <th>状态</th>
              <th>注册链接</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in invites" :key="inv.id">
              <td><code class="invite-code">{{ inv.code }}</code></td>
              <td>{{ inv.created_by || '-' }}</td>
              <td>{{ formatLogTime(inv.created_at) }}</td>
              <td>{{ inv.expires_at ? formatLogTime(inv.expires_at) : '-' }}</td>
              <td>
                <span :class="['inv-status', inv.status]">{{ inv.status === 'active' ? '可用' : inv.status === 'expired' ? '已过期' : '已使用' }}</span>
              </td>
              <td>
                <button v-if="inv.status === 'active'" class="save-btn" @click="copyInvite(inv.code)">复制链接</button>
                <span v-else class="used-by">{{ inv.status === 'used' ? '用户名：' + (inv.used_by_name || inv.used_by || '-') : '—' }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="banTarget" class="ban-modal-mask" @click.self="closeBanDialog">
      <section class="ban-modal">
        <h3>封禁账号：{{ banTarget.username }}</h3>
        <label>
          封禁类型
          <select v-model="banType" class="ban-control">
            <option value="permanent">永久封禁</option>
            <option value="temporary">临时封禁</option>
          </select>
        </label>
        <label v-if="banType === 'temporary'">
          封禁天数
          <input v-model="banDays" class="ban-control" type="number" min="1" step="1" placeholder="请输入正整数天数" />
        </label>
        <label>
          封禁原因（必填，用户登录时可见）
          <textarea v-model="banReason" class="ban-control" maxlength="500" rows="4" placeholder="请填写封禁原因"></textarea>
        </label>
        <div class="ban-modal-actions">
          <button class="save-btn" :disabled="banSaving" @click="banUser">{{ banSaving ? '处理中…' : '确认封禁' }}</button>
          <button class="cancel-btn" :disabled="banSaving" @click="closeBanDialog">取消</button>
        </div>
      </section>
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
const canManageSuperAdmins = ref(false)
const banTarget = ref(null)
const banType = ref('permanent')
const banDays = ref('')
const banReason = ref('')
const banSaving = ref(false)

// 邀请码状态
const invites = ref([])
const invitesLoading = ref(true)
const inviteDays = ref(7)
const generating = ref(false)

const isProtectedUser = (user) => Boolean(user?.is_protected)
const isSelf = (user) =>
  (user.email && user.email === currentUser.info?.email) ||
  user.username === currentUser.info?.username
const canBan = (user) =>
  !isProtectedUser(user) &&
  user.role !== 'super_admin' &&
  !isSelf(user)

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

const loadInvites = async () => {
  if (!currentUser.token) return

  invitesLoading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/invites`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '加载失败')
    invites.value = result.invites || []
  } catch (error) {
    showToast(error.message || '加载邀请码失败', 'error')
  } finally {
    invitesLoading.value = false
  }
}

const createInvite = async () => {
  if (!currentUser.token) {
    showToast('未登录，无法生成邀请码', 'error')
    return
  }
  const days = Number(inviteDays.value)
  if (!Number.isInteger(days) || days <= 0) {
    showToast('有效期天数请填写大于 0 的整数', 'error')
    return
  }
  generating.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/invites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({ expires_in_days: days })
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '生成失败')
    showToast(`邀请码已生成：${result.code}`, 'success')
    await loadInvites()
  } catch (error) {
    showToast(error.message || '生成失败', 'error')
  } finally {
    generating.value = false
  }
}

const copyInvite = async (code) => {
  const link = `${window.location.origin}/?invite=${code}`
  try {
    await navigator.clipboard.writeText(link)
    showToast('注册链接已复制', 'success')
  } catch {
    showToast(`请手动复制：${link}`, 'error')
  }
}

const loadLogs = async () => {
  if (!currentUser.token) return

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
  if (!currentUser.token) return

  loading.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const result = await res.json()

    if (!res.ok) {
      throw new Error(result.error || '加载失败')
    }

    canManageSuperAdmins.value = result.can_manage_super_admins === true
    users.value = (result.users || []).map((user) => ({
      ...user,
      original_role: user.role,
      orange_balance: Number(user.orange_balance || 0)
    }))
  } catch (error) {
    showToast(error.message || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

const saveUser = async (user) => {
  if (!currentUser.token) {
    showToast('未登录，无法更新用户信息', 'error')
    return
  }

  const protectedUser = isProtectedUser(user)
  const self = isSelf(user)

  if (protectedUser && user.role !== 'super_admin') {
    showToast('orange 账号应设为超级管理员', 'error')
    user.role = user.original_role
    return
  }

  if (self && !['admin', 'super_admin'].includes(user.role)) {
    showToast('管理员不能将自己设置为普通用户', 'error')
    user.role = currentUser.info.role
    return
  }

  if (user.role !== user.original_role &&
      (user.role === 'super_admin' || user.original_role === 'super_admin') &&
      !canManageSuperAdmins.value) {
    showToast('只有 orange 账号可以授予或撤销超级管理员权限', 'error')
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
    await loadUsers()
    await loadLogs()
  } catch (error) {
    showToast(error.message || '更新失败', 'error')
  }
}

const openBanDialog = (user) => {
  banTarget.value = user
  banType.value = 'permanent'
  banDays.value = ''
  banReason.value = ''
}

const closeBanDialog = () => {
  if (banSaving.value) return
  banTarget.value = null
}

const banUser = async () => {
  if (!banTarget.value) return
  const reason = banReason.value.trim()
  if (!reason) return showToast('请填写封禁原因', 'error')
  let durationDays = null
  if (banType.value === 'temporary') {
    durationDays = Number(banDays.value)
    if (!Number.isSafeInteger(durationDays) || durationDays <= 0) {
      return showToast('临时封禁天数必须为正整数', 'error')
    }
  }

  banSaving.value = true
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users/ban`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({ id: banTarget.value.id, reason, duration_days: durationDays })
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '封禁失败')
    showToast(result.message || '账号已封禁', 'success')
    banTarget.value = null
    await loadUsers()
    await loadLogs()
  } catch (error) {
    showToast(error.message || '封禁失败', 'error')
  } finally {
    banSaving.value = false
  }
}

const unbanUser = async (user) => {
  const confirmed = await new Promise((resolve) => {
    window.dispatchEvent(new CustomEvent('show-confirm', {
      detail: { message: `确定解除「${user.username}」的封禁并恢复发帖权限吗？`, resolve }
    }))
  })
  if (!confirmed) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/users/unban`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({ id: user.id })
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || '解封失败')
    showToast(result.message || '已解除封禁', 'success')
    await loadUsers()
    await loadLogs()
  } catch (error) {
    showToast(error.message || '解封失败', 'error')
  }
}

onMounted(() => {
  loadUsers()
  loadLogs()
  loadInvites()
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
.ban-state { display: block; color: #67c23a; }
.ban-state.banned { color: #c45656; font-weight: 700; }
.ban-reason { display: block; margin-top: 5px; color: #606266; max-width: 260px; white-space: normal; }
.ban-btn, .unban-btn, .cancel-btn { margin-left: 6px; padding: 8px 12px; border: 0; border-radius: 6px; cursor: pointer; }
.ban-btn { background: #f56c6c; color: #fff; }
.unban-btn { background: #67c23a; color: #fff; }
.cancel-btn { background: #f2f3f5; color: #606266; }
.ban-modal-mask { position: fixed; inset: 0; z-index: 3000; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(0, 0, 0, 0.45); }
.ban-modal { width: min(520px, 100%); padding: 24px; border-radius: 10px; background: #fff; box-shadow: 0 12px 36px rgba(0, 0, 0, 0.2); }
.ban-modal h3 { margin: 0 0 20px; }
.ban-modal label { display: block; margin: 14px 0; color: #606266; }
.ban-control { display: block; box-sizing: border-box; width: 100%; margin-top: 7px; padding: 9px 10px; border: 1px solid #dcdfe6; border-radius: 6px; font: inherit; }
.ban-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
.save-btn { padding: 8px 16px; border: none; border-radius: 6px; background: #ff9900; color: #fff; cursor: pointer; }
.save-btn:hover { background: #f28b00; }
.save-btn:disabled { background: #ffc98a; cursor: not-allowed; }
.invite-create { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }
.invite-create .balance-input { width: 80px; }
.invite-hint { width: 100%; margin: 4px 0 0; color: #909399; font-size: 13px; }
.invite-code { background: #fff7eb; padding: 3px 8px; border-radius: 4px; color: #8a5a00; font-weight: 700; letter-spacing: 1px; }
.inv-status { padding: 2px 10px; border-radius: 4px; font-size: 12px; }
.inv-status.active { background: #f0f9eb; color: #67c23a; }
.inv-status.used { background: #f4f4f5; color: #909399; }
.inv-status.expired { background: #fef0f0; color: #f56c6c; }
.used-by { color: #909399; font-size: 13px; }
</style>
