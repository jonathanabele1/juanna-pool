<script setup>
// Read-only NFL schedule for a week whose lines aren't posted yet, grouped by game day (ET).
import { computed } from 'vue'

const props = defineProps({ events: Array })

const ET = 'America/New_York'
const dayKey = iso => new Date(iso).toLocaleDateString('en-US', { timeZone: ET, weekday: 'long', month: 'short', day: 'numeric' })
const timeOf = iso => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

const days = computed(() => {
  const out = []
  for (const ev of [...props.events].sort((a, b) => a.kickoff.localeCompare(b.kickoff))) {
    const key = dayKey(ev.kickoff)
    let d = out.find(x => x.key === key)
    if (!d) out.push((d = { key, games: [] }))
    d.games.push(ev)
  }
  return out
})
const final = ev => ev.state === 'post' && ev.scores?.home != null
const scored = ev => ['in', 'post'].includes(ev.state) && ev.scores?.home != null
const clock = ev => {
  const l = ev.live
  if (!l) return 'Live'
  if (l.halftime) return 'Half'
  if (l.endOfPeriod) return `End ${l.quarter}`
  return [l.quarter, l.clock].filter(Boolean).join(' ')
}
const trailing = (ev, side) => final(ev) && ev.scores[side] < ev.scores[side === 'home' ? 'away' : 'home']
</script>

<template>
  <section v-for="d in days" :key="d.key" class="group">
    <h2>{{ d.key }}</h2>
    <div class="sched">
      <div v-for="ev in d.games" :key="ev.id" class="row">
        <div class="team">
          <img v-if="ev.away.logo" :src="ev.away.logo" alt="" />
          <span><b>{{ ev.away.name }}</b><small>{{ ev.away.record || ev.away.location }}</small></span>
          <span v-if="scored(ev)" :class="['score', { trailing: trailing(ev, 'away') }]">{{ ev.scores.away }}<i v-if="ev.live?.possession === ev.away.abbr" class="ball">🏈</i></span>
        </div>
        <span class="at">@</span>
        <div class="team home">
          <span v-if="scored(ev)" :class="['score', { trailing: trailing(ev, 'home') }]"><i v-if="ev.live?.possession === ev.home.abbr" class="ball">🏈</i>{{ ev.scores.home }}</span>
          <span><b>{{ ev.home.name }}</b><small>{{ ev.home.record || ev.home.location }}</small></span>
          <img v-if="ev.home.logo" :src="ev.home.logo" alt="" />
        </div>
        <span v-if="final(ev)" class="when final">Final</span>
        <span v-else-if="ev.state === 'in'" class="when live"><i></i>{{ clock(ev) }}</span>
        <span v-else class="when">{{ timeOf(ev.kickoff) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sched { background: #fff; border-radius: 16px; box-shadow: 0 1px 2px #0000000d; overflow: hidden; }
.row { display: grid; grid-template-columns: 1fr auto 1fr 72px; align-items: center; gap: 10px; padding: 10px 14px; border-top: 1px solid #f1f5f9; }
.row:first-child { border-top: 0; }
.team { display: flex; align-items: center; gap: 10px; min-width: 0; }
.team.home { justify-content: flex-end; text-align: right; }
.team img { width: 30px; height: 30px; object-fit: contain; flex: none; }
.team span { display: flex; flex-direction: column; min-width: 0; }
.team b { font-size: .92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.team small { color: #94a3b8; font-size: .72rem; }
.team .score { font-weight: 800; font-size: 1.05rem; color: #0f172a; flex-direction: row; align-items: center; gap: 4px; font-variant-numeric: tabular-nums; }
.team .score.trailing { color: #94a3b8; }
.ball { font-style: normal; font-size: .7rem; }
.when.final { justify-self: end; font-weight: 800; font-size: .66rem; letter-spacing: .06em; text-transform: uppercase; color: #fff; background: #0f172a; padding: 3px 8px; border-radius: 999px; }
.when.live { display: inline-flex; align-items: center; justify-content: flex-end; gap: 5px; color: #b91c1c; font-weight: 800; font-variant-numeric: tabular-nums; }
.when.live i { width: 7px; height: 7px; border-radius: 50%; background: #dc2626; animation: blink 1.4s ease-in-out infinite; }
@keyframes blink { 50% { opacity: .35; } }
.at { color: #cbd5e1; font-weight: 700; }
.when { text-align: right; font-size: .78rem; font-weight: 600; color: #64748b; }
@media (max-width: 480px) {
  .row { grid-template-columns: 1fr auto 1fr; }
  .when { grid-column: 1 / -1; text-align: center; margin-top: -4px; justify-self: center; }
  .team img { width: 24px; height: 24px; }
}
</style>
