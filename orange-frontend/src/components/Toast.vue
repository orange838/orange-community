<template>
  <Teleport to="body">
    <!-- 普通消息提示 (原来的功能) -->
    <transition name="toast-fade">
      <div v-if="toastVisible" class="toast-container top-center">
        <div class="toast-box" :class="status">
          <span class="toast-icon">{{ icon }}</span>
          <span class="toast-msg">{{ toastMessage }}</span>
        </div>
      </div>
    </transition>

    <!-- 确认弹窗 (新增功能) -->
    <transition name="modal-fade">
      <div v-if="activeDialog" class="confirm-overlay">
        <div class="confirm-box">
          <h3 class="confirm-title">{{ activeDialog.title }}</h3>
          <p class="confirm-content">{{ activeDialog.message }}</p>
          <div class="confirm-actions">
            <button v-if="activeDialog.type === 'confirm'" class="btn-cancel" @click="handleCancel">取消</button>
            <button class="btn-confirm" @click="handleConfirm">确认</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const toastVisible = ref(false)
const toastMessage = ref('')
const status = ref('success') // 'success' 或 'error'
const activeDialog = ref(null)
const dialogQueue = []
let toastTimer = null

// 计算图标
const icon = computed(() => {
  return status.value === 'success' ? '✅' : '❌'
})

// 1. 普通提示方法 (保持原有逻辑)
const showToast = (msg, typeStatus = 'success') => {
  toastMessage.value = msg
  status.value = typeStatus
  toastVisible.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2500)
}

// 确认框和提示框依次显示，防止并发提醒互相覆盖。
const enqueueDialog = (type, msg, title = '提示') => {
  return new Promise((resolve) => {
    dialogQueue.push({ type, message: msg, title, resolve })
    if (!activeDialog.value) activeDialog.value = dialogQueue.shift()
  })
}

const showConfirm = (msg) => enqueueDialog('confirm', msg)
const showAlert = (msg, title = '提示') => enqueueDialog('alert', msg, title)

onBeforeUnmount(() => {
  if (toastTimer) clearTimeout(toastTimer)
})

const finishDialog = (result) => {
  const current = activeDialog.value
  if (!current) return
  activeDialog.value = dialogQueue.shift() || null
  current.resolve(result)
}

const handleConfirm = () => finishDialog(true)
const handleCancel = () => finishDialog(false)

// 暴露给外部使用
defineExpose({
  showToast,
  showConfirm,
  showAlert
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
  padding: 16px; box-sizing: border-box; overflow-y: auto;
}
.confirm-box {
  background: #fff; width: 320px; max-width: 100%; padding: 25px; box-sizing: border-box;
  max-height: calc(100vh - 32px); max-height: calc(100dvh - 32px); overflow-y: auto;
  border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  text-align: center;
}
.confirm-title { margin: 0 0 15px 0; font-size: 18px; color: #333; }
.confirm-content { margin: 0 0 25px 0; font-size: 15px; color: #606266; line-height: 1.5; white-space: pre-line; }
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