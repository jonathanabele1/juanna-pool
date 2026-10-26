<script setup>
// Press and hold (or double-click) a team: its season so far on the sheet lines, and how you've done picking or fading it.
import { computed } from 'vue'

const props = defineProps({
  team: Object,    // ESPN team (logo, location, name, record)
  raw: String,     // sheet name, if there's no ESPN team
  role: String,    // 'fav' | 'dog' in this game
  stats: Object,   // backend team_stats row (weeks before this one), or null
})

const rec = o => (o && o.w + o.l + (o.p || 0) ? `${o.w}–${o.l}${o.p ? `–${o.p}` : ''}` : '—')
const sgn = n => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '±0')
const tone = n => (n > 0 ? 'up' : n < 0 ? 'down' : '')
const s = computed(() => props.stats)
const roleRec = computed(() => (props.role === 'dog' ? s.value?.asDog : s.value?.asFav))
const tiles = computed(() => [
  { label: 'ATS', value: rec(s.value?.ats) },
  { label: props.role === 'dog' ? 'As underdog' : 'As favorite', value: rec(roleRec.value) },
  { label: 'Picking them', value: rec(s.value?.backing), net: s.value?.backing.n ? s.value.backing.net : null },
  { label: 'Fading them', value: rec(s.value?.fading), net: s.value?.fading.n ? s.value.fading.net : null },
])
</script>

<template>
  <div class="tpeek" role="dialog" :aria-label="`${team ? `${team.location} ${team.name}` : raw} season stats`">
    <div class="tp-head">
      <img v-if="team?.logo" :src="team.logo" alt="" draggable="false" />
      <span class="tp-name"><small>{{ team?.location }}</small><b>{{ team?.name || raw?.toUpperCase() }}</b></span>
      <span v-if="team?.record" class="tp-rec"><b>{{ team.record.replace(/-/g, '–') }}</b><small>Record</small></span>
    </div>

    <p v-if="!stats" class="tp-empty">No finished games on the sheets yet.</p>
    <template v-else>
      <dl class="tp-grid">
        <div v-for="t in tiles" :key="t.label">
          <dt>{{ t.label }}</dt>
          <dd>{{ t.value }}<span v-if="t.net != null" :class="['tp-net', tone(t.net)]">{{ sgn(t.net) }}</span></dd>
        </div>
      </dl>
      <div v-if="stats.form?.length" class="tp-form">
        <span>Last {{ stats.form.length }} ATS</span>
        <i v-for="(o, k) in stats.form" :key="k" :class="o" :title="o === 'win' ? 'Covered' : o === 'loss' ? 'Didn’t cover' : 'Push'"></i>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tpeek {
  position: absolute; z-index: 30; width: min(264px, 100%); box-sizing: border-box;
  display: flex; flex-direction: column; gap: 10px; padding: 12px 14px;
  background: var(--inv-bg); color: var(--inv-text); border: 1px solid var(--inv-line); border-radius: 16px; box-shadow: 0 14px 32px var(--inv-shadow);
  pointer-events: none; animation: tpeek .14s ease-out;
}
.tpeek::before { content: ''; position: absolute; left: calc(var(--arrow) - 5px); width: 10px; height: 10px; background: inherit; transform: rotate(45deg); border-radius: 2px; top: -5px; }
.tpeek.above::before { top: auto; bottom: -5px; }
@keyframes tpeek { from { opacity: 0; transform: translateY(-4px); } }
.tpeek.above { animation-name: tpeek-up; }
@keyframes tpeek-up { from { opacity: 0; transform: translateY(4px); } }
@media (prefers-reduced-motion: reduce) { .tpeek { animation: none; } }

.tp-head { display: flex; align-items: center; gap: 10px; }
.tp-head img { width: 34px; height: 34px; object-fit: contain; flex: none; }
.tp-name { display: flex; flex-direction: column; min-width: 0; line-height: 1.15; }
.tp-name small { font-size: .7rem; color: var(--inv-muted); }
.tp-name b { font-size: 1rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tp-rec { margin-left: auto; display: flex; flex-direction: column; align-items: flex-end; line-height: 1.1; }
.tp-rec b { font-size: 1.05rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.tp-rec small, .tp-grid dt, .tp-form span { font-size: .6rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--inv-faint); }

.tp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 0; background: var(--inv-line); border-radius: 12px; overflow: hidden; }
.tp-grid > div { background: var(--inv-cell); padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.tp-grid dd { margin: 0; font-size: 1rem; font-weight: 800; font-variant-numeric: tabular-nums; display: flex; align-items: baseline; gap: 6px; }
.tp-net { font-size: .72rem; font-weight: 700; color: var(--inv-muted); }
.tp-net.up { color: var(--inv-good); } .tp-net.down { color: var(--inv-bad); }

.tp-form { display: flex; align-items: center; gap: 5px; }
.tp-form span { margin-right: auto; }
.tp-form i { width: 9px; height: 9px; border-radius: 50%; background: var(--inv-faint); }
.tp-form i.win { background: #22c55e; } .tp-form i.loss { background: #ef4444; }
.tp-empty { margin: 0; font-size: .8rem; color: var(--inv-muted); }
</style>
