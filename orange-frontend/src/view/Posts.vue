<template>
  <div class="page-container">
    <h2>📋 帖子广场</h2>

    <!-- 发帖表单 -->
    <div class="post-form-card">
      <template v-if="isLoggedIn && !banStatus.is_banned">
        <input
          v-model="form.title"
          type="text"
          class="title-input"
          maxlength="80"
          placeholder="标题（最多 80 字）"
        />
        <textarea
          v-model="form.content"
          class="content-input"
          rows="5"
          maxlength="5000"
          placeholder="写点什么…（内容会自动做敏感词过滤）"
        ></textarea>
        <div class="form-actions">
          <span class="hit-hint" v-if="hitWords.length">已过滤：{{ hitWords.join('、') }}</span>
          <button class="submit-btn" :disabled="submitting" @click="submitPost">
            {{ submitting ? '发布中…' : '发布' }}
          </button>
        </div>
        <!-- 敏感词命中时的预览：展示过滤后的标题/正文 -->
        <div class="filtered-preview" v-if="lastResult && !lastResult.safe">
          <p class="preview-label">检测到敏感词，已自动替换为 ***：</p>
          <p><strong>标题：</strong>{{ lastResult.filteredTitle }}</p>
          <p><strong>内容：</strong>{{ lastResult.filteredContent }}</p>
        </div>
      </template>
      <div v-else-if="isLoggedIn && banStatus.is_banned" class="ban-notice">
        <strong>账号已被封禁并禁言</strong>
        <p>{{ banStatus.banned_until ? `临时封禁 ${banStatus.duration_days} 天，至 ${formatTime(banStatus.banned_until)}` : '永久封禁' }}</p>
        <p v-if="banStatus.reason">原因：{{ banStatus.reason }}</p>
      </div>
      <div v-else class="need-login">
        登录后才能发帖，请先 <a href="#" @click.prevent="goLogin">登录</a>。
      </div>
    </div>

    <!-- 帖子列表 -->
    <div v-if="postsLoading && !posts.length" class="post-list loading-list" role="status" aria-label="正在加载帖子">
      <div v-for="item in 3" :key="item" class="post-skeleton">
        <div class="skeleton-line skeleton-meta"></div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-content"></div>
        <div class="skeleton-line skeleton-content skeleton-content-short"></div>
      </div>
    </div>
    <div class="post-list" v-else-if="posts.length">
      <div class="post-item" v-for="p in posts" :key="p.id">
        <div class="post-head">
          <span class="post-username">{{ p.username }}</span>
          <span class="post-time">{{ formatTime(p.created_at) }}</span>
          <button v-if="canDelete(p)" class="del-btn" @click="deletePost(p)">删除</button>
        </div>
        <h3 class="post-title">{{ p.title }}</h3>
        <p class="post-content">{{ p.content }}</p>
      </div>
    </div>
    <p class="empty load-error" v-else-if="postsError">{{ postsError }}</p>
    <p class="empty" v-else>还没有帖子，来发第一帖吧～</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { currentUser } from '../store'

const API = import.meta.env.VITE_API_URL
const form = ref({ title: '', content: '' })
const posts = ref([])
const postsLoading = ref(true)
const postsError = ref('')
const submitting = ref(false)
const hitWords = ref([])
const lastResult = ref(null)
const banStatus = ref({ is_banned: false, reason: '', banned_until: null })
let banStatusTimer = null
let banStatusErrorShown = false

// 用 token 判断登录（email 可能为空——未绑邮箱的账号也是已登录用户，不能据此判断）
const isLoggedIn = computed(() => Boolean(currentUser.token))
const goLogin = () => window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: '请先登录后再发帖', type: 'error' } }))

const toast = (msg, type) => window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))

const loadBanStatus = async () => {
  const token = currentUser.token
  if (!token) {
    banStatus.value = { is_banned: false, reason: '', banned_until: null }
    banStatusErrorShown = false
    return
  }
  try {
    banStatus.value = { is_banned: false, reason: '', duration_days: null, banned_until: null }
    const res = await fetch(`${API}/api/user/ban-status`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || '封禁状态查询失败')
    if (token !== currentUser.token) return
    banStatus.value = data
    banStatusErrorShown = false
  } catch (error) {
    if (!banStatusErrorShown) toast(error.message || '封禁状态查询失败', 'error')
    banStatusErrorShown = true
  }
}

const formatTime = (t) => {
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

const loadPosts = async () => {
  postsLoading.value = true
  postsError.value = ''
  try {
    const res = await fetch(`${API}/api/posts`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || '帖子加载失败，请稍后重试')
    posts.value = data.posts || []
  } catch (error) {
    postsError.value = error.message || '帖子加载失败，请稍后重试'
  } finally {
    postsLoading.value = false
  }
}

const canDelete = (p) =>
  (currentUser.info && (currentUser.info.id === p.user_id || currentUser.info.username === p.username)) ||
  ['admin', 'super_admin'].includes(currentUser.info?.role)

const confirmDelete = (message) => new Promise((resolve) => {
  window.dispatchEvent(new CustomEvent('show-confirm', { detail: { message, resolve } }))
})

const deletePost = async (p) => {
  const ok = await confirmDelete('确定删除这条帖子？')
  if (!ok) return
  try {
    const res = await fetch(`${API}/api/posts?id=${p.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${currentUser.token}` }
    })
    const data = await res.json()
    if (!res.ok) return toast(data.error || '删除失败', 'error')
    toast('已删除', 'success')
    await loadPosts()
  } catch (e) {
    toast(e.message || '删除失败', 'error')
  }
}

const submitPost = async () => {
  const title = form.value.title.trim()
  const content = form.value.content.trim()
  if (!title) return toast('标题不能为空', 'error')
  if (!content) return toast('内容不能为空', 'error')
  submitting.value = true
  hitWords.value = []
  lastResult.value = null
  try {
    const res = await fetch(`${API}/api/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentUser.token}` },
      body: JSON.stringify({ title, content })
    })
    const data = await res.json()
    if (!res.ok) return toast(data.error || '发布失败', 'error')
    lastResult.value = data
    hitWords.value = data.profaneWords || []
    if (!data.safe) {
      toast(`检测到敏感词（${(data.profaneWords || []).join('、')}），已替换后发布`, 'warning')
    } else {
      toast('发布成功', 'success')
    }
    form.value = { title: '', content: '' }
    await loadPosts()
  } catch (e) {
    toast(e.message || '发布失败', 'error')
  } finally {
    submitting.value = false
  }
}

watch(() => currentUser.token, loadBanStatus)
onMounted(() => {
  loadPosts()
  loadBanStatus()
  banStatusTimer = setInterval(loadBanStatus, 30000)
})
onBeforeUnmount(() => {
  if (banStatusTimer) clearInterval(banStatusTimer)
})
</script>

<style scoped>
.ban-notice {
  padding: 16px;
  border: 1px solid #f3c5c5;
  border-radius: 8px;
  background: #fff6f6;
  color: #a12626;
}
.ban-notice p { margin: 8px 0 0; }
.post-form-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-top: 15px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
.title-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  font-size: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  margin-bottom: 10px;
  outline: none;
}
.title-input:focus, .content-input:focus { border-color: #ff9900; }
.content-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  resize: vertical;
  outline: none;
}
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}
.hit-hint { color: #e6a23c; font-size: 13px; }
.submit-btn {
  padding: 8px 22px;
  background: #ff9900;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.submit-btn:disabled { background: #c0c4cc; cursor: not-allowed; }
.filtered-preview {
  margin-top: 10px;
  padding: 10px 14px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 6px;
  color: #e6a23c;
  font-size: 13px;
}
.preview-label { margin: 0 0 4px; font-weight: 600; }
.need-login {
  padding: 20px;
  text-align: center;
  color: #909399;
}
.need-login a { color: #ff9900; }
.post-list { margin-top: 15px; }
.post-skeleton {
  position: relative;
  overflow: hidden;
  background: #fff;
  padding: 18px 22px;
  border-radius: 8px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
.skeleton-line {
  position: relative;
  overflow: hidden;
  background: #edf0f4;
  border-radius: 5px;
}
.skeleton-line::after {
  position: absolute;
  inset: 0;
  content: '';
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent);
  animation: skeleton-shimmer 1.35s infinite;
}
.skeleton-meta { width: 38%; height: 14px; margin-bottom: 14px; }
.skeleton-title { width: 62%; height: 18px; margin-bottom: 12px; }
.skeleton-content { width: 100%; height: 13px; margin-bottom: 8px; }
.skeleton-content-short { width: 72%; margin-bottom: 0; }
@keyframes skeleton-shimmer {
  100% { transform: translateX(100%); }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-line::after { animation: none; }
}
.post-item {
  background: #fff;
  padding: 18px 22px;
  border-radius: 8px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
.post-head { display: flex; justify-content: space-between; align-items: center; }
.del-btn {
  margin-left: 8px;
  padding: 3px 12px;
  background: #f56c6c;
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}
.post-username { color: #ff9900; font-weight: 600; font-size: 14px; }
.post-time { color: #909399; font-size: 12px; }
.post-title { margin: 8px 0 6px; color: #303133; font-size: 16px; }
.post-content { margin: 0; color: #606266; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; }
.empty { text-align: center; color: #909399; margin-top: 30px; }
.load-error { color: #c45656; }
</style>
