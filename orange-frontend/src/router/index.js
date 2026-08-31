import { createRouter, createWebHashHistory } from 'vue-router'
import { currentUser } from '../store'

// 1. 引入你左侧目录里建好的那 4 个文件
// 注意路径：因为 index.js 在 router 文件夹里，所以要退一级到 view 文件夹哦
import Home from '../view/Home.vue'
import Checkin from '../view/CheckIn.vue'
import Notice from '../view/Notice.vue'
import Profile from '../view/Profile.vue'
import Admin from '../view/Admin.vue'

const routes = [
  // 2. 把 component 指向刚才引入的变量
  { path: '/', component: Home },
  { path: '/checkin', component: Checkin },
  { path: '/notice', component: Notice },
  { path: '/profile', component: Profile },
  { path: '/admin', component: Admin }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.path === '/admin' && currentUser.info?.role !== 'admin') {
    next('/profile')
    return
  }
  next()
})

export default router