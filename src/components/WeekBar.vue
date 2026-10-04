<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({ modelValue: Number, currentWeek: Number, summaries: Array })
defineEmits(['update:modelValue'])

const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1)
const byWeek = computed(() => Object.fromEntries(props.summaries.map(s => [s.week, s])))
const strip = ref(null)

function centerSelected() {
  strip.value?.querySelector('.on')?.scrollIntoView({ inline: 'center', block: 'nearest' })
}
onMounted(centerSelected)
watch(() => props.modelValue, () => nextTick(centerSelected))
</script>

<template>
  <nav ref="strip" class="weekbar" aria-label="Select week">
    <button
      v-for="w in WEEKS"
      :key="w"
      :class="['wk', { on: w === modelValue, cur: w === currentWeek, done: byWeek[w] }]"
      @click="$emit('update:modelValue', w)"
    >
      <span class="n">{{ w }}</span>
      <span class="s" v-if="byWeek[w]" :class="{ neg: byWeek[w].score < 0 }">{{ byWeek[w].score }}</span>
      <span class="s" v-else-if="w === currentWeek">now</span>
      <span class="s" v-else>·</span>
    </button>
  </nav>
</template>

<style scoped>
.weekbar { display: flex; gap: 6px; overflow-x: auto; padding: 4px 2px 10px; scrollbar-width: thin; }
.wk { flex: none; width: 52px; display: flex; flex-direction: column; align-items: center; gap: 1px; padding: 6px 0; border-radius: 12px; border: 1px solid #e2e8f0; background: #fff; cursor: pointer; color: #475569; }
.wk:hover { background: #f8fafc; }
.n { font-weight: 800; font-size: 1rem; }
.s { font-size: .68rem; font-weight: 700; color: #94a3b8; min-height: 1em; }
.done .s { color: #15803d; }
.done .s.neg { color: #b91c1c; }
.cur { border-color: #93c5fd; }
.cur .s { color: #2563eb; }
.on { background: #0f172a; border-color: #0f172a; color: #fff; }
.on .s { color: #cbd5e1 !important; }
</style>
