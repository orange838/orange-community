<template>
  <Teleport to="body">
    <transition name="toast-fade">
      <div v-if="visible" class="toast-container">
        <div class="toast-box">
          <span class="toast-icon">{{ type === 'success' ? '✅' : '❌' }}</span>
          <span class="toast-msg">{{ message }}</span>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const visible = ref(false)
const message = ref('')
const type = ref('success') // success 或 error

// 暴露给父组件调用的方法
const show = (msg, toastType = 'success', duration = 3000) => {
  message.value = msg
  type.value = toastType
  visible.value = true
  setTimeout(() => {
    visible.value = false
  }, duration)
}

defineExpose({ show })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999; /* 保证在最上层 */
}
.toast-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  font-size: 14px;
  color: #333;
  border-left: 4px solid #ff9900;
}
.toast-icon { font-size: 18px; }

/* 丝滑的淡入淡出动画 */
.toast-fade-enter-active, .toast-fade-leave-active {
  transition: all 0.4s ease;
}
.toast-fade-enter-from, .toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>