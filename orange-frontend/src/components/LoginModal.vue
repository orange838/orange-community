<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <h2 class="modal-title">{{ isLogin ? '欢迎回来' : '注册账号' }}</h2>

      <form class="login-form" @submit.prevent="handleSubmit">
        
        <!-- ========== 登录模式：Tab 切换 ========== -->
        <template v-if="isLogin">
          <div class="login-tabs">
            <button type="button" :class="{ active: loginMethod === 'password' }" @click="loginMethod = 'password'">密码登录</button>
            <button type="button" :class="{ active: loginMethod === 'code' }" @click="loginMethod = 'code'">验证码登录</button>
          </div>

          <!-- 密码登录表单 -->
          <div v-if="loginMethod === 'password'">
            <div class="form-item">
              <label>账号/邮箱</label>
              <!-- 注意这里绑定的是 account -->
              <input type="text" placeholder="请输入用户名或邮箱" v-model="formData.account" />
            </div>
            <div class="form-item">
              <label>密码</label>
              <input type="password" placeholder="请输入密码" v-model="formData.password" />
            </div>
          </div>

          <!-- 验证码登录表单 -->
          <div v-else>
            <div class="form-item">
              <label>邮箱</label>
              <!-- 注意这里绑定的是 email -->
              <input type="email" placeholder="请输入邮箱" v-model="formData.email" />
            </div>
            <div class="form-item code-item">
              <label>邮箱验证码</label>
              <div class="code-input-wrapper">
                <input type="text" placeholder="请输入验证码" v-model="formData.code" />
                <button type="button" class="code-btn" :disabled="countdown > 0 || loading" @click="sendCode">
                  {{ countdown > 0 ? `${countdown}秒后重试` : '获取验证码' }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- ========== 注册模式 ========== -->
        <template v-else>
          <div class="form-item">
            <label>邮箱</label>
            <input type="email" placeholder="请输入邮箱地址" v-model="formData.email" />
          </div>
          <div class="form-item">
            <label>用户名</label>
            <input type="text" placeholder="请输入用户名" v-model="formData.username" />
          </div>
          <div class="form-item">
            <label>密码</label>
            <input type="password" placeholder="请输入密码" v-model="formData.password" />
          </div>
          <div class="form-item">
            <label>确认密码</label>
            <input type="password" placeholder="请再次输入密码" v-model="formData.confirmPassword" />
          </div>
          <div class="form-item code-item">
            <label>邮箱验证码</label>
            <div class="code-input-wrapper">
              <input type="text" placeholder="请输入验证码" v-model="formData.code" />
              <button type="button" class="code-btn" :disabled="countdown > 0 || loading" @click="sendCode">
                {{ countdown > 0 ? `${countdown}秒后重试` : '获取验证码' }}
              </button>
            </div>
          </div>
        </template>

        <!-- Turnstile 人机验证 -->
        <div class="form-item turnstile-item">
          <label>人机验证</label>
          <div v-if="isLogin" ref="turnstileContainerLogin"></div>
          <div v-else ref="turnstileContainerRegister"></div>
          <p class="turnstile-hint" v-if="turnstileError">{{ turnstileError }}</p>
        </div>

        <!-- 提交按钮 -->
        <button type="submit" class="submit-btn" :disabled="loading || !currentTurnstileToken">
          {{ loading ? '处理中...' : (isLogin ? '登 录' : '注 册') }}
        </button>
      </form>

      <div class="modal-footer">
        <span v-if="isLogin">还没有账号？<a href="javascript:void(0)" @click="switchMode(false)">立即注册</a></span>
        <span v-else>已有账号？<a href="javascript:void(0)" @click="switchMode(true)">立即登录</a></span>
      </div>
      
      <div class="close-btn" @click="handleClose">×</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { currentUser } from '../store' 

const props = defineProps({ isLogin: { type: Boolean, default: true } })
const emit = defineEmits(['close', 'update:isLogin'])

// 统一表单数据对象
const formData = reactive({ 
  email: '',      // 用于：验证码登录、注册
  account: '',    // 用于：密码登录
  username: '',   // 用于：注册
  password: '',   // 用于：登录/注册
  confirmPassword: '', // 用于：注册确认
  code: ''        // 用于：验证码
})

const countdown = ref(0)
const loading = ref(false)
const loginMethod = ref('password') 
let timer = null

// --- Turnstile 相关状态 ---
const turnstileContainerLogin = ref(null)
const turnstileContainerRegister = ref(null)
const currentTurnstileToken = ref('')
const turnstileError = ref('')
let turnstileTimeout = null
let turnstileWaitInterval = null
let turnstileLoadTimeout = null
let turnstileWidgetId = null

// --- Toast 提示逻辑 (使用 window.dispatchEvent 触发自定义事件) ---
// 这样就不需要在这个组件里 import Toast 组件了，解耦更干净
const showToast = (msg, type = 'success') => {
  window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))
}

// --- 核心逻辑 ---

const switchMode = (toLogin) => {
  // 切换时清空表单，防止数据残留
  Object.assign(formData, { email: '', account: '', username: '', password: '', confirmPassword: '', code: '' })
  currentTurnstileToken.value = ''
  turnstileError.value = ''
  loginMethod.value = 'password' 
  if (turnstileTimeout) clearTimeout(turnstileTimeout)
  clearTurnstileWidget()
  emit('update:isLogin', toLogin)
}

const handleClose = () => emit('close')

const clearTurnstileWidget = () => {
  if (turnstileTimeout) {
    clearTimeout(turnstileTimeout)
    turnstileTimeout = null
  }
  if (turnstileWaitInterval) {
    clearInterval(turnstileWaitInterval)
    turnstileWaitInterval = null
  }
  if (turnstileLoadTimeout) {
    clearTimeout(turnstileLoadTimeout)
    turnstileLoadTimeout = null
  }
  if (turnstileWidgetId !== null && window.turnstile?.remove) {
    window.turnstile.remove(turnstileWidgetId)
    turnstileWidgetId = null
  }
}

const getTurnstileErrorCode = (error) => {
  if (typeof error === 'string' || typeof error === 'number') return String(error)
  if (error && typeof error === 'object') {
    if ('code' in error) return String(error.code)
    if ('errorCode' in error) return String(error.errorCode)
  }
  return '未知'
}

const showTurnstileError = (error, message) => {
  const code = getTurnstileErrorCode(error)
  console.error('Turnstile error:', { code, error, hostname: window.location.hostname })
  const errorMessages = {
    '110100': 'Turnstile site key 无效，请联系管理员',
    '110110': 'Turnstile site key 不存在，请联系管理员',
    '110200': '当前访问域名未获 Turnstile 授权，请联系管理员',
    '110600': '人机验证超时，请重试；如果持续失败，请检查设备时间和网络',
    '110620': '人机验证交互超时，请重新操作验证',
    '200100': '设备时间或浏览器缓存异常，请校准时间并刷新页面',
    '200500': '验证服务加载失败，请检查网络是否拦截 challenges.cloudflare.com',
    '400020': 'Turnstile site key 无效，请联系管理员',
    '400070': 'Turnstile site key 已停用，请联系管理员',
  }
  let detail = errorMessages[code]
  if (!detail && code.startsWith('300')) {
    detail = 'Cloudflare 通用挑战失败，请更新浏览器并关闭 VPN、代理或广告拦截后重试'
  }
  if (!detail && code.startsWith('600')) {
    detail = '验证环境未通过 Cloudflare 风险检查，请使用最新版 Chrome/系统浏览器，关闭 VPN 或广告拦截后重试'
  }
  turnstileError.value = `${detail || message}（错误码：${code}）`
  currentTurnstileToken.value = ''
}

const renderTurnstile = () => {
  const container = props.isLogin ? turnstileContainerLogin.value : turnstileContainerRegister.value
  if (!container) return

  clearTurnstileWidget()
  currentTurnstileToken.value = ''
  turnstileError.value = ''

  const hasSiteKey = Boolean(import.meta.env.VITE_CF_SITE_KEY)

  if (!hasSiteKey) {
    turnstileError.value = '未配置 Turnstile site key，无法渲染人机验证组件。'
    return
  }

  turnstileWaitInterval = setInterval(() => {
    if (window.turnstile) {
      clearInterval(turnstileWaitInterval)
      turnstileWaitInterval = null
      if (turnstileLoadTimeout) {
        clearTimeout(turnstileLoadTimeout)
        turnstileLoadTimeout = null
      }
      turnstileTimeout = setTimeout(() => {
        try {
          turnstileWidgetId = window.turnstile.render(container, {
            sitekey: import.meta.env.VITE_CF_SITE_KEY,
            action: props.isLogin ? 'login' : 'register',
            callback: (token) => {
              currentTurnstileToken.value = token
              turnstileError.value = ''
            },
            'error-callback': (err) => {
              showTurnstileError(err, '人机验证加载失败，请检查网络、浏览器拦截或 Turnstile 配置')
            },
            'expired-callback': () => {
              showTurnstileError('token-expired', '人机验证已过期，请重新验证')
            },
            'timeout-callback': () => {
              showTurnstileError('challenge-timeout', '人机验证超时，请重试')
            }
          })
        } catch (e) {
          showTurnstileError(e, '人机验证组件初始化失败，请刷新页面重试')
        }
      }, 100)
    }
  }, 100)
  turnstileLoadTimeout = setTimeout(() => {
    if (turnstileWaitInterval) {
      clearInterval(turnstileWaitInterval)
      turnstileWaitInterval = null
      showTurnstileError('script-not-loaded', '人机验证脚本加载失败，请检查网络或浏览器拦截')
    }
  }, 10000)
}

watch(() => props.isLogin, () => setTimeout(() => renderTurnstile(), 50))
onMounted(() => renderTurnstile())
onBeforeUnmount(clearTurnstileWidget)

// 【修复重点】发送验证码逻辑
const sendCode = async () => {
  // 1. 确定目标邮箱：无论是"验证码登录"还是"注册"，用的都是 formData.email
  const targetEmail = formData.email
  
  // 2. 校验邮箱格式
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!targetEmail || !emailReg.test(targetEmail)) {
    showToast('请输入正确的邮箱地址！', 'error')
    return
  }

  loading.value = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/send-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email: targetEmail,
        type: props.isLogin ? 'login' : 'register' 
      })
    })
    const result = await response.json()

    if (response.ok) {
      showToast('验证码已发送，请查收邮箱！', 'success')
      countdown.value = 60
      timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      showToast(result.error || '发送失败', 'error')
    }
  } catch (e) {
    showToast('网络错误，请检查后端服务', 'error')
  } finally {
    loading.value = false
  }
}

// 【修复重点】提交表单逻辑
const handleSubmit = async () => {
  // 1. 注册时的校验
  if (!props.isLogin) {
    if (formData.password !== formData.confirmPassword) {
      showToast('两次输入的密码不一致！', 'error')
      return
    }
    if (!formData.username || !formData.password || !formData.email || !formData.code) {
      showToast('请完整填写注册信息！', 'error')
      return
    }
  }

  // 2. 登录时的校验
  if (props.isLogin) {
    if (loginMethod.value === 'password') {
      // 密码登录：校验 account
      if (!formData.account || !formData.password) {
        showToast('请输入账号和密码！', 'error')
        return
      }
    } else {
      // 验证码登录：校验 email
      if (!formData.email || !formData.code) {
        showToast('请输入邮箱和验证码！', 'error')
        return
      }
    }
  }

  // 3. 人机验证校验
  if (!currentTurnstileToken.value) {
    showToast('请完成人机验证！', 'error')
    return
  }
  
  loading.value = true
  try {
    const url = props.isLogin 
      ? `${import.meta.env.VITE_API_URL}/api/login` 
      : `${import.meta.env.VITE_API_URL}/api/register`

    const body = { cf_token: currentTurnstileToken.value }

    // 根据模式填充不同的数据
    if (props.isLogin) {
        body.method = loginMethod.value
        if (loginMethod.value === 'password') {
            body.account = formData.account
            body.password = formData.password
        } else {
            body.email = formData.email
            body.code = formData.code
        }
    } else {
        // 注册模式
        body.email = formData.email
        body.username = formData.username
        body.password = formData.password
        body.code = formData.code
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const result = await response.json()

    if (response.ok) {
      showToast(result.message, 'success')

      // 【关键】登录成功，保存用户信息
      if (result.user) {
        currentUser.setInfo(result.user)
      }

      setTimeout(() => handleClose(), 1500)
    } else {
      showToast(result.error || '操作失败', 'error')
      // 失败重置 Turnstile
      if (window.turnstile) {
        const container = props.isLogin ? turnstileContainerLogin.value : turnstileContainerRegister.value
        if (container) window.turnstile.reset(container)
        currentTurnstileToken.value = ''
      }
    }
  } catch (e) {
    showToast('网络异常，请稍后再试', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: #fff; width: 420px; padding: 40px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; }
.modal-title { text-align: center; color: #333; margin-bottom: 30px; font-size: 24px; }
.form-item { margin-bottom: 20px; }
.form-item label { display: block; margin-bottom: 8px; color: #606266; font-size: 14px; }
.form-item input { width: 100%; padding: 10px; border: 1px solid #dcdfe6; border-radius: 4px; box-sizing: border-box; outline: none; }
.form-item input:focus { border-color: #ff9900; }

.login-tabs { display: flex; gap: 10px; margin-bottom: 20px; }
.login-tabs button { flex: 1; padding: 10px; border: 1px solid #dcdfe6; border-radius: 4px; background: #fff; cursor: pointer; font-size: 14px; transition: all 0.3s; }
.login-tabs button.active { background-color: #ff9900; color: #fff; border-color: #ff9900; }

.code-input-wrapper { display: flex; gap: 10px; }
.code-input-wrapper input { flex: 1; }
.code-btn { padding: 0 15px; background-color: #f4f4f5; border: 1px solid #dcdfe6; border-radius: 4px; color: #606266; cursor: pointer; white-space: nowrap; font-size: 14px; transition: all 0.3s; }
.code-btn:hover:not(:disabled) { color: #ff9900; border-color: #ff9900; }
.code-btn:disabled { cursor: not-allowed; color: #c0c4cc; background-color: #f5f7fa; }

.turnstile-item { margin-bottom: 20px; }
.turnstile-hint { color: #f56c6c; font-size: 12px; margin-top: 5px; }

.submit-btn { width: 100%; padding: 12px; background-color: #ff9900; color: #fff; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 10px; }
.submit-btn:hover:not(:disabled) { background-color: #e68a00; }
.submit-btn:disabled { background-color: #ffb84d; cursor: not-allowed; }

.modal-footer { text-align: center; margin-top: 20px; font-size: 14px; color: #909399; }
.modal-footer a { color: #ff9900; text-decoration: none; cursor: pointer; }
.modal-footer a:hover { text-decoration: underline; }
.close-btn { position: absolute; top: 15px; right: 20px; font-size: 24px; color: #909399; cursor: pointer; }
.close-btn:hover { color: #333; }
</style>