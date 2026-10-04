<script setup>
import { computed, onMounted, ref } from 'vue'
import { getStats } from './api.js'
import TeamStats from './components/TeamStats.vue'

const s = ref(null)
const error = ref('')
onMounted(async () => {
  try { s.value = await getStats() } catch (e) { error.value = e.message }
})

const fmt = n => (n == null ? '—' : n)
const sign = n => (n > 0 ? `+${n}` : n)

// weekly bar chart geometry
const chart = computed(() => {
  const rows = s.value?.byWeek || []
  if (!rows.length) return null
  const H = 170, pad = 24, bw = 34, gap = 10
  const max = Math.max(...rows.map(r => r.score), 1)
  const min = Math.min(...rows.map(r => r.score), 0)
  const y = v => pad + ((max - v) / (max - min || 1)) * (H - pad * 2)
  return {
    W: rows.length * (bw + gap) + gap, H, zero: y(0), avg: s.value.average == null ? null : y(s.value.average),
    bars: rows.map((r, i) => {
      const x = gap + i * (bw + gap)
      return { ...r, x, w: bw, y: Math.min(y(r.score), y(0)), h: Math.max(2, Math.abs(y(r.score) - y(0))) }
    }),
  }
})
const cumulative = computed(() => {
  let t = 0
  return (s.value?.byWeek || []).map(r => (t += r.score))
})
</script>

<template>
  <p v-if="error" class="err">Couldn’t load stats: {{ error }}</p>
  <p v-else-if="!s" class="loading">Crunching your season…</p>
  <p v-else-if="!s.weeksPlayed" class="empty">
    No scored weeks yet. Save your picks for a week whose games have finished and your stats will show up here.
  </p>

  <div v-else class="stats">
    <section class="hero">
      <div><span class="k">Season total</span><span class="v">{{ s.total }}</span></div>
      <div><span class="k">Weekly average</span><span class="v">{{ s.average }}</span></div>
      <div><span class="k">Record vs spread</span><span class="v">{{ s.record.wins }}–{{ s.record.losses }}<template v-if="s.record.pushes">–{{ s.record.pushes }}</template></span><small>{{ fmt(s.record.pct) }}% covers</small></div>
      <div><span class="k">Weeks played</span><span class="v">{{ s.weeksPlayed }}</span></div>
    </section>

    <section class="card">
      <h3>Score by week</h3>
      <div class="chartwrap">
        <svg :viewBox="`0 0 ${chart.W} ${chart.H}`" :width="chart.W" :height="chart.H" role="img" aria-label="Score by week">
          <line :x1="0" :x2="chart.W" :y1="chart.zero" :y2="chart.zero" stroke="#cbd5e1" />
          <line v-if="chart.avg != null" :x1="0" :x2="chart.W" :y1="chart.avg" :y2="chart.avg" stroke="#2563eb" stroke-dasharray="4 4" />
          <g v-for="b in chart.bars" :key="b.week">
            <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="5" :fill="b.score < 0 ? '#ef4444' : b.complete ? '#16a34a' : '#86efac'" />
            <text :x="b.x + b.w / 2" :y="b.score < 0 ? b.y + b.h + 12 : b.y - 5" text-anchor="middle" class="bv">{{ b.score }}</text>
            <text :x="b.x + b.w / 2" :y="chart.H - 4" text-anchor="middle" class="bl">W{{ b.week }}</text>
          </g>
        </svg>
      </div>
      <p class="note">Dashed line = your weekly average. Lighter bars are weeks still in progress.</p>
    </section>

    <div class="grid">
      <section class="card">
        <h3>Highlights</h3>
        <ul class="kv">
          <li><span>Best week</span><b>Week {{ s.best.week }} · {{ s.best.score }}</b></li>
          <li><span>Worst week</span><b>Week {{ s.worst.week }} · {{ s.worst.score }}</b></li>
          <li><span>Points earned</span><b>{{ s.pointsEarned }} <small>of {{ s.pointsWagered }} wagered</small></b></li>
          <li v-if="s.pointsWagered"><span>Confidence efficiency</span><b>{{ Math.round(100 * s.pointsEarned / s.pointsWagered) }}%</b></li>
          <li v-if="s.penalties || s.adjustments"><span>Penalties / adjustments</span><b class="neg">−{{ s.penalties }} / {{ sign(s.adjustments) }}</b></li>
          <li v-if="s.bestHit"><span>Biggest hit</span><b>{{ s.bestHit.team }} · {{ s.bestHit.points }} (wk {{ s.bestHit.week }})</b></li>
          <li v-if="s.worstMiss"><span>Costliest miss</span><b>{{ s.worstMiss.team }} · {{ s.worstMiss.points }} (wk {{ s.worstMiss.week }})</b></li>
          <li v-if="s.loy"><span>Lock of the Year</span><b>{{ s.loy.pick }} · wk {{ s.loy.week }} · {{ s.loy.outcome === 'win' ? '✓ hit' : s.loy.outcome === 'loss' ? '✗ missed' : 'push' }}</b></li>
          <li v-else><span>Lock of the Year</span><b>not used yet</b></li>
        </ul>
      </section>

      <section class="card">
        <h3>Cover rate by confidence</h3>
        <div v-for="t in s.byTier" :key="t.tier" class="bar">
          <span class="bl2">{{ t.tier }}</span>
          <span class="track2"><span class="fill2" :style="{ width: (t.pct || 0) + '%' }"></span></span>
          <span class="bv2">{{ t.picks ? `${t.pct}% (${t.wins}/${t.picks})` : '—' }}</span>
        </div>
        <p class="note">Are your high-confidence picks actually your best ones?</p>
      </section>

      <section class="card">
        <h3>Pick tendencies</h3>
        <div v-for="[name, r] in [['Favorites', s.favorites], ['Underdogs', s.underdogs], ['Home teams', s.homePicks], ['Away teams', s.awayPicks]]" :key="name" class="bar">
          <span class="bl2">{{ name }}</span>
          <span class="track2"><span class="fill2 alt" :style="{ width: (r.pct || 0) + '%' }"></span></span>
          <span class="bv2">{{ r.picks ? `${r.pct}% (${r.wins}/${r.picks})` : '—' }}</span>
        </div>
        <p class="note">Cover rate when you pick each type.</p>
      </section>

      <section class="card">
        <h3>Running total</h3>
        <ul class="kv">
          <li v-for="(r, i) in s.byWeek" :key="r.week">
            <span>Week {{ r.week }} <small>{{ r.wins }}–{{ r.losses }}<template v-if="r.pushes">–{{ r.pushes }}</template></small></span>
            <b>{{ cumulative[i] }} <small :class="{ neg: r.score < 0 }">({{ sign(r.score) }})</small></b>
          </li>
        </ul>
      </section>
    </div>

    <TeamStats v-if="s.teams?.length" :teams="s.teams" />
  </div>
</template>

<style scoped>
.stats { display: flex; flex-direction: column; gap: 14px; }
.hero { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.hero > div { background: #0f172a; color: #fff; border-radius: 16px; padding: 14px 16px; display: flex; flex-direction: column; gap: 2px; }
.hero .k { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: #94a3b8; }
.hero .v { font-size: 2rem; font-weight: 800; letter-spacing: -.02em; }
.hero small { color: #94a3b8; }
.card { background: #fff; border-radius: 16px; padding: 14px 16px; box-shadow: 0 1px 2px #0000000d; }
.card h3 { margin: 0 0 10px; font-size: .95rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.chartwrap { overflow-x: auto; }
.bv { font-size: 11px; font-weight: 700; fill: #334155; }
.bl { font-size: 10px; fill: #94a3b8; }
.note { font-size: .75rem; color: #94a3b8; margin: 8px 0 0; }
.kv { list-style: none; margin: 0; padding: 0; }
.kv li { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-top: 1px solid #f1f5f9; font-size: .88rem; }
.kv li:first-child { border-top: 0; }
.kv span { color: #64748b; }
.kv small { color: #94a3b8; font-weight: 500; }
.neg { color: #b91c1c !important; }
.bar { display: grid; grid-template-columns: 90px 1fr 110px; align-items: center; gap: 8px; margin: 7px 0; font-size: .82rem; }
.bl2 { color: #475569; font-weight: 600; }
.track2 { height: 10px; background: #f1f5f9; border-radius: 99px; overflow: hidden; }
.fill2 { display: block; height: 100%; background: #16a34a; border-radius: 99px; }
.fill2.alt { background: #2563eb; }
.bv2 { text-align: right; color: #334155; font-variant-numeric: tabular-nums; }
.loading, .empty { color: #64748b; text-align: center; padding: 40px 10px; }
.err { color: #b91c1c; }
</style>
