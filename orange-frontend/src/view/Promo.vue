<template>
  <div class="page-container">
    <h2>🔗 推广链接</h2>
    <p class="promo-intro">
      这里放的是我在用的服务和作品，点进去看看。<template v-if="styleMode === 'glass'">前排两个就是页面底部那两个徽章，切进来的时候它们会自己飞上来。</template>
    </p>

    <div class="promo-list">
      <a
        v-for="(item, index) in promos"
        :key="item.key"
        ref="cardRefs"
        :data-fly-from="item.flyFrom"
        class="promo-card"
        :class="'promo-' + item.key"
        :href="item.href"
        target="_blank"
        rel="noopener noreferrer"
        :style="{ transitionDelay: index * 70 + 'ms' }"
      >
        <span class="promo-tag">{{ item.tag }}</span>
        <span class="promo-body">
          <span class="promo-title">{{ item.title }}</span>
          <span class="promo-desc">{{ item.desc }}</span>
          <span v-if="item.meta" class="promo-meta">{{ item.meta }}</span>
        </span>
        <span class="promo-arrow" aria-hidden="true">↗</span>
      </a>
    </div>

    <p class="promo-foot">链接均为直达官方站点，不带中间跳转。有想互换友链的可以到个人中心联系我。</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useStyleMode } from '../composables/useStyleMode'

const { styleMode } = useStyleMode()
const cardRefs = ref([])
let footerEl = null

const promos = [
  {
    key: 'digitalplat',
    flyFrom: 'digitalplat',
    tag: 'DigitalPlat',
    title: '本网站由 DigitalPlat FreeDomain 提供支持',
    desc: '来 DigitalPlat 免费领取域名',
    href: 'https://dashboard.digitalplat.org/signup?ref=AYxV65nOjF'
  },
  {
    key: 'tudou',
    flyFrom: 'tudou',
    tag: '土豆公益',
    title: '邀请你注册土豆公益',
    desc: '免费开游戏联机服务器',
    href: 'https://tudouai.cn/r/3n6bl5b'
  },
  {
    key: 'railway',
    flyFrom: '',
    tag: 'MOD',
    title: '纵横铁路 · ZongHeng Railway',
    desc: '走出出生点，铁路已经在那里了。自动撒站、自动连线、自动架桥钻洞，把整张地图连成能坐车走通的路网。',
    meta: 'Minecraft 1.21.1 · NeoForge 21.1.x · v1.3.0 · GPL-3.0',
    href: 'https://zhtl.cslblog.dpdns.org'
  }
]

// 只有新版亚克力模式才做飞入动画；兼容模式直接静态显示
function playFlyIn() {
  if (styleMode.value !== 'glass') return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const cards = (cardRefs.value || []).filter(Boolean)
  const animated = []

  cards.forEach((card) => {
    const key = card.dataset.flyFrom
    if (!key) return
    const source = document.querySelector(`[data-promo-badge="${key}"]`)
    if (!source) return

    const from = source.getBoundingClientRect()
    const to = card.getBoundingClientRect()
    if (!to.width || !to.height) return

    const dx = from.left - to.left
    const dy = from.top - to.top
    const sx = from.width / to.width
    const sy = from.height / to.height
    if (!Number.isFinite(dx) || !Number.isFinite(sx) || sx <= 0 || sy <= 0) return

    card.style.transition = 'none'
    card.style.transformOrigin = 'top left'
    card.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`
    card.style.opacity = '0'
    animated.push(card)

    // 源徽章一边被复制走，一边淡出
    source.classList.add('is-flown')
  })

  if (animated.length) {
    footerEl = document.querySelector('.site-footer')
    if (footerEl) footerEl.classList.add('is-flown-away')
  }

  // 两帧之后再放开过渡，确保起始位置先被浏览器记录
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      animated.forEach((card) => {
        card.style.transition = ''
        card.style.transformOrigin = ''
        card.style.transform = ''
        card.style.opacity = '1'
      })
    })
  })
}

function restore() {
  ;(cardRefs.value || []).filter(Boolean).forEach((card) => {
    card.style.transition = ''
    card.style.transformOrigin = ''
    card.style.transform = ''
    card.style.opacity = ''
  })
  document.querySelectorAll('[data-promo-badge].is-flown').forEach((el) => el.classList.remove('is-flown'))
  const footer = footerEl || document.querySelector('.site-footer')
  if (footer) footer.classList.remove('is-flown-away')
  footerEl = null
}

onMounted(async () => {
  await nextTick()
  // 等一帧，让内容区完成布局后再量尺寸
  requestAnimationFrame(playFlyIn)
})

onBeforeUnmount(restore)
</script>

<style scoped>
.promo-intro {
  color: #909399;
  font-size: 14px;
  line-height: 1.7;
  margin: 10px 0 18px;
}

.promo-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 720px;
}

.promo-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e4e7ed;
  background: #fff;
  color: #0f172a;
  text-decoration: none;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  transition: transform 0.62s cubic-bezier(0.22, 0.68, 0.32, 1), opacity 0.5s ease,
    box-shadow 0.25s ease, border-color 0.25s ease;
  will-change: transform;
}

.promo-card:hover {
  border-color: var(--promo-accent, #ff9900);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
}

.promo-tag {
  flex: none;
  padding: 5px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  background: #eff6ff;
  color: #1d4ed8;
}

.promo-tudou .promo-tag {
  background: #fde68a;
  color: #92400e;
}

.promo-railway {
  --promo-accent: #059669;
}

.promo-railway .promo-tag {
  background: #d1fae5;
  color: #047857;
}

.promo-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.promo-title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.4;
}

.promo-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.promo-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

.promo-arrow {
  margin-left: auto;
  flex: none;
  color: #c0c4cc;
  font-size: 15px;
}

.promo-card:hover .promo-arrow {
  color: var(--promo-accent, #ff9900);
}

.promo-foot {
  margin-top: 18px;
  font-size: 13px;
  color: #a8abb2;
}

@media (max-width: 640px) {
  .promo-card {
    padding: 13px 14px;
    gap: 10px;
    align-items: flex-start;
  }
  .promo-tag {
    margin-top: 2px;
  }
}
</style>
