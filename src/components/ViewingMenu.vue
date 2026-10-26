<script setup>
// Whose picks and season stats the Picks and Season stats tabs show: you, or anyone else in the pool.
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({ players: Array, modelValue: Number })
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const root = ref(null)
const onDocTap = e => { if (open.value && !root.value?.contains(e.target)) open.value = false }
const onKey = e => { if (e.key === 'Escape') open.value = false }
onMounted(() => { document.addEventListener('pointerdown', onDocTap); document.addEventListener('keydown', onKey) })
onUnmounted(() => { document.removeEventListener('pointerdown', onDocTap); document.removeEventListener('keydown', onKey) })

// you first, then everyone else as the server sorts them (by name)
const list = computed(() => [...props.players].sort((a, b) => b.me - a.me))
const current = computed(() => props.players.find(p => p.id === props.modelValue))
const other = computed(() => !!current.value && !current.value.me)
const initial = p => (p?.displayName || '?').trim().charAt(0).toUpperCase()

function choose(p) {
  emit('update:modelValue', p.id)
  open.value = false
}
</script>

<template>
  <div ref="root" class="vm">
    <button :class="['pill', { other, on: open }]" :aria-expanded="open" aria-haspopup="listbox"
            :aria-label="`Viewing ${other ? current.displayName : 'your picks'}. Change player`" @click="open = !open">
      <span class="av" aria-hidden="true">{{ initial(current) }}</span>
      <span class="nm">{{ other ? current.displayName : 'You' }}</span>
      <svg class="chev" viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4" /></svg>
    </button>

    <div v-if="open" class="menu" role="listbox" aria-label="View a player">
      <p class="hd">View picks &amp; stats for</p>
      <button v-for="p in list" :key="p.id" type="button" role="option" :aria-selected="p.id === modelValue"
              :class="['row', { sel: p.id === modelValue, me: p.me }]" @click="choose(p)">
        <span class="av" aria-hidden="true">{{ initial(p) }}</span>
        <span class="txt">
          <b>{{ p.displayName }}<small v-if="p.me" class="you">You</small></b>
          <small v-if="p.teamName">{{ p.teamName }}</small>
        </span>
        <svg v-if="p.id === modelValue" class="tick" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" /></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.vm { position: relative; min-width: 0; }
.pill {
  display: inline-flex; align-items: center; gap: 7px; height: 40px; max-width: min(46vw, 220px); padding: 0 12px 0 5px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--text); font: inherit; font-weight: 700;
  cursor: pointer; transition: background .15s, border-color .15s;
}
.pill:hover, .pill.on { background: var(--soft); border-color: var(--line-strong); }
.pill:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }
/* looking at someone else: tinted, so it's obvious these aren't your picks */
.pill.other { background: var(--blue-tint); border-color: var(--blue-line); color: var(--blue-ink); }
.pill.other:hover, .pill.other.on { background: var(--blue-tint-2); }
.av {
  flex: none; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
  background: var(--chip); color: var(--text-2); font-size: .8rem; font-weight: 800;
}
.pill .av { width: 28px; height: 28px; }
.pill.other .av, .row.sel .av { background: var(--blue); color: #fff; }
.nm { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .9rem; }
.chev { flex: none; width: 10px; height: 6px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; opacity: .6; transition: transform .15s; }
.pill.on .chev { transform: rotate(180deg); }

.menu {
  position: absolute; right: 0; top: calc(100% + 6px); z-index: 40; width: min(280px, calc(100vw - 28px));
  max-height: min(70vh, 460px); overflow-y: auto; overscroll-behavior: contain;
  background: var(--card); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 12px 30px #0f172a1f; padding: 6px;
}
.hd { margin: 0; padding: 6px 10px 8px; font-size: .66rem; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; color: var(--faint); }
.row {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 7px 10px 7px 7px; border: 0; border-radius: 10px;
  background: none; font: inherit; color: var(--text); text-align: left; cursor: pointer;
}
.row:hover { background: var(--soft); }
.row:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }
.row.sel { background: var(--blue-tint); }
/* a hairline between you and everyone else */
.row.me { position: relative; margin-bottom: 7px; }
.row.me::after { content: ''; position: absolute; left: 10px; right: 10px; bottom: -4px; border-top: 1px solid var(--line-soft); }
.txt { display: flex; flex-direction: column; min-width: 0; flex: 1; gap: 1px; }
.txt b { font-size: .92rem; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.txt > small { font-size: .74rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.you { margin-left: 6px; padding: 1px 6px; border-radius: 99px; background: var(--chip); color: var(--text-2); font-size: .62rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; vertical-align: 1px; }
.tick { flex: none; width: 16px; height: 16px; fill: none; stroke: var(--blue); stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
</style>
