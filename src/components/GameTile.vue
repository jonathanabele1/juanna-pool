<script setup>
// Compact version of GameRow for the desktop grid: one game per small tile, everything at a glance.
import { computed, ref } from 'vue'
import { coverNow, resolveGame } from '../lines.js'
import { pct } from '../pool.js'
import PoolDialog from './PoolDialog.vue'

const props = defineProps({
  game: Object, events: Array, now: Object, result: Object,
  readonly: Boolean,  // view mode: nothing can be changed
  pool: Object,       // how the pool picked this game (revealed at kickoff)
  split: Object,      // DraftKings public betting
})

const DAY_NAMES = { Thurs: 'Thu', Tues: 'Tue', Wed: 'Wed', Fri: 'Fri', Sat: 'Sat', Sun: 'Sun', Mon: 'Mon' }

const r = computed(() => resolveGame(props.game, props.events))
const g = computed(() => props.game)
const ev = computed(() => r.value.event)
const gameState = computed(() => ev.value?.state || props.result?.state)
const live = computed(() => gameState.value === 'in')
const final = computed(() => gameState.value === 'post')
const started = computed(() => !!props.now?.locked || live.value)
const noLine = computed(() => g.value.source === 'schedule' && g.value.hasLine === false)

// Away on top, home underneath.
const sides = computed(() => {
  const fav = { key: 'fav', team: r.value.favTeam, home: r.value.favHome }
  const dog = { key: 'dog', team: r.value.dogTeam, home: !r.value.favHome }
  return fav.home ? [dog, fav] : [fav, dog]
})
const spreadText = key => (noLine.value ? '—' : !g.value.spread ? 'PK' : key === 'fav' ? `−${g.value.spread}` : `+${g.value.spread}`)
const nameOf = s => s.team?.name || g.value[s.key]?.toUpperCase()

const scoreFor = key => {
  if (!live.value && !final.value) return null
  const team = key === 'fav' ? r.value.favTeam : r.value.dogTeam
  const s = ev.value && team ? ev.value.scores?.[team === ev.value.home ? 'home' : 'away'] : null
  return s ?? props.result?.[key === 'fav' ? 'favScore' : 'dogScore'] ?? null
}
const trailing = key => {
  if (!final.value) return false
  const f = scoreFor('fav'), d = scoreFor('dog')
  return f != null && d != null && f !== d && (key === 'fav' ? f < d : d < f)
}

const cover = computed(() => (g.value.pick ? coverNow(g.value, props.events) : null))
const outcome = computed(() => {
  if (!final.value || !g.value.pick) return null
  const o = props.result?.outcome
  return ['win', 'loss', 'push'].includes(o) ? o : cover.value?.status || null
})
const liveStatus = computed(() => (live.value ? cover.value?.status || null : null))
const num = n => String(Math.abs(n)).replace('.5', '½')

const when = computed(() => {
  if (final.value) return /OT/.test(ev.value?.detail || '') ? 'Final · OT' : 'Final'
  if (live.value) {
    const l = ev.value?.live
    if (!l) return ev.value?.detail || 'Live'
    if (l.halftime) return 'Halftime'
    if (l.endOfPeriod) return `End of ${l.quarter}`
    return [l.quarter, l.clock].filter(Boolean).join(' · ')
  }
  return `${DAY_NAMES[g.value.day] || g.value.day}${g.value.time ? ` · ${g.value.time}` : ''}`
})
const statusText = computed(() => {
  if (outcome.value) return { win: `Covered +${props.result?.earned ?? g.value.points}`, loss: 'Missed', push: `Push +${num(props.result?.earned ?? g.value.points / 2)}` }[outcome.value]
  if (liveStatus.value) return liveStatus.value === 'push' ? 'On the number' : liveStatus.value === 'win' ? `Covering by ${num(cover.value.margin)}` : `Short by ${num(cover.value.margin)}`
  return ''
})

function choose(key) { if (!props.readonly) g.value.pick = g.value.pick === key ? null : key }
function bump(d) { g.value.points = Math.min(50, Math.max(0, (Number(g.value.points) || 0) + d)) }
const isLoy = computed(() => Number(g.value.points) === 50)
const broken = ref({})

// the pool's split on this game, once it kicks off
const poolOpen = ref(false)
const poolSides = computed(() => sides.value.map(s => ({
  key: s.key, abbr: s.team?.abbr || (g.value[s.key] || '').toUpperCase(), name: nameOf(s), logo: s.team?.logo,
  spread: spreadText(s.key), color: s.team?.color, alternateColor: s.team?.alternateColor,
})))
const poolTop = computed(() => {
  const p = props.pool
  if (!p?.revealed) return null
  const n = p.fav.count + p.dog.count
  if (!n) return { text: 'No picks' }
  const top = poolSides.value.reduce((a, b) => (p[b.key].count > p[a.key].count ? b : a))
  if (p.fav.count === p.dog.count) return { text: 'Split 50/50' }
  return { text: `${pct(p[top.key].count, n)}% ${top.abbr}`, mine: g.value.pick === top.key }
})
</script>

<template>
  <article :class="['tile', { nopick: !g.pick && !g.hidden, ro: readonly, live, final }, outcome && `is-${outcome}`, liveStatus && `live-${liveStatus}`]">
    <header class="t-meta">
      <span :class="['when', { on: live }]"><i v-if="live" class="ldot"></i>{{ when }}</span>
      <span v-if="!live && !final && now?.changed" :class="['moved', { flipped: now.flipped }]" :title="now.title">DK {{ now.text }}</span>
      <span v-else-if="!live && !final && started" class="moved">Started</span>
    </header>

    <button
      v-for="s in sides"
      :key="s.key"
      type="button"
      :class="['t-team', { picked: g.pick === s.key, other: g.pick && g.pick !== s.key, trailing: trailing(s.key) }]"
      :disabled="readonly"
      :aria-pressed="g.pick === s.key"
      :aria-label="`Pick ${s.team ? s.team.location + ' ' + s.team.name : g[s.key]} ${spreadText(s.key)}`"
      @click="choose(s.key)"
    >
      <img v-if="s.team?.logo && !broken[s.key]" :src="s.team.logo" alt="" class="t-logo" @error="broken[s.key] = true" />
      <span v-else class="t-logo fallback">{{ (g[s.key] || '?').slice(0, 2).toUpperCase() }}</span>
      <span class="t-name">{{ nameOf(s) }}</span>
      <span class="t-spread">{{ spreadText(s.key) }}</span>
      <span v-if="scoreFor(s.key) != null" class="t-score">{{ scoreFor(s.key) }}</span>
    </button>

    <button v-if="poolTop" type="button" class="t-pool" @click="poolOpen = true" title="See everyone's pick">
      <span class="lbl">Pool</span> <b :class="{ mine: poolTop.mine }">{{ poolTop.text }}</b><span class="go">›</span>
    </button>
    <PoolDialog
      v-if="poolOpen"
      :sides="poolSides"
      :pool="pool"
      :split="split"
      :status="live || final ? when : ''"
      :scores="{ fav: scoreFor('fav'), dog: scoreFor('dog') }"
      @close="poolOpen = false"
    />

    <footer class="t-foot">
      <span v-if="statusText" :class="['t-status', outcome || liveStatus]">{{ statusText }}</span>
      <span v-else-if="g.hidden" class="t-hint">🔒 Hidden until kickoff</span>
      <span v-else-if="!g.pick" class="t-hint">{{ readonly ? 'No pick' : 'Tap a team' }}</span>
      <span class="spacer"></span>
      <template v-if="g.pick">
        <div v-if="!readonly" class="t-step">
          <button aria-label="Decrease points" @click="bump(-1)">−</button>
          <input type="number" inputmode="numeric" min="2" max="50" v-model.number="g.points" @focus="$event.target.select()" aria-label="Points" />
          <button aria-label="Increase points" @click="bump(1)">+</button>
        </div>
        <span v-else :class="['t-pts', { loy: isLoy }]"><template v-if="isLoy">★ </template>{{ g.points }}</span>
      </template>
    </footer>
  </article>
</template>

<style scoped>
.tile {
  background: #fff; border-radius: 14px; padding: 10px 10px 8px; display: flex; flex-direction: column; gap: 3px;
  box-shadow: 0 1px 2px #0000000d, 0 2px 10px #0000000a; transition: opacity .15s, box-shadow .15s;
}
.tile.nopick.ro { opacity: .6; }
.tile.live { box-shadow: 0 0 0 2px #fca5a5; }
.tile.live.live-win { box-shadow: 0 0 0 2px #86efac; }
.tile.live.live-loss { box-shadow: 0 0 0 2px #fcd34d; }
.tile.final { box-shadow: inset 4px 0 0 #cbd5e1, 0 1px 2px #0000000d; padding-left: 14px; }
.tile.final.is-win { box-shadow: inset 4px 0 0 #22c55e, 0 1px 2px #0000000d; }
.tile.final.is-loss { box-shadow: inset 4px 0 0 #ef4444, 0 1px 2px #0000000d; }

.t-meta { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 0 4px 3px; min-height: 18px; }
.when { font-size: .7rem; font-weight: 700; color: #64748b; display: inline-flex; align-items: center; gap: 5px; font-variant-numeric: tabular-nums; }
.when.on { color: #b91c1c; }
.final .when { color: #0f172a; text-transform: uppercase; letter-spacing: .05em; font-size: .64rem; }
.moved { font-size: .64rem; font-weight: 800; padding: 1px 7px; border-radius: 999px; background: #fef3c7; color: #92400e; }
.moved.flipped { background: #fee2e2; color: #991b1b; }

.t-team {
  display: flex; align-items: center; gap: 8px; width: 100%; padding: 5px 6px; border: 0; border-radius: 9px;
  background: none; font: inherit; color: #0f172a; text-align: left; cursor: pointer; transition: background .12s, opacity .12s;
}
.t-team:not(:disabled):hover { background: #f1f5f9; }
.t-team:disabled { cursor: default; }
.t-team:focus-visible { outline: 2px solid #93c5fd; outline-offset: 0; }
.t-team.picked { background: #eff6ff; box-shadow: inset 3px 0 0 #2563eb; }
.is-win .t-team.picked, .live-win .t-team.picked { background: #f0fdf4; box-shadow: inset 3px 0 0 #22c55e; }
.is-loss .t-team.picked { background: #fef2f2; box-shadow: inset 3px 0 0 #ef4444; }
.live-loss .t-team.picked { background: #fefce8; box-shadow: inset 3px 0 0 #eab308; }
.t-team.other { opacity: .55; }
.t-logo { width: 24px; height: 24px; object-fit: contain; flex: none; }
.t-logo.fallback { display: grid; place-items: center; border-radius: 50%; background: #e2e8f0; color: #475569; font-size: .6rem; font-weight: 800; }
.t-name { flex: 1; min-width: 0; font-weight: 700; font-size: .9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.t-team.picked .t-name { font-weight: 800; }
.t-spread { font-size: .8rem; font-weight: 700; color: #64748b; font-variant-numeric: tabular-nums; }
.t-score { min-width: 26px; text-align: right; font-size: 1.05rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.t-team.trailing .t-score { color: #94a3b8; font-weight: 700; }

.t-pool { display: flex; align-items: center; gap: 6px; margin: 2px 0 0; padding: 4px 6px; border: 0; border-radius: 8px; background: #f8fafc; font: inherit; font-size: .72rem; color: #475569; cursor: pointer; text-align: left; }
.t-pool:hover { background: #eef2ff; }
.t-pool .lbl { font-size: .6rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: #94a3b8; }
.t-pool b { color: #0f172a; } .t-pool b.mine { color: #1d4ed8; }
.t-pool .go { margin-left: auto; color: #2563eb; font-weight: 800; }
.t-foot { display: flex; align-items: center; gap: 6px; min-height: 30px; padding: 4px 4px 0; margin-top: 2px; border-top: 1px solid #f1f5f9; }
.spacer { flex: 1; }
.t-hint { font-size: .72rem; color: #94a3b8; }
.t-status { font-size: .72rem; font-weight: 700; color: #475569; }
.t-status.win { color: #15803d; } .t-status.loss { color: #b91c1c; } .live-loss .t-status { color: #a16207; }
.t-pts { font-weight: 800; font-size: .82rem; padding: 2px 9px; border-radius: 999px; background: #f1f5f9; font-variant-numeric: tabular-nums; }
.t-pts.loy { background: #fef08a; color: #422006; }
.t-step { display: flex; align-items: center; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.t-step button { width: 24px; height: 26px; border: 0; background: #f8fafc; cursor: pointer; color: #0f172a; font-size: .95rem; line-height: 1; }
.t-step button:hover { background: #e2e8f0; }
.t-step input { width: 32px; height: 26px; border: 0; text-align: center; font-weight: 800; font-size: .85rem; -moz-appearance: textfield; }
.t-step input::-webkit-outer-spin-button, .t-step input::-webkit-inner-spin-button { appearance: none; margin: 0; }
.t-step input:focus { outline: 2px solid #93c5fd; outline-offset: -2px; }
</style>
