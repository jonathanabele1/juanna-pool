<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

defineProps({ week: Number, busy: Boolean, status: String, hasGames: Boolean })
const emit = defineEmits(['close', 'file'])

const over = ref(false)
const input = ref(null)
const onKey = e => e.key === 'Escape' && emit('close')
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

const pick = f => f && emit('file', f)
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="dialog" role="dialog" aria-modal="true" :aria-label="`Upload week ${week} sheet`">
      <header>
        <h3>Upload week {{ week }} sheet</h3>
        <button class="x" aria-label="Close" @click="$emit('close')">✕</button>
      </header>

      <div
        :class="['zone', { over, busy }]"
        tabindex="0"
        @click="!busy && input.click()"
        @keydown.enter="!busy && input.click()"
        @dragover.prevent="over = true"
        @dragleave="over = false"
        @drop.prevent="over = false; pick($event.dataTransfer.files[0])"
      >
        <input ref="input" type="file" accept="image/*" hidden @change="pick($event.target.files[0])" />
        <template v-if="!busy">
          <span class="icon">🖼️</span>
          <b>Drop the spreads image here</b>
          <span>or click to browse · or just paste it (⌘V / Ctrl+V)</span>
        </template>
        <template v-else>
          <span class="spin" aria-hidden="true"></span>
          <b>Reading the sheet…</b>
        </template>
      </div>

      <p v-if="status" :class="['status', { warn: status.includes('No games') || status.includes('failed') }]">{{ status }}</p>
      <p v-if="hasGames && !busy" class="note">The sheet’s spreads replace the DraftKings ones, and your picks carry over for every matchup that’s still there.</p>

      <footer><button class="btn ghost" @click="$emit('close')">Close</button></footer>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; z-index: 50; display: grid; place-items: center; padding: 16px; background: #0f172a8c; backdrop-filter: blur(3px); }
.dialog { width: min(520px, 100%); background: var(--card); border-radius: 20px; padding: 18px; box-shadow: 0 20px 60px #0006; display: flex; flex-direction: column; gap: 12px; }
header { display: flex; justify-content: space-between; align-items: center; }
h3 { margin: 0; font-size: 1.05rem; }
.x { border: 0; background: var(--soft); width: 30px; height: 30px; border-radius: 50%; cursor: pointer; color: var(--text-2); }
.x:hover { background: var(--chip); }
.zone { display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; padding: 34px 16px; border: 2px dashed var(--line-strong); border-radius: 16px; background: var(--card-2); color: var(--muted); cursor: pointer; transition: border-color .15s, background .15s; font-size: .85rem; }
.zone b { color: var(--text); font-size: 1rem; }
.zone:hover, .zone:focus-visible, .zone.over { border-color: #2563eb; background: var(--blue-tint); outline: none; }
.zone.busy { cursor: progress; border-style: solid; border-color: #93c5fd; }
.icon { font-size: 2rem; }
.spin { width: 28px; height: 28px; border-radius: 50%; border: 3px solid var(--blue-line); border-top-color: #2563eb; animation: spin .8s linear infinite; margin-bottom: 6px; }
@keyframes spin { to { transform: rotate(360deg); } }
.status { margin: 0; font-size: .85rem; color: var(--text-2); background: var(--soft); padding: 8px 10px; border-radius: 10px; }
.status.warn { background: var(--amber-tint); color: var(--amber-ink); }
.note { margin: 0; font-size: .78rem; color: var(--faint); }
footer { display: flex; justify-content: flex-end; }
</style>
