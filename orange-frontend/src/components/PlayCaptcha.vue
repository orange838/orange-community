<template>
  <div ref="rootEl" class="play-captcha-wrap"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import React from 'react'
import { createRoot } from 'react-dom/client'
import { ClawCaptcha } from 'playcaptcha'
import '../assets/clawcaptcha.css'

const props = defineProps({
  assetBase: { type: String, default: '/playcaptcha/toys/' },
  title: { type: String, default: '抓中正确玩具证明你是真人' }
})
const emit = defineEmits(['verified'])
const rootEl = ref(null)
let root = null

onMounted(() => {
  const node = React.createElement(ClawCaptcha, {
    assetBase: props.assetBase,
    title: props.title,
    onVerify: () => emit('verified')
  })
  root = createRoot(rootEl.value)
  root.render(node)
})

onBeforeUnmount(() => {
  if (root) { root.unmount(); root = null }
})
</script>

<style scoped>
.play-captcha-wrap { display: flex; justify-content: center; width: 100%; max-width: 440px; min-width: 0; margin: 10px 0; }
.play-captcha-wrap :deep(.clawcap) { width: 100%; max-width: 100%; }
</style>
