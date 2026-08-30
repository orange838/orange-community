import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // 1. 引入刚才创建的路由配置

const app = createApp(App)

app.use(router) // 2. 【核心】告诉 Vue 使用路由插件！不做这一步 router-link 就是废铁

app.mount('#app')