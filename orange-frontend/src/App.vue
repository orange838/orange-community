<template>
  <!-- 登录/注册、人机验证：独立整页（不带侧边栏 / 顶栏 / 页脚） -->
  <div v-if="isBarePage" class="bare-shell">
    <router-view />
  </div>

  <div v-else class="app-container">
    <!-- 左侧侧边栏 -->
    <aside class="sidebar">
      <div class="logo">🍊 橙子社区</div>
      <ul class="nav-menu">
        <li><router-link to="/" active-class="active">首页</router-link></li>
        <li><router-link to="/posts" active-class="active">帖子广场</router-link></li>
        <li><router-link to="/tasks" active-class="active">任务中心</router-link></li>
        <li><router-link to="/notice" active-class="active">公告</router-link></li>
        <li><router-link to="/profile" active-class="active">个人中心</router-link></li>
        <li><a href="https://aeb.cslblog.dpdns.org" target="_blank" rel="noopener">AI错题本</a></li>
        <li v-if="isAdminRole(currentUser.info?.role)">
          <router-link to="/admin" active-class="active">后台</router-link>
        </li>
      </ul>

      <!-- 侧边栏底部：运行时长 + 仓库链接 -->
      <div class="sidebar-footer">
        <div class="uptime">本站已运行 {{ uptimeText }}</div>
        <a href="https://qm.qq.com/q/J1lkB9JoWc" target="_blank" rel="noopener">💬 加入 QQ 交流群</a>
        <a href="https://github.com/orange838/orange-community" target="_blank" rel="noopener">GitHub 仓库</a>
        <div class="switch-row">
          <span class="switch-side" :class="{ on: styleMode === 'classic' }">兼容</span>
          <button
            type="button"
            class="switch"
            role="switch"
            :aria-checked="styleMode === 'glass'"
            aria-label="切换新版亚克力 / 兼容纯色样式"
            @click="toggleStyleMode"
          >
            <span class="knob" :class="{ right: styleMode === 'glass' }"></span>
          </button>
          <span class="switch-side" :class="{ on: styleMode === 'glass' }">新版</span>
        </div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <div class="main-wrapper">
      <header class="top-header">
        <div class="auth-buttons">
          <!-- 根据登录状态显示不同内容 -->
          <template v-if="$user.info">
            <span class="username">👋 {{ $user.info.username }}</span>
            <!-- 消息铃铛 + 未读计数 -->
            <div class="msg-bell-wrap" @click="toggleMsgPanel">
              <span class="msg-bell">🔔</span>
              <span v-if="unreadCount > 0" class="msg-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
            </div>
            <!-- 消息面板 -->
            <div v-if="showMsgPanel" class="msg-panel">
              <div class="msg-panel-head">系统消息<button class="msg-close" @click="showMsgPanel = false">✕</button></div>
              <div v-if="msgList.length" class="msg-list">
                <div v-for="m in msgList" :key="m.id" class="msg-item">
                  <p class="msg-content">{{ m.content }}</p>
                  <span class="msg-time">{{ formatMsgTime(m.created_at) }}</span>
                </div>
              </div>
              <p v-else class="msg-empty">暂无消息</p>
            </div>
            <!-- 退出按钮 -->
            <button class="btn-logout" @click="handleLogout">退出登录</button>
          </template>
          <template v-else>
            <button class="btn-login" @click="router.push('/login?mode=login')">登录</button>
            <button class="btn-register" @click="router.push('/login?mode=register')">注册</button>
          </template>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>

      <!-- 页脚：DigitalPlat FreeDomain 徽章 -->
      <footer class="site-footer" style="display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:12px;">
        <a href="https://dashboard.digitalplat.org/signup?ref=AYxV65nOjF" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid #d6dbe7;border-radius:12px;background:#ffffff;color:#0f172a;text-decoration:none;font:500 13px/1.25 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;box-shadow:0 1px 2px rgba(15,23,42,0.06);"><span style="display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:9999px;background:#eff6ff;color:#1d4ed8;font:600 11px/1 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;letter-spacing:0.02em;text-transform:uppercase;">DigitalPlat</span><span style="display:flex;flex-direction:column;gap:2px;"><span style="font-weight:600;">本网站由 DigitalPlat FreeDomain 提供支持</span><span style="color:#475569;">来 DigitalPlat 免费领取域名</span></span></a>
        <a href="https://tudouai.cn/r/3n6bl5b" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid #fde68a;border-radius:12px;background:#fffbeb;color:#78350f;text-decoration:none;font:500 13px/1.25 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;box-shadow:0 1px 2px rgba(120,53,15,0.08);"><span style="display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:9999px;background:#fde68a;color:#92400e;font:600 11px/1 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;letter-spacing:0.02em;text-transform:uppercase;">土豆公益</span><span style="display:flex;flex-direction:column;gap:2px;"><span style="font-weight:600;">邀请你注册土豆公益</span><span style="color:#92400e;">免费开游戏联机服务器</span></span></a>
      </footer>
    </div>

  </div>

  <!-- 全局 Toast 组件：挂载在最外层，任何页面都能调用 -->
  <Toast ref="toastRef" />
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import Toast from './components/Toast.vue' // 引入 Toast
import { currentUser } from './store'
import { useRoute, useRouter } from 'vue-router'
import { useStyleMode } from './composables/useStyleMode'

const toastRef = ref(null) // 获取 Toast 组件实例
const router = useRouter()
const route = useRoute()
// 这些页面单独整页显示，不套左侧栏 / 顶栏 / 页脚
const BARE_PAGES = ['/login', '/captcha']

// ---- 样式模式：glass（新版亚克力）/ classic（兼容纯色），存 localStorage ----
const { styleMode, toggle: toggleStyleMode } = useStyleMode()
const isBarePage = computed(() => BARE_PAGES.includes(route.path))
const isAdminRole = (role) => role === 'admin' || role === 'super_admin'
let appMounted = false
// 开站时长：从站点上线那天开始算（要改开站日期就改下面这一行）
const SITE_LAUNCH = new Date('2026-08-28T00:00:00+08:00')
const uptimeText = ref('')
let uptimeTimer = null
function refreshUptime() {
  const totalSeconds = Math.max(0, Math.floor((Date.now() - SITE_LAUNCH.getTime()) / 1000))
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  uptimeText.value = `${days} 天 ${hours} 时 ${minutes} 分 ${seconds} 秒`
}
onMounted(() => {
  refreshUptime()
  uptimeTimer = setInterval(refreshUptime, 1000)
})
onBeforeUnmount(() => {
  if (uptimeTimer) clearInterval(uptimeTimer)
})

// ---- 错题本 SSO 授权（errbook_sso=1&origin=xxx 打开本站）----
const isSsoMode = ref(false)
const ssoOrigin = ref('')
const authAsked = ref(false)

function detectSso() {
  const p = new URLSearchParams(window.location.search)
  if (p.get('errbook_sso') !== '1') return false
  isSsoMode.value = true
  ssoOrigin.value = p.get('origin') || 'https://aeb.cslblog.dpdns.org'
  return true
}

function authorizeToErrbook() {
  const token = currentUser.token
  if (!token) return
  const target = ssoOrigin.value
  const win = window.opener || window.parent
  if (win) {
    win.postMessage({ type: 'errbook-sso', token }, target)
  }
  window.close()
}

function cancelToErrbook() {
  const target = ssoOrigin.value
  const win = window.opener || window.parent
  if (win) {
    win.postMessage({ type: 'errbook-sso', cancelled: true }, target)
  }
  window.close()
}

async function askAuth() {
  if (authAsked.value) return
  authAsked.value = true
  await checkBanStatus()
  const info = currentUser.info
  if (!info) return
  const ok = await toastRef.value.showConfirm(`是否授权账号「${info.username}」登录 AI 错题本？`)
  if (ok) authorizeToErrbook()
  else cancelToErrbook()
}

function handleSso() {
  if (!detectSso()) return
  if (!currentUser.info) {
    // 未登录：跳转独立登录页，登录成功后由 watch 触发授权
    router.push('/login?mode=login')
  } else {
    askAuth()
  }
}

// SSO 模式下，等待用户在弹窗内登录成功后自动询问授权
watch(currentUser.info, (val) => {
  if (isSsoMode.value && val && !authAsked.value) askAuth()
})

// 未绑定邮箱的账号：每次登录成功后提醒一次（常规登录与 SSO/OAuth 均生效）
// 注意：不能在 watch 里直接 { immediate: true }，因为 Toast 子组件在父组件 mount 后才挂载，
// immediate 同步触发时 toastRef.value 为 null，showConfirm 会被静默跳过且守卫已置位，永不弹。
// 改为函数 + watch（登录变化）+ onMounted（刷新时已有登录态）各调一次。
let emailReminded = false
const remindBindEmail = async () => {
  if (emailReminded) return
  if (!currentUser.info || currentUser.info.email) return
  if (await checkBanStatus()) return
  emailReminded = true
  const go = await toastRef.value?.showConfirm(
    '你的账号还没有绑定邮箱。绑定后可用于找回账号、接收登录验证码。要现在去绑定吗？'
  )
  if (go) router.push({ path: '/profile', query: { bind: '1' } })
}
watch(currentUser.info, () => { remindBindEmail() })

// 消息系统：顶部铃铛显示未读数，点击弹出消息面板（不再弹窗）
const unreadCount = ref(0)
const showMsgPanel = ref(false)
const msgList = ref([])
const msgTimer = ref(null)

const fetchUnread = async () => {
  if (!currentUser.token) return
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/messages`, {
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    if (!res.ok) return
    const data = await res.json()
    unreadCount.value = (data.messages || []).length
  } catch (e) { /* 忽略 */ }
}

const formatMsgTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(d).replace(/\//g, '-')
}

let checkedBanStatusToken = null
let checkedBanStatus = false
let pendingBanStatusToken = null
let pendingBanStatusCheck = null
const checkBanStatus = async () => {
  const token = currentUser.token
  if (!token || !currentUser.info) {
    checkedBanStatusToken = null
    checkedBanStatus = false
    return false
  }
  if (checkedBanStatusToken === token) return checkedBanStatus
  if (pendingBanStatusToken === token && pendingBanStatusCheck) {
    try {
      return await pendingBanStatusCheck
    } catch {
      return false
    }
  }

  pendingBanStatusToken = token
  pendingBanStatusCheck = (async () => {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/ban-status`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('封禁状态查询失败')
    const data = await res.json()
    const isBanned = Boolean(data.is_banned)
    if (isBanned) {
      const expiry = data.banned_until
        ? `临时封禁 ${data.duration_days ?? ''} 天，至 ${formatMsgTime(data.banned_until)}`
        : '永久封禁'
      const reason = data.reason ? `\n封禁原因：${data.reason}` : ''
      await toastRef.value?.showAlert(`你的账号已被${expiry}并禁言，目前不能发布帖子。${reason}`, '账号封禁提醒')
    }
    checkedBanStatusToken = token
    checkedBanStatus = isBanned
    return isBanned
  })()
  try {
    return await pendingBanStatusCheck
  } catch {
    window.dispatchEvent(new CustomEvent('show-toast', {
      detail: { msg: '无法读取账号封禁状态，请刷新页面重试', type: 'error' }
    }))
    return false
  } finally {
    if (pendingBanStatusToken === token) {
      pendingBanStatusToken = null
      pendingBanStatusCheck = null
    }
  }
}

const toggleMsgPanel = async () => {
  if (!currentUser.token) return
  showMsgPanel.value = !showMsgPanel.value
  if (showMsgPanel.value) {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/user/messages`, {
        headers: { Authorization: `Bearer ${currentUser.token}` }
      })
      if (res.ok) {
        const data = await res.json()
        msgList.value = data.messages || []
      }
      // 打开后标记已读并清空未读计数
      await fetch(`${import.meta.env.VITE_API_URL}/api/user/messages/read`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${currentUser.token}` }
      })
      unreadCount.value = 0
    } catch (e) { /* 忽略 */ }
  }
}

// 登录后拉取未读数并定时刷新；退出时清除定时器
watch(currentUser.info, (val) => {
  if (msgTimer.value) { clearInterval(msgTimer.value); msgTimer.value = null }
  if (val && currentUser.token) {
    fetchUnread()
    msgTimer.value = setInterval(fetchUnread, 30000)
  }
}, { immediate: true })

watch(() => currentUser.token, (token) => {
  if (token && appMounted) {
    checkBanStatus()
  } else if (!token) {
    checkedBanStatusToken = null
    checkedBanStatus = false
    pendingBanStatusToken = null
    pendingBanStatusCheck = null
  }
})

watch(() => currentUser.info, (user, previousUser) => {
  if (user && !previousUser && currentUser.token && appMounted) {
    checkedBanStatusToken = null
    checkedBanStatus = false
    checkBanStatus()
  }
})

const handleOpenLoginModal = () => router.push('/login?mode=login')

const handleGlobalToast = (event) => {
  const { msg, type = 'success' } = event.detail || {}
  if (msg && toastRef.value?.showToast) {
    toastRef.value.showToast(msg, type)
  }
}

// 全局「仅提示」弹窗：只有一个确认按钮
const handleGlobalAlert = (event) => {
  const { msg, title = '提示' } = event.detail || {}
  if (msg && toastRef.value?.showAlert) {
    toastRef.value.showAlert(msg, title)
  }
}

// 全局「确认」弹窗：橙色确认框（站内统一风格，替代 window.confirm）
const handleGlobalConfirm = (event) => {
  const { message, resolve } = event.detail || {}
  if (message && toastRef.value?.showConfirm) {
    toastRef.value.showConfirm(message).then((ok) => { if (typeof resolve === 'function') resolve(ok) })
  } else if (typeof resolve === 'function') {
    resolve(false)
  }
}

onMounted(() => {
  appMounted = true
  window.addEventListener('open-login-modal', handleOpenLoginModal)
  window.addEventListener('show-toast', handleGlobalToast)
  window.addEventListener('show-alert', handleGlobalAlert)
  window.addEventListener('show-confirm', handleGlobalConfirm)
  handleSso()
  remindBindEmail()  // Toast 已挂载后再检查一次，处理刷新/已有登录态场景
  checkBanStatus()

  // 通过邀请或拉新链接打开时，自动跳到注册页
  // （链接参数预填由 LoginModal 挂载时的 onMounted 读取 query 完成）
  if (!currentUser.info) {
    const params = new URLSearchParams(window.location.search)
    const invite = params.get('invite') || ''
    const ref = params.get('ref') || ''
    if ((invite || ref) && route.path !== '/login') {
      router.push({ path: '/login', query: { mode: 'register', ...(invite ? { invite } : {}), ...(ref ? { ref } : {}) } })
    }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('open-login-modal', handleOpenLoginModal)
  window.removeEventListener('show-toast', handleGlobalToast)
  window.removeEventListener('show-alert', handleGlobalAlert)
  window.removeEventListener('show-confirm', handleGlobalConfirm)
})

// 【修改】退出登录逻辑 - 使用自定义弹窗
const handleLogout = async () => {
  // 调用 Toast 的 showConfirm 方法，它会返回 true 或 false
  const confirmed = await toastRef.value.showConfirm('确定要退出登录吗？')
  
  if (confirmed) {
    currentUser.clearInfo()
    // 可以加个提示
    toastRef.value.showToast('已退出登录', 'success')
    setTimeout(() => {
        window.location.reload()
    }, 1000)
  }
}
</script>

<style scoped>
.bare-shell { height: 100vh; height: 100dvh; overflow-y: auto; background: #f7f8fa; -webkit-overflow-scrolling: touch; }
.app-container { display: flex; height: 100vh; height: 100dvh; overflow: hidden; background-color: #f5f7fa; color: #333; font-family: "Microsoft YaHei", sans-serif; }
.sidebar { width: 220px; background-color: #fff; border-right: 1px solid #e4e7ed; display: flex; flex-direction: column; padding-top: 20px; }
.logo { font-size: 22px; font-weight: bold; color: #ff9900; text-align: center; margin-bottom: 30px; }
.nav-menu { list-style: none; padding: 0; margin: 0; }
.nav-menu li a { display: block; padding: 15px 25px; text-decoration: none; color: #606266; transition: all 0.3s; cursor: pointer; }
.nav-menu li a:hover, .nav-menu li a.active { background-color: #fff7e6; color: #ff9900; border-right: 3px solid #ff9900; }
.main-wrapper { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.top-header { flex: none; height: 60px; background-color: #fff; border-bottom: 1px solid #e4e7ed; display: flex; justify-content: flex-end; align-items: center; padding: 0 30px; }
.auth-buttons { display: flex; gap: 10px; align-items: center; }
.username { font-weight: bold; color: #333; }
.btn-login, .btn-register, .btn-logout { padding: 8px 20px; border-radius: 20px; border: none; cursor: pointer; font-size: 14px; }
.btn-login { background-color: #fff; border: 1px solid #dcdfe6; color: #606266; }
.btn-register { background-color: #ff9900; color: #fff; }
.btn-logout { background-color: #f56c6c; color: #fff; }
.msg-bell-wrap { position: relative; cursor: pointer; font-size: 20px; display: flex; align-items: center; }
.msg-bell { line-height: 1; }
.msg-badge {
  position: absolute;
  top: -6px;
  right: -10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
}
.msg-panel {
  position: absolute;
  top: 60px;
  right: 30px;
  width: 320px;
  max-height: 400px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
  z-index: 999;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.msg-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
}
.msg-close { border: none; background: none; font-size: 14px; color: #909399; cursor: pointer; }
.msg-list { max-height: 320px; overflow-y: auto; }
.msg-item { padding: 12px 16px; border-bottom: 1px solid #f2f3f5; }
.msg-content { margin: 0 0 4px; color: #303133; font-size: 13px; line-height: 1.6; }
.msg-time { color: #909399; font-size: 12px; }
.msg-empty { padding: 24px; text-align: center; color: #909399; font-size: 13px; }
.btn-logout:hover { background-color: #e05c5c; }
.content-area { flex: 1; padding: 30px; overflow-y: auto; }
.site-footer { flex: none; display: flex; justify-content: center; align-items: center; padding: 14px 20px 18px; background-color: #f5f7fa; }

.sidebar-footer { margin-top: auto; padding: 14px 25px 18px; border-top: 1px solid #f0f2f5; font-size: 13px; display: flex; flex-direction: column; gap: 8px; }
.sidebar-footer .uptime { color: #909399; }
.sidebar-footer a { color: #ff9900; text-decoration: none; }
.sidebar-footer a:hover { text-decoration: underline; }
.switch-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.switch-side { font-size: 12px; color: #a8abb2; transition: color 0.2s; white-space: nowrap; }
.switch-side.on { color: #ff9900; font-weight: 600; }
.switch {
  position: relative;
  width: 46px;
  height: 26px;
  flex: none;
  border: none;
  border-radius: 13px;
  background: #d9dee7;
  cursor: pointer;
  padding: 0;
  transition: background 0.25s;
}
.switch[aria-checked='true'] { background: #ff9900; }
.knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.25s;
}
.knob.right { transform: translateX(20px); }
@media (max-width: 768px) {
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
    min-height: 0;
    overflow: hidden;
  }

  .sidebar {
    width: 100%;
    padding: 12px 12px 8px;
    border-right: none;
    border-bottom: 1px solid #e4e7ed;
    flex: none;
  }

  .logo {
    margin: 0 0 10px;
    font-size: 20px;
  }

  .nav-menu {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
  }

  .nav-menu li {
    flex: 1 1 auto;
  }

  .nav-menu li a {
    padding: 9px 10px;
    border-radius: 6px;
    text-align: center;
    font-size: 14px;
  }

  .nav-menu li a:hover,
  .nav-menu li a.active {
    border-right: none;
    background-color: #fff7e6;
  }

  .main-wrapper {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .top-header {
    min-height: 56px;
    height: auto;
    padding: 10px 14px;
  }

  .auth-buttons {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .content-area {
    padding: 16px 12px 24px;
    flex: 1;
    overflow-y: auto;
  }
}
</style>