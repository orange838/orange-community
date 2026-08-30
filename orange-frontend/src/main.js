import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// 【新增】引入状态仓库
import { currentUser } from './store'

const app = createApp(App)

app.use(router)

// 【新增】挂载到全局属性 $user，这样任何组件都能用 this.$user 访问
app.config.globalProperties.$user = currentUser

app.mount('#app')