<template>
  <div class="app-container">
    <!-- 左侧侧边栏 -->
    <aside class="sidebar">
      <div class="logo">🍊 橙子社区</div>
      <ul class="nav-menu">
        <li><router-link to="/" active-class="active">首页</router-link></li>
        <li><router-link to="/checkin" active-class="active">签到</router-link></li>
        <li><router-link to="/notice" active-class="active">公告</router-link></li>
        <li><router-link to="/profile" active-class="active">个人信息</router-link></li>
        <li v-if="currentUser.info?.role === 'admin'">
          <router-link to="/admin" active-class="active">后台</router-link>
        </li>
      </ul>
    </aside>

    <!-- 右侧主区域 -->
    <div class="main-wrapper">
      <header class="top-header">
        <div class="auth-buttons">
          <!-- 根据登录状态显示不同内容 -->
          <template v-if="$user.info">
            <span class="username">👋 {{ $user.info.username }}</span>
            <!-- 退出按钮 -->
            <button class="btn-logout" @click="handleLogout">退出登录</button>
          </template>
          <template v-else>
            <button class="btn-login" @click="openModal(true)">登录</button>
            <button class="btn-register" @click="openModal(false)">注册</button>
          </template>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </div>

    <!-- 登录弹窗 -->
    <LoginModal 
      v-if="showLogin" 
      v-model:is-login="isLoginMode" 
      @close="showLogin = false" 
    />

    <!-- 【新增】全局 Toast 组件，给它加个 ref 方便调用 -->
    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import LoginModal from './components/LoginModal.vue'
import Toast from './components/Toast.vue' // 引入 Toast
import { currentUser } from './store'

const showLogin = ref(false)
const isLoginMode = ref(true)
const toastRef = ref(null) // 获取 Toast 组件实例

const openModal = (mode) => {
  isLoginMode.value = mode
  showLogin.value = true
}

const handleGlobalToast = (event) => {
  const { msg, type = 'success' } = event.detail || {}
  if (msg && toastRef.value?.showToast) {
    toastRef.value.showToast(msg, type)
  }
}

onMounted(() => {
  window.addEventListener('show-toast', handleGlobalToast)

  // 通过邀请链接（/?invite=xxx）直接打开时，自动弹出注册弹窗
  // （邀请码预填由 LoginModal 挂载时的 onMounted 读取 URL 完成）
  if (!currentUser.info) {
    const params = new URLSearchParams(window.location.search)
    if (params.get('invite')) {
      openModal(false)
    }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('show-toast', handleGlobalToast)
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
.app-container { display: flex; height: 100vh; background-color: #f5f7fa; color: #333; font-family: "Microsoft YaHei", sans-serif; }
.sidebar { width: 220px; background-color: #fff; border-right: 1px solid #e4e7ed; display: flex; flex-direction: column; padding-top: 20px; }
.logo { font-size: 22px; font-weight: bold; color: #ff9900; text-align: center; margin-bottom: 30px; }
.nav-menu { list-style: none; padding: 0; margin: 0; }
.nav-menu li a { display: block; padding: 15px 25px; text-decoration: none; color: #606266; transition: all 0.3s; cursor: pointer; }
.nav-menu li a:hover, .nav-menu li a.active { background-color: #fff7e6; color: #ff9900; border-right: 3px solid #ff9900; }
.main-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-header { height: 60px; background-color: #fff; border-bottom: 1px solid #e4e7ed; display: flex; justify-content: flex-end; align-items: center; padding: 0 30px; }
.auth-buttons { display: flex; gap: 10px; align-items: center; }
.username { font-weight: bold; color: #333; }
.btn-login, .btn-register, .btn-logout { padding: 8px 20px; border-radius: 20px; border: none; cursor: pointer; font-size: 14px; }
.btn-login { background-color: #fff; border: 1px solid #dcdfe6; color: #606266; }
.btn-register { background-color: #ff9900; color: #fff; }
.btn-logout { background-color: #f56c6c; color: #fff; }
.btn-logout:hover { background-color: #e05c5c; }
.content-area { flex: 1; padding: 30px; overflow-y: auto; }

@media (max-width: 768px) {
  .app-container {
    display: block;
    min-height: 100vh;
    height: auto;
  }

  .sidebar {
    width: 100%;
    padding: 12px 12px 8px;
    border-right: none;
    border-bottom: 1px solid #e4e7ed;
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
    min-height: calc(100vh - 104px);
    overflow: visible;
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
    overflow: visible;
  }
}
</style>