// 样式模式（新版亚克力 / 兼容纯色）必须在首屏渲染前确定，避免刷新时闪一下。
// 独立成文件是为了让 CSP 的 script-src 可以不带 'unsafe-inline'。
(function () {
  var mode = 'classic'
  try {
    var saved = localStorage.getItem('site_style')
    if (saved === 'glass' || saved === 'classic') mode = saved
  } catch (e) {}
  try {
    var canBlur = !!(window.CSS && CSS.supports && (CSS.supports('backdrop-filter', 'blur(1px)') || CSS.supports('-webkit-backdrop-filter', 'blur(1px)')))
    if (mode === 'glass' && !canBlur) mode = 'classic'
  } catch (e) {
    mode = 'classic'
  }
  document.documentElement.classList.add(mode === 'glass' ? 'style-glass' : 'style-classic')
})()
