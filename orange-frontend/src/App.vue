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
      </ul>
    </aside>

    <!-- 右侧主区域 -->
    <div class="main-wrapper">
      <header class="top-header">
        <div class="auth-buttons">
          <!-- 点击登录：传入 true -->
          <button class="btn-login" @click="openModal(true)">登录</button>
          <!-- 点击注册：传入 false -->
          <button class="btn-register" @click="openModal(false)">注册</button>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </div>

    <!-- 弹窗组件 -->
    <!-- v-model:is-login 实现了双向绑定，子组件切换模式时，父组件也会同步更新 -->
    <LoginModal 
      v-if="showLogin" 
      v-model:is-login="isLoginMode" 
      @close="showLogin = false" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LoginModal from './components/LoginModal.vue'

const showLogin = ref(false)
const isLoginMode = ref(true)

const openModal = (mode) => {
  isLoginMode.value = mode
  showLogin.value = true
}
</script>

<style scoped>
/* 样式保持不变 */
.app-container { display: flex; height: 100vh; background-color: #f5f7fa; color: #333; font-family: "Microsoft YaHei", sans-serif; }
.sidebar { width: 220px; background-color: #fff; border-right: 1px solid #e4e7ed; display: flex; flex-direction: column; padding-top: 20px; }
.logo { font-size: 22px; font-weight: bold; color: #ff9900; text-align: center; margin-bottom: 30px; }
.nav-menu { list-style: none; padding: 0; margin: 0; }
.nav-menu li a { display: block; padding: 15px 25px; text-decoration: none; color: #606266; transition: all 0.3s; cursor: pointer; }
.nav-menu li a:hover, .nav-menu li a.active { background-color: #fff7e6; color: #ff9900; border-right: 3px solid #ff9900; }
.main-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-header { height: 60px; background-color: #fff; border-bottom: 1px solid #e4e7ed; display: flex; justify-content: flex-end; align-items: center; padding: 0 30px; }
.auth-buttons { display: flex; gap: 10px; }
.btn-login, .btn-register { padding: 8px 20px; border-radius: 20px; border: none; cursor: pointer; font-size: 14px; }
.btn-login { background-color: #fff; border: 1px solid #dcdfe6; color: #606266; }
.btn-register { background-color: #ff9900; color: #fff; }
.content-area { flex: 1; padding: 30px; overflow-y: auto; }
</style>