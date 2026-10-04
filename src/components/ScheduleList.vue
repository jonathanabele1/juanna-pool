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
</script>

<template>
  <section v-for="d in days" :key="d.key" class="group">
    <h2>{{ d.key }}</h2>
    <div class="sched">
      <div v-for="ev in d.games" :key="ev.id" class="row">
        <div class="team">
          <img v-if="ev.away.logo" :src="ev.away.logo" alt="" />
          <span><b>{{ ev.away.name }}</b><small>{{ ev.away.record || ev.away.location }}</small></span>
          <span v-if="final(ev)" class="score">{{ ev.scores.away }}</span>
        </div>
        <span class="at">@</span>
        <div class="team home">
          <span v-if="final(ev)" class="score">{{ ev.scores.home }}</span>
          <span><b>{{ ev.home.name }}</b><small>{{ ev.home.record || ev.home.location }}</small></span>
          <img v-if="ev.home.logo" :src="ev.home.logo" alt="" />
        </div>
        <span class="when">{{ final(ev) ? 'Final' : ev.state === 'in' ? 'Live' : timeOf(ev.kickoff) }}</span>
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
.team .score { font-weight: 800; font-size: 1.05rem; color: #0f172a; }
.at { color: #cbd5e1; font-weight: 700; }
.when { text-align: right; font-size: .78rem; font-weight: 600; color: #64748b; }
@media (max-width: 480px) {
  .row { grid-template-columns: 1fr auto 1fr; }
  .when { grid-column: 1 / -1; text-align: center; margin-top: -4px; }
  .team img { width: 24px; height: 24px; }
}
</style>
