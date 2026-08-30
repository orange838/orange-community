<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <h2 class="modal-title">{{ isLogin ? '欢迎登录' : '注册账号' }}</h2>

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
          <!-- 确认密码 -->
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

        <!-- Turnstile 人机验证（登录和注册都强制显示） -->
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

  <!-- Toast 提示组件 -->
  <Teleport to="body">
    <transition name="toast-fade">
      <div v-if="toastVisible" class="toast-container">
        <div class="toast-box">
          <span class="toast-icon">{{ toastType === 'success' ? '✅' : '❌' }}</span>
          <span class="toast-msg">{{ toastMsg }}</span>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
// 【新增】引入状态仓库
import { currentUser } from '../store'

const props = defineProps({ isLogin: { type: Boolean, default: true } })
const emit = defineEmits(['close', 'update:isLogin'])

const formData = reactive({ 
  email: '', 
  account: '', 
  username: '', 
  password: '', 
  confirmPassword: '', 
  code: '' 
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

// --- Toast 提示 ---
const toastVisible = ref(false)
const toastMsg = ref('')
const toastType = ref('success')
const showToast = (msg, type = 'success') => {
  toastMsg.value = msg
  toastType.value = type
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 2500)
}

// --- 核心逻辑 ---
const switchMode = (toLogin) => {
  Object.assign(formData, { email: '', account: '', username: '', password: '', confirmPassword: '', code: '' })
  currentTurnstileToken.value = ''
  turnstileError.value = ''
  loginMethod.value = 'password' 
  if (turnstileTimeout) clearTimeout(turnstileTimeout)
  emit('update:isLogin', toLogin)
}

const handleClose = () => emit('close')

const renderTurnstile = () => {
  const container = props.isLogin ? turnstileContainerLogin.value : turnstileContainerRegister.value
  if (!container) return
  
  currentTurnstileToken.value = ''
  turnstileError.value = ''
  
  const waitForTurnstile = setInterval(() => {
    if (window.turnstile) {
      clearInterval(waitForTurnstile)
      turnstileTimeout = setTimeout(() => {
        try {
          window.turnstile.render(container, {
            sitekey: import.meta.env.VITE_CF_SITE_KEY,
            callback: (token) => {
              currentTurnstileToken.value = token
              turnstileError.value = ''
            },
            'error-callback': (err) => {
              console.error('Turnstile error:', err)
              turnstileError.value = '人机验证失败，请重试'
              currentTurnstileToken.value = ''
            }
          })
        } catch (e) {
          turnstileError.value = '验证组件加载失败，请刷新页面重试'
        }
      }, 100)
    }
  }, 100)
}

watch(() => props.isLogin, () => setTimeout(() => renderTurnstile(), 50))
onMounted(() => renderTurnstile())

// 发送验证码
const sendCode = async () => {
  const emailReg = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/
  const targetEmail = formData.email
  
  if (!emailReg.test(targetEmail)) {
    showToast('请输入正确的邮箱地址！', 'error')
    return
  }

  loading.value = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/send-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: targetEmail })
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
    showToast('网络错误，请确保后端服务已启动', 'error')
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  // 1. 注册时的确认密码校验
  if (!props.isLogin && formData.password !== formData.confirmPassword) {
    showToast('两次输入的密码不一致！', 'error')
    return
  }

  // 2. 基础校验
  if (props.isLogin) {
    if (loginMethod.value === 'password' && (!formData.account || !formData.password)) {
      showToast('请输入账号和密码！', 'error')
      return
    }
    if (loginMethod.value === 'code' && (!formData.email || !formData.code)) {
      showToast('请输入邮箱和验证码！', 'error')
      return
    }
  } else {
    if (!formData.username || !formData.password || !formData.code) {
      showToast('请完整填写注册信息！', 'error')
      return
    }
  }

  if (!currentTurnstileToken.value) {
    showToast('请完成人机验证！', 'error')
    return
  }
  
  loading.value = true
  try {
    const url = props.isLogin 
      ? `${import.meta.env.VITE_API_URL}/api/login` 
      : `${import.meta.env.VITE_API_URL}/api/register`

    const body = { ...formData, cf_token: currentTurnstileToken.value }
    
    // 如果是登录，告诉后端当前是哪种登录方式
    if (props.isLogin) {
      body.method = loginMethod.value
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const result = await response.json()

    if (response.ok) {
      showToast(result.message, 'success')

      // 【新增】登录成功，保存用户信息到全局状态 + localStorage
      // 后端返回的字段就是 result.user（包含 email 和 username）
      if (result.user) {
        currentUser.setInfo(result.user)
      }

      setTimeout(() => handleClose(), 1500)
    } else {
      showToast(result.error || '操作失败', 'error')
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

.toast-container { position: fixed; top: 30px; left: 50%; transform: translateX(-50%); z-index: 9999; }
.toast-box { display: flex; align-items: center; gap: 10px; background: #fff; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 14px; color: #333; border-left: 4px solid #ff9900; }
.toast-icon { font-size: 18px; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.4s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(-20px); }
</style>