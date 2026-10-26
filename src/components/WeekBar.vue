<script setup>
// Weeks 1–18 in one sideways strip. The selected week always sits in the middle: it glides there when you pick
// one, and jumps there when the strip first shows or changes size (e.g. coming back to the Picks tab).
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({ modelValue: Number, currentWeek: Number, summaries: Array })
const emit = defineEmits(['update:modelValue'])

const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1)
const byWeek = computed(() => Object.fromEntries(props.summaries.map(s => [s.week, s])))
const strip = ref(null)
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

// scroll only the strip (scrollIntoView would also nudge the page)
function center(smooth) {
  const el = strip.value
  const btn = el?.querySelector(`[data-week="${props.modelValue}"]`)
  if (!btn || !el.clientWidth) return
  const left = btn.offsetLeft + btn.offsetWidth / 2 - el.clientWidth / 2
  el.scrollTo({ left, behavior: smooth && !reduceMotion.matches ? 'smooth' : 'auto' })
}

let ro
onMounted(() => {
  center(false)
  ro = new ResizeObserver(() => center(false))
  ro.observe(strip.value)
})
onUnmounted(() => ro?.disconnect())
watch(() => props.modelValue, () => center(true), { flush: 'post' })

const pick = w => emit('update:modelValue', Math.min(18, Math.max(1, w)))
function onKey(e) {
  const step = { ArrowLeft: -1, ArrowRight: 1 }[e.key]
  if (!step) return
  e.preventDefault()
  pick(props.modelValue + step)
  // keep focus on the selected week so the next arrow press carries on from there
  requestAnimationFrame(() => strip.value?.querySelector(`[data-week="${props.modelValue}"]`)?.focus({ preventScroll: true }))
}
</script>

<template>
  <nav ref="strip" class="weekbar" aria-label="Select week" @keydown="onKey">
    <button
      v-for="w in WEEKS"
      :key="w"
      type="button"
      :data-week="w"
      :aria-current="w === modelValue ? 'true' : null"
      :tabindex="w === modelValue ? 0 : -1"
      :class="['wk', { on: w === modelValue, cur: w === currentWeek, done: byWeek[w] }]"
      @click="pick(w)"
    >
      <i v-if="byWeek[w]?.live" class="live" title="Games live now"></i>
      <span class="n">{{ w }}</span>
      <span class="s" v-if="byWeek[w]" :class="{ neg: byWeek[w].score < 0 }">{{ byWeek[w].score }}</span>
      <span class="s" v-else-if="w === currentWeek">now</span>
      <span class="s" v-else>·</span>
    </button>
  </nav>
</template>

<style scoped>
.weekbar {
  --w: 52px;
  position: relative;  /* offsetLeft is measured from here */
  display: flex; gap: 6px; overflow-x: auto; overscroll-behavior-x: contain;
  padding: 4px 0 12px;
  margin-bottom: 2px;
  scroll-snap-type: x proximity; scrollbar-width: none; -webkit-overflow-scrolling: touch;
  /* fade the weeks out at the edges */
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 36px, #000 calc(100% - 36px), transparent);
  mask-image: linear-gradient(90deg, transparent, #000 36px, #000 calc(100% - 36px), transparent);
}
.weekbar::-webkit-scrollbar { display: none; }
/* room on both ends so week 1 and week 18 can sit in the middle too (spacers: end padding doesn't always scroll) */
.weekbar::before, .weekbar::after { content: ''; flex: none; width: calc(50% - var(--w) / 2 - 6px); }
.wk {
  position: relative; flex: none; width: var(--w); scroll-snap-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 1px; padding: 6px 0;
  border-radius: 12px; border: 1px solid var(--line); background: var(--card); color: var(--text-2); cursor: pointer;
  transition: background .18s, border-color .18s, color .18s, transform .18s;
}
@media (hover: hover) { .wk:not(.on):hover { background: var(--card-2); border-color: var(--line-strong); } }
.wk:active { transform: scale(.95); }
.wk:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }
.n { font-weight: 800; font-size: 1rem; font-variant-numeric: tabular-nums; }
.s { font-size: .68rem; font-weight: 700; color: var(--faint); min-height: 1em; font-variant-numeric: tabular-nums; }
.done .s { color: var(--pos); }
.done .s.neg { color: var(--neg); }
.cur { border-color: #93c5fd; }
.cur .s { color: var(--blue); }
.wk.on { background: var(--ink); border-color: var(--ink); color: var(--on-ink); transform: translateY(-1px); box-shadow: 0 4px 12px #0f172a26; }
.wk.on .s { color: var(--faint); }
.live { position: absolute; top: 5px; right: 5px; width: 7px; height: 7px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 0 2px var(--card); animation: blink 1.4s ease-in-out infinite; }
.on .live { box-shadow: 0 0 0 2px var(--ink); }
@keyframes blink { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .live { animation: none; } .wk { transition: none; } }
</style>
