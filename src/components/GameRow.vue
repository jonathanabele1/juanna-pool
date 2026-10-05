<script setup>
import { computed } from 'vue'
import TeamCard from './TeamCard.vue'
import { coverNow, resolveGame } from '../lines.js'

const props = defineProps({
  game: Object, events: Array, now: Object, result: Object, ats: Object,
  editing: Boolean,   // "fix names" inputs
  readonly: Boolean,  // view mode: nothing can be changed
  showDay: Boolean,   // flat (sorted) lists don't have day headings, so show the day on the card
})

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
const num = n => String(Math.abs(n)).replace('.5', '½')
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
function choose(key) { g.value.pick = g.value.pick === key ? null : key }

const pts = computed({
  get: () => g.value.points,
  set: v => (g.value.points = v),
})
function bump(d) {
  const cur = Number(g.value.points) || 0
  g.value.points = Math.min(50, Math.max(0, cur + d))
}
const isLoy = computed(() => Number(g.value.points) === 50)
function toggleLoy() { g.value.points = isLoy.value ? 2 : 50 }
const deltaText = d => (d > 0 ? `▲ +${d}` : `▼ ${d}`)
</script>

<template>
  <article :class="['game', { nopick: !g.pick, ro: readonly, live, final }, outcome && `is-${outcome}`, liveStatus && `live-${liveStatus}`]">
    <header class="meta">
      <span v-if="showDay" class="pill day">{{ dayText }}</span>
      <span v-if="final" class="pill final">{{ finalText }}</span>
      <template v-else-if="live">
        <span class="pill live"><i class="pulse"></i>Live</span>
        <span v-if="clockText" class="pill clock">{{ clockText }}</span>
      </template>
      <span v-else-if="started" class="pill started">Started</span>
      <span v-else-if="g.pastDue && !g.pick" class="pill pastdue" title="Past the pick deadline. You can still change it.">Past due</span>

      <span class="spacer"></span>

      <span v-if="final && outcome" :class="['pill', 'res', outcome]">
        {{ outcome === 'win' ? 'Covered' : outcome === 'loss' ? 'Missed' : 'Push' }}
        <b>{{ outcome === 'win' ? `+${result?.earned ?? g.points}` : outcome === 'loss' ? `0 of ${g.points}` : `+${num(result?.earned ?? g.points / 2)}` }}</b>
      </span>
      <span v-else-if="live && cover" :class="['pill', 'cov', cover.status]" title="Your pick against the sheet spread, if it ended now">
        {{ coverText }}
        <b v-if="cover.status === 'win'">+{{ g.points }}</b>
        <b v-else-if="cover.status === 'push'">+{{ num(g.points / 2) }}</b>
      </span>
      <span
        v-else-if="!live && !final"
        :class="['pill', 'now', { changed: now?.changed, flipped: now?.flipped }]"
        :title="now?.title"
      >
        DK {{ now?.text }}
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
        :ats="ats?.[s.team?.abbr]"
        :score="scoreFor(s.key)"
        :outcome="g.pick === s.key ? outcome : null"
        :live="g.pick === s.key ? liveStatus : null"
        :possession="live && !!info?.possession && info.possession === sideAbbr(s.key)"
        :trailing="!!leader && leader !== s.key"
        @select="choose(s.key)"
        @update:raw="g[s.key] = $event"
        :style="{ gridColumn: i === 0 ? 1 : 3 }"
      />
      <span class="at">@</span>
    </div>

    <p v-if="live && (info?.down || info?.lastPlay)" class="situation">
      <span v-if="info.down" :class="['down', { rz: info.redZone }]">
        <b v-if="info.possession">{{ info.possession }} ball ·</b> {{ info.down }}<template v-if="info.spot"> at {{ info.spot }}</template>
        <em v-if="info.redZone">Red zone</em>
      </span>
      <span v-if="info.lastPlay" class="last" :title="info.lastPlay">{{ info.lastPlay }}</span>
    </p>

    <footer v-if="!readonly" class="foot">
      <span class="picked">
        <template v-if="g.pick">Picking <b>{{ pickedName }}</b></template>
        <template v-else>Tap a team to pick it</template>
        <small v-if="editing">
          · <button class="link" @click="g.favHome = !r.favHome">swap home/away</button>
        </small>
      </span>
      <span class="spacer"></span>
      <button class="loy" :class="{ on: isLoy }" :disabled="!g.pick" @click="toggleLoy" title="Lock of the Year (50 points, once a season)">★ LOY</button>
      <div :class="['stepper', { off: !g.pick }]" :title="g.pick ? '' : 'Pick a team first'">
        <button aria-label="Decrease points" :disabled="!g.pick" @click="bump(-1)">−</button>
        <input type="number" inputmode="numeric" min="2" max="50" v-model.number="pts" :disabled="!g.pick" @focus="$event.target.select()" aria-label="Points" />
        <button aria-label="Increase points" :disabled="!g.pick" @click="bump(1)">+</button>
      </div>
    </footer>

    <footer v-else class="foot ro">
      <span class="picked">
        <template v-if="!g.pick">No pick</template>
        <template v-else>Picked <b>{{ pickedName }}</b></template>
      </span>
      <span class="spacer"></span>
      <span v-if="g.pick" :class="['ptsbadge', { loy: isLoy }]">
        <template v-if="isLoy">★ Lock · </template>{{ g.points }} pts
      </span>
    </footer>
  </article>
</template>

<style scoped>
.pill.pastdue { background: #fef3c7; color: #92400e; }
.game { background: #fff; border-radius: 18px; padding: 12px; box-shadow: 0 1px 2px #0000000d, 0 4px 14px #0000000a; transition: opacity .15s; }
.game.nopick.ro { opacity: .6; }
.stepper.off, .loy:disabled { opacity: .45; }
.stepper.off button, .loy:disabled { cursor: not-allowed; }

.meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.spacer { flex: 1; }


.pill { display: inline-flex; align-items: center; height: 26px; padding: 0 10px; font-size: .72rem; font-weight: 700; border-radius: 999px; background: #f1f5f9; color: #475569; white-space: nowrap; }
.pill b { margin-left: 5px; }
.pill.day { background: #fff; box-shadow: inset 0 0 0 1px #e2e8f0; }
.pill.final { background: #0f172a; color: #fff; letter-spacing: .04em; text-transform: uppercase; }
.pill.live { background: #dc2626; color: #fff; letter-spacing: .06em; text-transform: uppercase; gap: 6px; }
.pill.clock { background: #fef2f2; color: #991b1b; font-variant-numeric: tabular-nums; }
.pill.cov.win { background: #dcfce7; color: #166534; }
.pill.cov.loss { background: #fef3c7; color: #92400e; }
.pill.cov.push { background: #e2e8f0; color: #334155; }
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
.pill.res.win { background: #dcfce7; color: #166534; }
.pill.res.loss { background: #fee2e2; color: #991b1b; }
.pill.res.push { background: #e2e8f0; color: #334155; }
.pill.started { background: #fee2e2; color: #991b1b; }
.pill.now.changed { background: #fef3c7; color: #92400e; box-shadow: 0 0 0 2px #fcd34d; }
.pill.now.flipped { background: #fee2e2; color: #991b1b; box-shadow: 0 0 0 2px #fca5a5; }

.matchup { display: grid; grid-template-columns: 1fr 28px 1fr; align-items: stretch; gap: 0; }
.matchup > :deep(.team):nth-child(1) { grid-column: 1; }
.at { grid-column: 2; grid-row: 1; align-self: center; text-align: center; font-weight: 800; color: #94a3b8; }

.foot { display: flex; align-items: center; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.foot.ro { margin-top: 8px; }
.picked { font-size: .85rem; color: #475569; }
.picked b { color: #0f172a; }
.ptsbadge { font-weight: 800; font-size: .95rem; padding: 4px 12px; border-radius: 999px; background: #f1f5f9; color: #0f172a; font-variant-numeric: tabular-nums; }
.ptsbadge.loy { background: #fef08a; color: #422006; }
.link { background: none; border: 0; padding: 0; color: #2563eb; cursor: pointer; font: inherit; text-decoration: underline; }
.loy { border: 1px solid #e2e8f0; background: #fff; border-radius: 999px; padding: 5px 10px; font-size: .75rem; font-weight: 700; color: #94a3b8; cursor: pointer; }
.loy.on { background: #facc15; border-color: #eab308; color: #422006; }
.stepper { display: flex; align-items: center; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
.stepper button { width: 40px; height: 40px; border: 0; background: #f8fafc; font-size: 1.2rem; cursor: pointer; color: #0f172a; }
.stepper button:hover { background: #e2e8f0; }
.stepper input { width: 52px; height: 40px; text-align: center; border: 0; font-size: 1.1rem; font-weight: 800; -moz-appearance: textfield; }
.stepper input::-webkit-outer-spin-button, .stepper input::-webkit-inner-spin-button { appearance: none; margin: 0; }
.stepper input:focus { outline: 2px solid #93c5fd; outline-offset: -2px; }

@media (max-width: 520px) {
  .matchup { grid-template-columns: 1fr; gap: 6px; }
  .matchup > :deep(.team) { grid-column: 1 !important; }
  .at { display: none; }
}
</style>
