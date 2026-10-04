<script setup>
// Countdown to the next pick deadline for the current week (Thursday game, then Sunday/Monday).
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getDeadlines } from '../api.js'

const groups = ref([])
const week = ref(null)
const now = ref(Date.now())
let tick, refresh

async function load() {
  try {
    const d = await getDeadlines()
    groups.value = d.groups
    week.value = d.week
  } catch { /* no countdown when ESPN is unreachable */ }
}
onMounted(() => {
  load()
  tick = setInterval(() => (now.value = Date.now()), 1000)
  refresh = setInterval(load, 15 * 60 * 1000)
})
onUnmounted(() => { clearInterval(tick); clearInterval(refresh) })

const next = computed(() => groups.value.find(g => Date.parse(g.deadline) > now.value))
const left = computed(() => {
  if (!next.value) return ''
  const s = Math.floor((Date.parse(next.value.deadline) - now.value) / 1000)
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d) return `${d}d ${h}h ${m}m`
  if (h) return `${h}h ${m}m`
  return `${m}m ${s % 60}s`
})
const urgent = computed(() => next.value && Date.parse(next.value.deadline) - now.value < 3 * 3600 * 1000)
const when = computed(() => next.value && new Date(next.value.deadline).toLocaleString([], {
  weekday: 'short', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
}))
</script>

<template>
  <p v-if="next" :class="['countdown', { urgent }]">
    <span>⏱ Week {{ week }} · <b>{{ next.label }}</b> picks lock in</span>
    <b class="left">{{ left }}</b>
    <small>{{ when }}</small>
  </p>
  <p v-else-if="groups.length" class="countdown done">🔒 All week {{ week }} picks are locked.</p>
</template>

<style scoped>
.countdown { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; margin: 0 0 12px; padding: 10px 14px; border-radius: 14px; background: #eff6ff; color: #1e3a8a; font-size: .9rem; }
.left { font-size: 1.15rem; font-variant-numeric: tabular-nums; }
small { color: #64748b; }
.urgent { background: #fef2f2; color: #991b1b; }
.done { background: #f1f5f9; color: #475569; }
</style>
