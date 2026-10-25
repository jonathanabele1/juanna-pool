<script setup>
import { computed, nextTick, onUnmounted, ref } from 'vue'
import TeamCard from './TeamCard.vue'
import TeamPeek from './TeamPeek.vue'
import PoolBar from './PoolBar.vue'
import PoolDialog from './PoolDialog.vue'
import { coverNow, resolveGame } from '../lines.js'
import { clampPoints, stepPoints, MIN_PTS, MAX_PTS } from '../points.js'
import { openOne, closeOpen } from '../dismiss.js'

const props = defineProps({
  game: Object, events: Array, now: Object, result: Object,
  teams: Object,      // your per-team stats by abbr (weeks before this one): ATS on the card, hold a team for more
  editing: Boolean,   // "fix names" inputs
  readonly: Boolean,  // view mode: nothing can be changed
  showDay: Boolean,   // flat (sorted) lists don't have day headings, so show the day on the card
  pool: Object,       // how the pool picked this game (revealed at kickoff)
  split: Object,      // DraftKings public betting
  otherPlayer: Boolean, // someone else's picks: the pool bar doesn't compare against them
  editable: Boolean,  // your saved week in view mode: show an Edit button on the card
})
defineEmits(['edit'])

const DAY_NAMES = { Thurs: 'Thu', Tues: 'Tue', Wed: 'Wed', Fri: 'Fri', Sat: 'Sat', Sun: 'Sun', Mon: 'Mon' }

const r = computed(() => resolveGame(props.game, props.events))
const g = computed(() => props.game)

// Away on the left, home on the right ("away @ home").
const sides = computed(() => {
  const fav = { role: 'fav', key: 'fav', team: r.value.favTeam, home: r.value.favHome }
  const dog = { role: 'dog', key: 'dog', team: r.value.dogTeam, home: !r.value.favHome }
  return fav.home ? [dog, fav] : [fav, dog]
})

const noLine = computed(() => g.value.source === 'schedule' && g.value.hasLine === false)
const dayText = computed(() => `${DAY_NAMES[g.value.day] || g.value.day}${g.value.time ? ` · ${g.value.time}` : ''}`)
const ev = computed(() => r.value.event)
const gameState = computed(() => ev.value?.state || props.result?.state)
const started = computed(() => !!props.now?.locked || gameState.value === 'in')
const live = computed(() => gameState.value === 'in')
const final = computed(() => gameState.value === 'post')
const info = computed(() => ev.value?.live || null)  // clock, quarter, down & distance

// scores straight from the scoreboard (freshest), else what the server scored
const evScore = key => {
  const team = key === 'fav' ? r.value.favTeam : r.value.dogTeam
  if (!ev.value || !team) return null
  return ev.value.scores?.[team === ev.value.home ? 'home' : 'away'] ?? null
}
const scoreFor = key => {
  if (!live.value && !final.value) return null
  return evScore(key) ?? props.result?.[key === 'fav' ? 'favScore' : 'dogScore'] ?? null
}
const leader = computed(() => {
  if (!final.value) return null
  const f = scoreFor('fav'), d = scoreFor('dog')
  return f == null || d == null || f === d ? null : f > d ? 'fav' : 'dog'
})

// your side against the sheet spread, right now
const cover = computed(() => (g.value.pick ? coverNow(g.value, props.events) : null))
const outcome = computed(() => {
  if (!final.value || !g.value.pick) return null
  const o = props.result?.outcome
  return ['win', 'loss', 'push'].includes(o) ? o : cover.value?.status || null
})
const liveStatus = computed(() => (live.value ? cover.value?.status || null : null))
const num = n => String(Math.abs(n)).replace(/^0\.5$/, '½').replace('.5', '½')
const earnedText = computed(() => {
  if (outcome.value === 'loss') return '0'
  return `+${num(props.result?.earned ?? (outcome.value === 'push' ? g.value.points / 2 : g.value.points))}`
})
const liveEarnedText = computed(() => {
  const st = cover.value?.status
  return st === 'loss' ? '0' : `+${num(st === 'push' ? g.value.points / 2 : g.value.points)}`
})
const coverText = computed(() => {
  const c = cover.value
  if (!c) return ''
  return c.status === 'push' ? 'On the number' : c.status === 'win' ? `Covering by ${num(c.margin)}` : `Short by ${num(c.margin)}`
})
const clockText = computed(() => {
  const l = info.value
  if (!l) return ev.value?.detail || ''
  if (l.halftime) return 'Halftime'
  if (l.endOfPeriod) return `End of ${l.quarter}`
  return [l.quarter, l.clock].filter(Boolean).join(' · ')
})
const finalText = computed(() => (/OT/.test(ev.value?.detail || '') ? 'Final · OT' : 'Final'))
const sideAbbr = key => (key === 'fav' ? r.value.favTeam : r.value.dogTeam)?.abbr
const pickedName = computed(() => (g.value.pick === 'fav' ? r.value.favTeam : r.value.dogTeam)?.name || g.value[g.value.pick])
// tap a team to pick it, tap it again to clear the pick
let lastChoice = null   // so a double-click (to see the team's stats) can undo its two taps
function choose(key) {
  lastChoice = { pick: g.value.pick, at: Date.now() }
  g.value.pick = g.value.pick === key ? null : key
}

// ---- press and hold (or double-click) a team: its season so far, under the card. Any tap closes it. ----
const PEEK_W = 264
const articleEl = ref(null)
const cardRefs = []   // the TeamCards, in sides order
const peek = ref(null)   // { key, left, top, arrow, above } (px, inside the card)
const closePeek = () => { peek.value = null }
async function openPeek(i, key, opts) {
  if (opts?.undo && lastChoice && Date.now() - lastChoice.at < 800) g.value.pick = lastChoice.pick
  lastChoice = null
  const box = articleEl.value.getBoundingClientRect(), c = cardRefs[i].$el.getBoundingClientRect()
  const w = Math.min(PEEK_W, box.width)
  const center = c.left + c.width / 2 - box.left
  const left = Math.max(0, Math.min(box.width - w, center - w / 2))
  peek.value = { key, left, arrow: center - left, top: c.bottom - box.top + 10, above: false }
  openOne(closePeek)
  await nextTick()
  // no room under the team (the edit bar docks at the bottom): open above it
  const h = articleEl.value?.querySelector('.tpeek')?.offsetHeight || 0
  const bar = document.querySelector('.totalbar')?.offsetHeight || 0
  if (peek.value && c.bottom + 10 + h > innerHeight - bar && c.top - 10 - h > 0) peek.value = { ...peek.value, above: true, top: c.top - box.top - 10 - h }
}
onUnmounted(() => closeOpen(closePeek))
const peekSide = computed(() => peek.value && sides.value.find(s => s.key === peek.value.key))

const pts = computed({
  get: () => g.value.points,
  set: v => (g.value.points = v),
})
function bump(d) { g.value.points = stepPoints(g.value.points, d) }
const isLoy = computed(() => Number(g.value.points) === 50)
function toggleLoy() { g.value.points = isLoy.value ? MIN_PTS : 50 }
// quick presets: tap to set, tap again to go back to the minimum
const PRESETS = [10, MAX_PTS]
function togglePreset(n) { g.value.points = Number(g.value.points) === n ? MIN_PTS : n }
const deltaText = d => (d > 0 ? `▲ +${d}` : `▼ ${d}`)

// ---- the pool + public betting on this game ----
const poolOpen = ref(false)
const spreadOf = key => (noLine.value ? '' : !g.value.spread ? 'PK' : key === 'fav' ? `−${g.value.spread}` : `+${g.value.spread}`)
const poolSides = computed(() => sides.value.map(s => ({
  key: s.key, abbr: s.team?.abbr || (g.value[s.key] || '').toUpperCase(), name: s.team?.name || g.value[s.key],
  logo: s.team?.logo, spread: spreadOf(s.key), color: s.team?.color, alternateColor: s.team?.alternateColor,
})))
const poolStatus = computed(() => (final.value ? finalText.value : live.value ? clockText.value : ''))
</script>

<template>
  <article ref="articleEl" :class="['game', { nopick: !g.pick && !g.hidden, ro: readonly, live, final }, outcome && `is-${outcome}`, liveStatus && `live-${liveStatus}`]">
    <header class="meta">
      <span v-if="showDay" class="pill day">{{ dayText }}</span>
      <span v-if="final" class="pill final">{{ finalText }}</span>
      <template v-else-if="live">
        <span class="pill live" :aria-label="`Live${clockText ? `, ${clockText}` : ''}`"><i class="pulse"></i>{{ clockText || 'Live' }}</span>
      </template>
      <span v-else-if="started" class="pill started">Started</span>
      <span v-else-if="g.pastDue && !g.pick" class="pill pastdue" title="Past the pick deadline. You can still change it.">Past due</span>

      <span class="spacer"></span>

      <span v-if="final && outcome" :class="['result', outcome]" :title="`${earnedText} of the ${g.points} you wagered`">
        <span class="r-label">{{ outcome === 'win' ? 'Covered' : outcome === 'loss' ? 'Missed' : 'Push' }}</span>
        <b class="r-pts">{{ earnedText }}</b>
        <span class="r-of">of {{ g.points }}</span>
      </span>
      <span v-else-if="live && cover" :class="['result', 'live', cover.status]" :title="`If it ended now: ${liveEarnedText} of the ${g.points} you wagered`">
        <span class="r-label">{{ coverText }}</span>
        <b class="r-pts">{{ liveEarnedText }}</b>
        <span class="r-of">of {{ g.points }}</span>
      </span>
      <span
        v-else-if="!live && !final && now?.changed"
        :class="['pill', 'now', { changed: now?.changed, flipped: now?.flipped }]"
        :title="now?.title"
      >
        DraftKings {{ now?.text }}
        <b v-if="now?.delta">{{ deltaText(now.delta) }}</b>
        <b v-else-if="now?.flipped">flipped</b>
      </span>
    </header>

    <div class="matchup">
      <TeamCard
        v-for="(s, i) in sides"
        :key="s.key"
        :raw="g[s.key]"
        :team="s.team"
        :role="s.role"
        :home="s.home"
        :spread="g.spread"
        :selected="g.pick === s.key"
        :dimmed="!!g.pick && g.pick !== s.key"
        :editing="editing"
        :readonly="readonly"
        :no-line="noLine"
        :ats="teams?.[s.team?.abbr]?.ats"
        :peekable="!!teams && !!s.team && !editing"
        :score="scoreFor(s.key)"
        :outcome="g.pick === s.key ? outcome : null"
        :live="g.pick === s.key ? liveStatus : null"
        :possession="live && !!info?.possession && info.possession === sideAbbr(s.key)"
        :trailing="!!leader && leader !== s.key"
        :points="g.pick === s.key ? g.points : null"
        :ref="el => (cardRefs[i] = el)"
        @select="choose(s.key)"
        @peek="openPeek(i, s.key, $event)"
        @update:raw="g[s.key] = $event"
        :style="{ gridColumn: i === 0 ? 1 : 3 }"
      />
      <span class="at">@</span>
    </div>
    <TeamPeek
      v-if="peekSide"
      :class="{ above: peek.above }"
      :style="{ left: peek.left + 'px', top: peek.top + 'px', '--arrow': peek.arrow + 'px' }"
      :team="peekSide.team"
      :raw="g[peekSide.key]"
      :role="peekSide.role"
      :stats="teams?.[peekSide.team?.abbr] || null"
    />

    <p v-if="live && (info?.down || info?.lastPlay)" class="situation">
      <span v-if="info.down" :class="['down', { rz: info.redZone }]">
        <b v-if="info.possession">{{ info.possession }} ball ·</b> {{ info.down }}<template v-if="info.spot"> at {{ info.spot }}</template>
        <em v-if="info.redZone">Red zone</em>
      </span>
      <span v-if="info.lastPlay" class="last" :title="info.lastPlay">{{ info.lastPlay }}</span>
    </p>

    <PoolBar
      v-if="pool || split"
      :sides="poolSides"
      :pool="pool"
      :split="split"
      :mine="otherPlayer ? null : g.pick"
      @details="poolOpen = true"
    />
    <PoolDialog
      v-if="poolOpen && pool?.revealed"
      :sides="poolSides"
      :pool="pool"
      :split="split"
      :status="poolStatus"
      :scores="{ fav: scoreFor('fav'), dog: scoreFor('dog') }"
      @close="poolOpen = false"
    />

    <footer v-if="!readonly" :class="['foot', { fixing: editing }]">
      <button v-if="editing" class="link" @click="g.favHome = !r.favHome">swap home/away</button>
      <button v-for="n in PRESETS" :key="n" class="loy max" :class="{ on: Number(g.points) === n }" :disabled="!g.pick" @click="togglePreset(n)" :aria-label="`Set to ${n} points`">{{ n }}</button>
      <button class="loy" :class="{ on: isLoy }" :disabled="!g.pick" @click="toggleLoy" title="Lock of the Year (50 points, once a season)">★ LOY</button>
      <span class="spacer"></span>
      <div :class="['stepper', { off: !g.pick }]" :title="g.pick ? '' : 'Pick a team first'">
        <button aria-label="Decrease points" :disabled="!g.pick || g.points <= MIN_PTS" @click="bump(-1)">−</button>
        <input type="number" inputmode="numeric" :min="MIN_PTS" :max="MAX_PTS" v-model.number="pts" :disabled="!g.pick" @focus="$event.target.select()" @change="pts = clampPoints(pts)" aria-label="Points" />
        <button aria-label="Increase points" :disabled="!g.pick || g.points >= MAX_PTS" @click="bump(1)">+</button>
      </div>
    </footer>

    <footer v-else class="foot ro">
      <span class="picked">
        <template v-if="g.hidden"><span aria-hidden="true">🔒</span> Pick hidden until kickoff</template>
        <template v-else-if="!g.pick">No pick</template>
        <template v-else>Picked <b>{{ pickedName }}</b><template v-if="g.points"> · {{ g.points }} pts</template></template>
      </span>
      <span class="spacer"></span>
      <button v-if="editable" type="button" class="edit-btn" :aria-label="`Edit picks (${g.fav} vs ${g.dog})`" @click="$emit('edit', $event.currentTarget.closest('article'))">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 2.5l2.5 2.5L6 12.5H3.5V10z"/></svg> {{ g.pick ? 'Edit' : 'Pick' }}
      </button>
    </footer>
  </article>
</template>

<style scoped>
/* read-only card: quick way back into edit mode, so you don't have to scroll to the top */
.edit-btn { display: inline-flex; align-items: center; gap: 4px; min-height: 30px; padding: 0 11px; border: 1px solid #dbeafe; border-radius: 999px; background: #fff; color: #2563eb; font-size: .78rem; font-weight: 700; cursor: pointer; transition: background .12s, border-color .12s; }
.edit-btn:hover { background: #eff6ff; border-color: #bfdbfe; }
.edit-btn:active { background: #dbeafe; }
.edit-btn:focus-visible { outline: 2px solid #93c5fd; outline-offset: 1px; }
.edit-btn svg { width: 12px; height: 12px; }
.pill.pastdue { background: #fef3c7; color: #92400e; }
.game { position: relative; background: #fff; border-radius: 18px; padding: 12px; box-shadow: 0 1px 2px #0000000d, 0 4px 14px #0000000a; transition: opacity .15s; }
.game.nopick.ro { opacity: .6; }
.stepper.off, .loy:disabled { opacity: .45; }
.stepper.off button, .loy:disabled { cursor: not-allowed; }

.meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; min-width: 0; }
.meta > * { flex: none; }
.meta > .spacer { flex: 1; }
.meta > .result { flex: 0 1 auto; min-width: 0; }
.spacer { flex: 1; }


.pill { display: inline-flex; align-items: center; height: 26px; padding: 0 10px; font-size: .72rem; font-weight: 700; border-radius: 999px; background: #f1f5f9; color: #475569; white-space: nowrap; }
.pill b { margin-left: 5px; }
.pill.day { background: #fff; box-shadow: inset 0 0 0 1px #e2e8f0; }
.pill.final { background: #0f172a; color: #fff; letter-spacing: .04em; text-transform: uppercase; }
.pill.live { background: #dc2626; color: #fff; gap: 6px; font-variant-numeric: tabular-nums; }
.pulse { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.7); } }
@media (prefers-reduced-motion: reduce) { .pulse { animation: none; } }

/* live: red ring; final: a left edge in the result's color */
.game.live { box-shadow: 0 0 0 2px #fca5a5, 0 4px 14px #dc26261a; }
.game.live.live-win { box-shadow: 0 0 0 2px #86efac, 0 4px 14px #16a34a1a; }
.game.live.live-loss { box-shadow: 0 0 0 2px #fcd34d, 0 4px 14px #d977061a; }
.game.final { box-shadow: inset 5px 0 0 #94a3b8, 0 1px 2px #0000000d; }
.game.final.is-win { box-shadow: inset 5px 0 0 #22c55e, 0 1px 2px #0000000d; }
.game.final.is-loss { box-shadow: inset 5px 0 0 #ef4444, 0 1px 2px #0000000d; }
.game.final { padding-left: 17px; }

.situation { display: flex; flex-direction: column; gap: 3px; margin: 10px 0 0; padding: 8px 12px; border-radius: 12px; background: #f8fafc; font-size: .8rem; color: #334155; }
.situation .down { font-weight: 600; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.situation .down em { font-style: normal; font-size: .64rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; padding: 2px 7px; border-radius: 999px; background: #fee2e2; color: #b91c1c; }
.situation .last { color: #64748b; font-size: .76rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* final: what you got back, out of what you wagered */
.result { display: inline-flex; align-items: center; gap: 8px; height: 34px; padding: 0 12px 0 11px; border-radius: 12px; white-space: nowrap; animation: res-in .35s cubic-bezier(.2, 1.4, .4, 1) both; }
.r-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: .64rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.r-pts { font-size: 1.35rem; font-weight: 900; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.r-of { font-size: .72rem; font-weight: 700; opacity: .75; font-variant-numeric: tabular-nums; }
.result.win { background: #16a34a; color: #fff; box-shadow: 0 2px 8px #16a34a40; }
.result.loss { background: #fef2f2; color: #b91c1c; box-shadow: inset 0 0 0 1.5px #fecaca; }
.result.push { background: #f1f5f9; color: #334155; box-shadow: inset 0 0 0 1.5px #e2e8f0; }
/* live: same shape, lighter, since it can still change */
.result.live { animation: none; }
.result.live.win { background: #dcfce7; color: #166534; box-shadow: inset 0 0 0 1.5px #86efac; }
.result.live.loss { background: #fef3c7; color: #92400e; box-shadow: inset 0 0 0 1.5px #fcd34d; }
.result.live.push { background: #f1f5f9; color: #334155; box-shadow: inset 0 0 0 1.5px #e2e8f0; }
@keyframes res-in { from { transform: scale(.85); opacity: 0; } to { transform: none; opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .result { animation: none; } }
.pill.started { background: #fee2e2; color: #991b1b; }
.pill.now.changed { background: #fef3c7; color: #92400e; box-shadow: 0 0 0 2px #fcd34d; }
.pill.now.flipped { background: #fee2e2; color: #991b1b; box-shadow: 0 0 0 2px #fca5a5; }

.matchup { display: grid; grid-template-columns: 1fr 28px 1fr; align-items: stretch; gap: 0; }
.matchup > :deep(.team):nth-child(1) { grid-column: 1; }
.at { grid-column: 2; grid-row: 1; align-self: center; text-align: center; font-weight: 800; color: #94a3b8; }

.foot { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.foot.fixing { flex-wrap: wrap; }
.foot > * { flex: none; }
.foot > .picked { flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.foot > .spacer { flex: 1; }
.foot.ro { margin-top: 8px; }
.picked { font-size: .85rem; color: #475569; }
.picked b { color: #0f172a; }
.link { background: none; border: 0; padding: 0; color: #2563eb; cursor: pointer; font: inherit; text-decoration: underline; }
.loy { height: 32px; border: 1px solid #e2e8f0; background: #fff; border-radius: 999px; padding: 0 10px; font-size: .75rem; font-weight: 700; color: #94a3b8; cursor: pointer; }
.loy.on { background: #facc15; border-color: #eab308; color: #422006; }
.loy.max { min-width: 40px; font-variant-numeric: tabular-nums; }
.loy.max.on { background: #0f172a; border-color: #0f172a; color: #fff; }
.stepper { display: flex; align-items: center; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
.stepper button { width: 40px; height: 40px; border: 0; background: #f8fafc; font-size: 1.2rem; cursor: pointer; color: #0f172a; }
.stepper button:hover:not(:disabled) { background: #e2e8f0; }
.stepper button:disabled { color: #cbd5e1; cursor: default; }
.stepper input { width: 52px; height: 40px; text-align: center; border: 0; font-size: 1.1rem; font-weight: 800; -moz-appearance: textfield; }
.stepper input::-webkit-outer-spin-button, .stepper input::-webkit-inner-spin-button { appearance: none; margin: 0; }
.stepper input:focus { outline: 2px solid #93c5fd; outline-offset: -2px; }

@media (max-width: 520px) {
  .result { gap: 6px; padding: 0 10px; }
  .stepper button { width: 36px; }
  .stepper input { width: 44px; }
  .matchup { grid-template-columns: 1fr; gap: 6px; }
  .matchup > :deep(.team) { grid-column: 1 !important; }
  .at { display: none; }
}
@media (max-width: 380px) {
  .meta .r-of { display: none; }
  .foot { gap: 6px; }
  .loy { padding: 0 8px; }
  .loy.max { min-width: 36px; }
}
</style>
