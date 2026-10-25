<script setup>
// The whole pool: this week's leaderboard (live while games are on) and the season table. Tap a player to see their picks.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getWeekStandings, getSeasonStandings } from './api.js'

const props = defineProps({ currentWeek: Number })
const emit = defineEmits(['open'])

const saved = (k, d) => { try { return localStorage.getItem(k) ?? d } catch { return d } }
const mode = ref(saved('standingsMode', 'week'))
watch(mode, v => { try { localStorage.setItem('standingsMode', v) } catch {} })
const week = ref(props.currentWeek || 1)
watch(() => props.currentWeek, w => { if (w && !data.value) week.value = w })

const data = ref(null)      // this week's standings
const season = ref(null)
const error = ref('')
const loading = ref(false)
let timer
const LIVE_POLL = 30 * 1000

async function load(quiet = false) {
  clearTimeout(timer)
  if (!quiet) loading.value = true
  try {
    if (mode.value === 'week') {
      const n = week.value
      const d = await getWeekStandings(n)
      if (n === week.value) data.value = d
    } else {
      season.value = await getSeasonStandings()
    }
    error.value = ''
  } catch (e) {
    if (!quiet) error.value = e.message
  } finally {
    loading.value = false
  }
  // keep it live while games are on (the season table moves with the live week too)
  if (live.value) timer = setTimeout(() => load(true), LIVE_POLL)
}
const onVisible = () => { if (document.visibilityState === 'visible') load(true) }
onMounted(() => { load(); document.addEventListener('visibilitychange', onVisible) })
onUnmounted(() => { clearTimeout(timer); document.removeEventListener('visibilitychange', onVisible) })
watch([mode, week], () => { if (mode.value === 'week') data.value = null; load() })

const live = computed(() => (mode.value === 'week'
  ? (data.value?.games.live || 0) > 0
  : (season.value?.rows || []).some(r => r.projected !== r.total)))
const g = computed(() => data.value?.games || { total: 0, live: 0, final: 0 })
const started = computed(() => g.value.live + g.value.final > 0)
const weekOver = computed(() => g.value.total > 0 && g.value.final === g.value.total)
const isLive = computed(() => g.value.live > 0)
const rows = computed(() => data.value?.rows || [])

// Week columns: Score always; Live while games are on; Max and Live max while games are left to play
// (Live max: games on now end as they stand, every game not started covers). Tap a header to sort by it,
// tap it again to flip. Default: Live while games are on, otherwise Score.
const COLS = { score: 'Score', projected: 'Live', max: 'Max', liveMax: 'Live max' }
const anyPending = computed(() => rows.value.some(r => r.pending))
const cols = computed(() => ['score', isLive.value && 'projected', anyPending.value && 'max', isLive.value && anyPending.value && 'liveMax'].filter(Boolean))
const sortKey = ref(null)
const sortDir = ref(-1)
const key = computed(() => (cols.value.includes(sortKey.value) ? sortKey.value : isLive.value ? 'projected' : 'score'))
function sortBy(k) {
  if (key.value === k) sortDir.value *= -1
  else { sortKey.value = k; sortDir.value = -1 }
}
const sorted = computed(() => {
  const k = key.value, other = k === 'score' ? 'projected' : 'score'
  const v = (r, c) => r[c] ?? -Infinity
  return [...rows.value].sort((a, b) => sortDir.value * (v(a, k) - v(b, k) || v(a, other) - v(b, other)) || a.name.localeCompare(b.name))
})
const rankOf = r => (key.value === 'projected' ? r.projectedRank : key.value === 'score' ? r.rank
  : 1 + rows.value.filter(x => (x[key.value] ?? -Infinity) > (r[key.value] ?? -Infinity)).length)
const ariaSort = c => (key.value === c ? (sortDir.value < 0 ? 'descending' : 'ascending') : 'none')

const rec = r => `${r.wins}–${r.losses}${r.pushes ? `–${r.pushes}` : ''}`
const liveRec = r => (r.live.wins + r.live.losses + r.live.pushes ? `${r.live.wins}–${r.live.losses}${r.live.pushes ? `–${r.live.pushes}` : ''}` : '')
const move = r => r.rank - r.projectedRank   // places gained if the live games ended now
const ord = n => `${n}${['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) ? 0 : n % 10] || 'th'}`
</script>

<template>
  <div class="standings">
    <section class="head">
      <div class="seg" role="tablist" aria-label="Standings view">
        <button role="tab" :aria-selected="mode === 'week'" :class="{ on: mode === 'week' }" @click="mode = 'week'">Week</button>
        <button role="tab" :aria-selected="mode === 'season'" :class="{ on: mode === 'season' }" @click="mode = 'season'">Season</button>
      </div>
      <div v-if="mode === 'week'" class="stepper" aria-label="Choose week">
        <button :disabled="week <= 1" aria-label="Previous week" @click="week--">‹</button>
        <span>Week {{ week }}<i v-if="isLive" class="ldot" :title="`${g.live} live · ${g.final} of ${g.total} final`"></i><small v-else-if="week === currentWeek">now</small></span>
        <button :disabled="week >= 18" aria-label="Next week" @click="week++">›</button>
      </div>

    </section>

    <p v-if="error" class="err">Couldn’t load the league: {{ error }}</p>

    <!-- ================= WEEK ================= -->
    <template v-else-if="mode === 'week'">
      <p v-if="!data" class="loading">Loading week {{ week }}…</p>
      <template v-else>
        <p v-if="!data.posted" class="empty">Week {{ week }}’s lines aren’t posted yet.</p>
        <section v-else-if="!started" class="card prestart">
          <h3>No games have kicked off yet</h3>
          <ul class="inlist">
            <li v-for="r in rows" :key="r.id" :class="{ me: r.me }" @click="emit('open', r.id)"><span class="ok">✓</span>{{ r.name }}</li>
            <li v-for="n in data.noPicks" :key="n" class="missing"><span>·</span>{{ n }} <small>no picks yet</small></li>
          </ul>
        </section>

        <section v-else class="table" role="table" aria-label="Week standings" :style="{ '--cols': cols.length }">
          <div class="tr th" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">Player</span>
            <button v-for="c in cols" :key="c" type="button" role="columnheader" :aria-sort="ariaSort(c)"
                    :class="['num', 'sort', { on: key === c }]" @click="sortBy(c)">
              {{ COLS[c] }}<i class="arr" :class="{ up: key === c && sortDir > 0 }"></i>
            </button>
          </div>
          <button
            v-for="r in sorted" :key="r.id" type="button" role="row"
            :class="['tr', { me: r.me, first: rankOf(r) === 1 }]"
            @click="emit('open', r.id)"
          >
            <span class="rank">
              {{ rankOf(r) }}
              <template v-if="key === 'projected'">
                <i v-if="move(r) > 0" class="mv up" :title="`Up ${move(r)} from ${ord(r.rank)}`">▲{{ move(r) }}</i>
                <i v-else-if="move(r) < 0" class="mv down" :title="`Down ${-move(r)} from ${ord(r.rank)}`">▼{{ -move(r) }}</i>
              </template>
            </span>
            <span class="who">
              <b>{{ r.name }}<span v-if="weekOver && r.rank === 1" class="crown" title="Week winner">👑</span></b>
              <small>
                {{ rec(r) }}
                <template v-if="liveRec(r)"> · <span class="lv">{{ liveRec(r) }} live</span></template>
                <template v-if="r.penalties"> · <span class="neg">−{{ r.penalties }}</span></template>
              </small>
            </span>
            <span v-for="c in cols" :key="c" :class="['num', 'val', { on: key === c, neg: r[c] < 0 }]">{{ r[c] ?? '—' }}</span>
          </button>
          <p v-if="data.noPicks.length" class="nopicks">No picks: {{ data.noPicks.join(', ') }}</p>
        </section>
      </template>
    </template>

    <!-- ================= SEASON ================= -->
    <template v-else>
      <p v-if="!season" class="loading">Adding up the season…</p>
      <p v-else-if="!season.rows.length" class="empty">No scored weeks yet.</p>
      <section v-else class="table season" role="table" aria-label="Season standings">
        <div class="tr th" role="row">
          <span role="columnheader">#</span>
          <span role="columnheader">Player</span>
          <span role="columnheader" class="num">Total</span>
          <span role="columnheader" class="num avg">Avg</span>
          <span role="columnheader" class="num wins" title="Weeks won (finished weeks)">Wins</span>
        </div>
        <button v-for="r in season.rows" :key="r.id" type="button" role="row" :class="['tr', { me: r.me, first: r.rank === 1 }]" @click="emit('open', r.id)">
          <span class="rank">{{ r.rank }}</span>
          <span class="who">
            <b>{{ r.name }}</b>
            <small>
              {{ r.record.wins }}–{{ r.record.losses }}<template v-if="r.record.pushes">–{{ r.record.pushes }}</template>
              <template v-if="r.record.pct != null"> · {{ r.record.pct }}%</template>
              · {{ r.weeksPlayed }} wk{{ r.weeksPlayed === 1 ? '' : 's' }}
              <span class="mobile-only"> · avg {{ r.average }}</span>
            </small>
          </span>
          <span class="num score">
            <b :class="{ neg: r.total < 0 }">{{ r.total }}</b>
            <small v-if="r.projected !== r.total" :class="['lv', r.projected > r.total ? 'pos' : 'neg']" title="If the games on now ended as they stand"><i class="ldot"></i>{{ r.projected }}</small>
          </span>
          <span class="num avg">{{ r.average }}</span>
          <span class="num wins">{{ r.weeklyWins || '—' }}</span>
        </button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.standings { display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.seg { display: inline-flex; background: #e2e8f0; border-radius: 12px; padding: 3px; }
.seg button { border: 0; background: none; padding: 7px 16px; border-radius: 9px; font-weight: 700; color: #475569; cursor: pointer; }
.seg button.on { background: #fff; color: #0f172a; box-shadow: 0 1px 3px #0002; }
.stepper { display: inline-flex; align-items: center; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
.stepper button { width: 38px; height: 38px; border: 0; background: none; font-size: 1.3rem; cursor: pointer; color: #0f172a; }
.stepper button:hover:not(:disabled) { background: #f1f5f9; }
.stepper button:disabled { color: #cbd5e1; cursor: default; }
.stepper span { min-width: 84px; text-align: center; font-weight: 800; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.stepper small { font-size: .6rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #2563eb; }

/* table: # | player | one column per number (Score, Live, Max, Live max) */
.table { background: #fff; border-radius: 18px; box-shadow: 0 1px 2px #0000000d, 0 4px 14px #0000000a; overflow: hidden; }
.tr {
  display: grid; grid-template-columns: 40px minmax(0, 1fr) repeat(var(--cols, 1), 62px); align-items: center; gap: 0 4px;
  width: 100%; min-height: 56px; padding: 8px 14px 8px 12px; border: 0; border-top: 1px solid #f1f5f9; background: #fff; font: inherit; color: inherit; text-align: left;
}
.season .tr { grid-template-columns: 40px minmax(0, 1fr) 76px 56px 56px; }
.th { min-height: 0; border-top: 0; background: #f8fafc; padding-top: 8px; padding-bottom: 8px; font-size: .62rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #94a3b8; }
.th .sort {
  align-self: stretch; border: 0; background: none; padding: 4px 0; margin: -4px 0; font: inherit; color: inherit; text-transform: inherit; letter-spacing: inherit;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: flex-end; gap: 3px; line-height: 1.15; text-align: right;
}
.th .sort:hover { color: #475569; }
.th .sort.on { color: #2563eb; }
.th .sort:focus-visible { outline: 2px solid #93c5fd; border-radius: 4px; }
.arr { width: 0; height: 0; border-left: 3.5px solid transparent; border-right: 3.5px solid transparent; border-top: 4px solid currentColor; opacity: 0; flex: none; }
.sort.on .arr { opacity: 1; }
.arr.up { transform: rotate(180deg); }
button.tr { cursor: pointer; transition: background .12s; }
button.tr:hover { background: #f8fafc; }
button.tr:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }
.tr.me { background: #eff6ff; box-shadow: inset 3px 0 0 #2563eb; }
.tr.me:hover { background: #e0ecff; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.rank { font-weight: 800; font-size: 1rem; color: #64748b; display: flex; flex-direction: column; align-items: flex-start; line-height: 1.05; font-variant-numeric: tabular-nums; }
.first .rank { color: #b45309; }
.mv { font-style: normal; font-size: .6rem; font-weight: 800; }
.mv.up { color: #15803d; } .mv.down { color: #b91c1c; }
.who { display: flex; flex-direction: column; min-width: 0; gap: 2px; }
.who b { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who small { font-size: .72rem; color: #94a3b8; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.crown { margin-left: 5px; }
.lv { color: #b91c1c; font-weight: 700; }
.val { font-size: 1rem; font-weight: 700; color: #94a3b8; }
.val.on { font-size: 1.12rem; font-weight: 800; color: #0f172a; }
.val.neg { color: #f87171; } .val.on.neg { color: #b91c1c; }
.score { font-weight: 800; font-size: 1.1rem; color: #0f172a; }
.season .score { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.15; }
.season .score small { font-size: .7rem; display: inline-flex; align-items: center; gap: 4px; }
.avg, .wins { color: #475569; font-weight: 700; }
.pos { color: #15803d; }
.neg { color: #b91c1c; }
.season .score b.neg { color: #b91c1c; }
.mobile-only { display: none; }
.nopicks { margin: 0; padding: 10px 14px; border-top: 1px solid #f1f5f9; font-size: .76rem; color: #94a3b8; }

.card { background: #fff; border-radius: 18px; padding: 16px 18px; box-shadow: 0 1px 2px #0000000d; }
.card h3 { margin: 0; font-size: 1rem; }
.inlist { list-style: none; padding: 0; margin: 12px 0 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; }
.inlist li { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 10px; background: #f8fafc; font-weight: 600; font-size: .88rem; cursor: pointer; }
.inlist li.me { background: #eff6ff; }
.inlist li.missing { color: #94a3b8; cursor: default; font-weight: 500; }
.inlist small { font-size: .7rem; }
.ok { color: #16a34a; font-weight: 800; }
.loading, .empty { color: #64748b; text-align: center; padding: 34px 10px; }
.err { color: #b91c1c; }

@media (max-width: 520px) {
  .tr { grid-template-columns: 26px minmax(0, 1fr) repeat(var(--cols, 1), 46px); padding: 8px 10px; gap: 0 3px; min-height: 52px; }
  .season .tr { grid-template-columns: 26px minmax(0, 1fr) 64px 48px; }
  .season .avg { display: none; }
  .mobile-only { display: inline; }
  .th { font-size: .56rem; letter-spacing: .03em; }
  .val { font-size: .92rem; } .val.on { font-size: 1rem; }
  .seg button { padding: 7px 13px; }
}
</style>
