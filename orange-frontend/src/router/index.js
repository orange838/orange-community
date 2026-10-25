import { createRouter, createWebHashHistory } from 'vue-router'
import { currentUser } from '../store'

// 1. 引入你左侧目录里建好的那 4 个文件
// 注意路径：因为 index.js 在 router 文件夹里，所以要退一级到 view 文件夹哦
import Home from '../view/Home.vue'
import Posts from '../view/Posts.vue'
import PlayCaptchaPage from '../view/PlayCaptchaPage.vue'
import LoginPage from '../view/LoginPage.vue'
import Tasks from '../view/Tasks.vue'
import Notice from '../view/Notice.vue'
import Profile from '../view/Profile.vue'
import Admin from '../view/Admin.vue'
import OAuthCallback from '../view/OAuthCallback.vue'

const routes = [
  // 2. 把 component 指向刚才引入的变量
  { path: '/', component: Home },
  { path: '/posts', component: Posts },
  { path: '/captcha', component: PlayCaptchaPage },
  { path: '/login', component: LoginPage },
  { path: '/tasks', component: Tasks },
  { path: '/checkin', redirect: '/tasks' },
  { path: '/notice', component: Notice },
  { path: '/profile', component: Profile },
  { path: '/admin', component: Admin },
  { path: '/oauth-callback', component: OAuthCallback },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.path === '/admin' && !['admin', 'super_admin'].includes(currentUser.info?.role)) {
    next('/profile')
    return
  }
  next()
})

export default router