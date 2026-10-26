<script setup>
// Under a game: two slim bars, laid out like the team cards above (away left, home right).
// Pool = how the pool picked it (once it kicks off; tap for everyone's pick). Public = DraftKings' % of bets.
import { computed } from 'vue'
import { pct, teamColors, textColor } from '../pool.js'
import { isDark } from '../theme.js'

const props = defineProps({
  sides: Array,     // [{ key: 'fav'|'dog', abbr, name, color, alternateColor }] in display order (away, home)
  pool: Object,     // this game's pool entry: { revealed, fav: {count, points}, dog, none, picks }
  split: Object,    // DraftKings public: { sides: { ABBR: { bets, handle, line } } }
  mine: String,     // your pick on this game ('fav' | 'dog')
})
defineEmits(['details'])

const colors = computed(() => teamColors(...props.sides, isDark.value))
const ink = i => textColor(colors.value[i], isDark.value)

const revealed = computed(() => !!props.pool?.revealed)
const picked = computed(() => (revealed.value ? props.pool.fav.count + props.pool.dog.count : 0))
const poolPct = computed(() => props.sides.map(s => pct(props.pool?.[s.key]?.count || 0, picked.value)))
const poolTitle = computed(() => (revealed.value
  ? `Pool: ${props.sides.map(s => `${props.pool[s.key].count} on ${s.name}`).join(', ')}. Tap for everyone's pick.`
  : ''))

const pub = computed(() => {
  const s = props.split?.sides
  const rows = s && props.sides.map(x => s[x.abbr])
  return rows?.every(r => r?.bets != null) ? rows : null
})
const pubTitle = computed(() => (pub.value
  ? `DraftKings public betting: ${props.sides.map((x, i) => `${x.name} ${pub.value[i].bets}% of bets, ${pub.value[i].handle}% of money`).join(' · ')}`
  : ''))
</script>

<template>
  <div v-if="pool || pub" class="insights">
    <button v-if="revealed" type="button" class="ln" :title="poolTitle" :aria-label="poolTitle" @click="$emit('details')">
      <span class="lbl">Pool</span>
      <b :class="{ me: mine === sides[0].key }" :style="{ color: ink(0) }">{{ poolPct[0] }}%</b>
      <span class="pbar" aria-hidden="true">
        <i :style="{ flexGrow: picked ? poolPct[0] : 1, background: colors[0] }"></i>
        <i :style="{ flexGrow: picked ? poolPct[1] : 1, background: colors[1] }"></i>
      </span>
      <b :class="['r', { me: mine === sides[1].key }]" :style="{ color: ink(1) }">{{ poolPct[1] }}%</b>
      <span class="go" aria-hidden="true">›</span>
    </button>
    <div v-else-if="pool" class="ln muted">
      <span class="lbl">Pool</span>
      <span class="wait"><span aria-hidden="true">🔒</span> Locked until kickoff</span>
    </div>

    <div v-if="pub" class="ln" :title="pubTitle">
      <span class="lbl">Public</span>
      <b :style="{ color: ink(0) }">{{ pub[0].bets }}%</b>
      <span class="pbar" aria-hidden="true">
        <i :style="{ flexGrow: pub[0].bets, background: colors[0] }"></i>
        <i :style="{ flexGrow: pub[1].bets, background: colors[1] }"></i>
      </span>
      <b class="r" :style="{ color: ink(1) }">{{ pub[1].bets }}%</b>
      <span class="go" aria-hidden="true"></span>
    </div>
  </div>
</template>

<style scoped>
.insights { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--line-soft); display: flex; flex-direction: column; gap: 2px; }
.ln {
  display: grid; grid-template-columns: 48px 40px minmax(0, 1fr) 40px 12px; align-items: center; gap: 8px;
  width: 100%; min-height: 24px; padding: 0; border: 0; background: none; font: inherit; text-align: left; color: inherit;
}
button.ln { cursor: pointer; border-radius: 8px; }
button.ln:hover .pbar { filter: brightness(1.08); }
button.ln:hover .go { color: var(--blue); }
button.ln:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }
.lbl { font-size: .6rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--faint); }
.ln b { font-size: .8rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.ln b.r { text-align: right; }
.ln b.me { text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }
.pbar { display: flex; gap: 2px; height: 6px; border-radius: 99px; overflow: hidden; }
.pbar i { flex: 1 1 0; min-width: 0; }
.go { color: var(--faint); font-weight: 800; font-size: 1rem; line-height: 1; text-align: right; }
.wait { grid-column: 2 / -1; font-size: .74rem; color: var(--faint); }
</style>
