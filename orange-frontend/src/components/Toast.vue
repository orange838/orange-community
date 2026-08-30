<template>
  <Teleport to="body">
    <!-- 普通消息提示 (原来的功能) -->
    <transition name="toast-fade">
      <div v-if="visible && type === 'message'" class="toast-container top-center">
        <div class="toast-box" :class="status">
          <span class="toast-icon">{{ icon }}</span>
          <span class="toast-msg">{{ message }}</span>
        </div>
      </div>
    </transition>

    <!-- 确认弹窗 (新增功能) -->
    <transition name="modal-fade">
      <div v-if="visible && type === 'confirm'" class="confirm-overlay">
        <div class="confirm-box">
          <h3 class="confirm-title">提示</h3>
          <p class="confirm-content">{{ message }}</p>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="handleCancel">取消</button>
            <button class="btn-confirm" @click="handleConfirm">确定</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const visible = ref(false)
const message = ref('')
const type = ref('message') // 'message' 或 'confirm'
const status = ref('success') // 'success' 或 'error'
let resolvePromise = null // 用来存回调函数

// 计算图标
const icon = computed(() => {
  return status.value === 'success' ? '✅' : '❌'
})

// 1. 普通提示方法 (保持原有逻辑)
const showToast = (msg, typeStatus = 'success') => {
  message.value = msg
  status.value = typeStatus
  type.value = 'message'
  visible.value = true
  setTimeout(() => { visible.value = false }, 2500)
}

// 2. 确认弹窗方法 (新增)
const showConfirm = (msg) => {
  message.value = msg
  type.value = 'confirm'
  visible.value = true
  
  // 返回一个 Promise，方便外部等待用户点击
  return new Promise((resolve) => {
    resolvePromise = resolve
  })
}

// 点击确定
const handleConfirm = () => {
  visible.value = false
  if (resolvePromise) resolvePromise(true)
}

// 点击取消
const handleCancel = () => {
  visible.value = false
  if (resolvePromise) resolvePromise(false)
}

// 暴露给外部使用
defineExpose({
  showToast,
  showConfirm
})
</script>

<style scoped>
/* --- 原有 Toast 样式 --- */
.toast-container { position: fixed; top: 30px; left: 50%; transform: translateX(-50%); z-index: 9999; }
.toast-box { display: flex; align-items: center; gap: 10px; background: #fff; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 14px; color: #333; border-left: 4px solid #ff9900; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.4s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(-20px); }

/* --- 新增 Confirm 弹窗样式 --- */
.confirm-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex; justify-content: center; align-items: center;
  z-index: 10000; /* 比 Toast 高一层 */
}
.confirm-box {
  background: #fff; width: 320px; padding: 25px;
  border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  text-align: center;
}
.confirm-title { margin: 0 0 15px 0; font-size: 18px; color: #333; }
.confirm-content { margin: 0 0 25px 0; font-size: 15px; color: #606266; line-height: 1.5; }
.confirm-actions { display: flex; justify-content: space-between; gap: 15px; }
.confirm-actions button {
  flex: 1; padding: 10px 0; border-radius: 6px; border: none;
  font-size: 14px; cursor: pointer; transition: all 0.3s;
}
.btn-cancel { background-color: #f4f4f5; color: #606266; }
.btn-cancel:hover { background-color: #e9e9eb; }
.btn-confirm { background-color: #ff9900; color: #fff; }
.btn-confirm:hover { background-color: #e68a00; }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.3s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
</style>