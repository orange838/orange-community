import { ref } from 'vue'

const STYLE_KEY = 'site_style'

// 初始值来自 index.html 里的首屏脚本（已给 <html> 打好 style-glass / style-classic）
const styleMode = ref(
  document.documentElement.classList.contains('style-glass') ? 'glass' : 'classic'
)

export function useStyleMode() {
  const setMode = (next) => {
    if (next !== 'glass' && next !== 'classic') return
    styleMode.value = next
    const root = document.documentElement
    root.classList.toggle('style-glass', next === 'glass')
    root.classList.toggle('style-classic', next === 'classic')
    try {
      localStorage.setItem(STYLE_KEY, next)
    } catch (e) {
      /* 隐私模式下写不进去，忽略：本次会话仍然生效 */
    }
  }

  const toggle = () => setMode(styleMode.value === 'glass' ? 'classic' : 'glass')

  return { styleMode, setMode, toggle }
}