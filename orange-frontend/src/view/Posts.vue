<template>
  <div class="page-container">
    <h2>📋 帖子广场</h2>

    <!-- 发帖表单 -->
    <div class="post-form-card">
      <template v-if="isLoggedIn">
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
      <div v-else class="need-login">
        登录后才能发帖，请先 <a href="#" @click.prevent="goLogin">登录</a>。
      </div>
    </div>

    <!-- 帖子列表 -->
    <div class="post-list" v-if="posts.length">
      <div class="post-item" v-for="p in posts" :key="p.id">
        <div class="post-head">
          <span class="post-username">{{ p.username }}</span>
          <span class="post-time">{{ formatTime(p.created_at) }}</span>
        </div>
        <h3 class="post-title">{{ p.title }}</h3>
        <p class="post-content">{{ p.content }}</p>
      </div>
    </div>
    <p class="empty" v-else>还没有帖子，来发第一帖吧～</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { currentUser } from '../store'

const API = import.meta.env.VITE_API_URL
const form = ref({ title: '', content: '' })
const posts = ref([])
const submitting = ref(false)
const hitWords = ref([])
const lastResult = ref(null)

const isLoggedIn = computed(() => Boolean(currentUser.info?.email))
const goLogin = () => window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg: '请先登录后再发帖', type: 'error' } }))

const toast = (msg, type) => window.dispatchEvent(new CustomEvent('show-toast', { detail: { msg, type } }))

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const loadPosts = async () => {
  try {
    const res = await fetch(`${API}/api/posts`)
    const data = await res.json()
    posts.value = data.posts || []
  } catch {
    posts.value = []
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

onMounted(loadPosts)
</script>

<style scoped>
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
.post-item {
  background: #fff;
  padding: 18px 22px;
  border-radius: 8px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
.post-head { display: flex; justify-content: space-between; align-items: center; }
.post-username { color: #ff9900; font-weight: 600; font-size: 14px; }
.post-time { color: #909399; font-size: 12px; }
.post-title { margin: 8px 0 6px; color: #303133; font-size: 16px; }
.post-content { margin: 0; color: #606266; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; }
.empty { text-align: center; color: #909399; margin-top: 30px; }
</style>
