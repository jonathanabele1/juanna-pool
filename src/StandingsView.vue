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

// Week table: sorted by live score (the score if every game ended now) until the week has no live games,
// then by score. Tap a column header to sort by it; tap it again to flip (lowest first).
const sortKey = ref('projected')
const sortDir = ref(-1)
const key = computed(() => (isLive.value ? sortKey.value : 'score'))
function sortBy(k) {
  if (key.value === k) sortDir.value *= -1
  else { sortKey.value = k; sortDir.value = -1 }
}
const sorted = computed(() => {
  const k = key.value, other = k === 'score' ? 'projected' : 'score'
  return [...rows.value].sort((a, b) => sortDir.value * (a[k] - b[k] || a[other] - b[other]) || a.name.localeCompare(b.name))
})
const rankOf = r => (key.value === 'projected' ? r.projectedRank : r.rank)
const arrow = k => (key.value === k ? (sortDir.value < 0 ? '▼' : '▲') : '')

const rec = r => `${r.wins}–${r.losses}${r.pushes ? `–${r.pushes}` : ''}`
const liveRec = r => (r.live.wins + r.live.losses + r.live.pushes ? `${r.live.wins}–${r.live.losses}${r.live.pushes ? `–${r.live.pushes}` : ''}` : '')
const sign = n => (n > 0 ? `+${n}` : `${n}`)
const move = r => r.rank - r.projectedRank   // places gained if the live games ended now
const ord = n => `${n}${['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) ? 0 : n % 10] || 'th'}`
const me = computed(() => rows.value.find(r => r.me))
// projected == score once nothing is live, so this works for live and finished weeks alike
const behind = computed(() => (me.value && rows.value[0] && rows.value[0] !== me.value ? rows.value[0].projected - me.value.projected : 0))
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
        <span>Week {{ week }}<small v-if="week === currentWeek">now</small></span>
        <button :disabled="week >= 18" aria-label="Next week" @click="week++">›</button>
      </div>
    </section>

    <p v-if="error" class="err">Couldn’t load the league: {{ error }}</p>

    <!-- ================= WEEK ================= -->
    <template v-else-if="mode === 'week'">
      <p v-if="!data" class="loading">Loading week {{ week }}…</p>
      <template v-else>
        <p v-if="isLive" class="livebar">
          <i class="ldot"></i><b>{{ g.live }} game{{ g.live > 1 ? 's' : '' }} live</b>
          <span>{{ g.final }} of {{ g.total }} final · updates every 30s</span>
        </p>
        <p v-else-if="weekOver" class="donebar">Final · all {{ g.total }} games played</p>
        <p v-else-if="started" class="donebar">{{ g.final }} of {{ g.total }} games final</p>

        <section v-if="me && started" :class="['mine', { up: move(me) > 0, down: move(me) < 0 }]">
          <span class="big">{{ ord(isLive ? me.projectedRank : me.rank) }}</span>
          <span class="txt">
            <b>{{ isLive ? 'Where you’d finish if it ended now' : weekOver ? 'Your finish this week' : 'Where you stand' }}</b>
            <small>
              of {{ rows.length }}
              <template v-if="isLive && move(me)"> · {{ move(me) > 0 ? `up ${move(me)}` : `down ${-move(me)}` }} from {{ ord(me.rank) }} on final games</template>
              <template v-if="behind > 0"> · {{ behind }} behind the lead</template>
              <template v-else-if="me.projectedRank === 1 && rows.length > 1"> · {{ me.projected - rows[1].projected }} ahead</template>
            </small>
          </span>
        </section>

        <p v-if="!data.posted" class="empty">Week {{ week }}’s lines aren’t posted yet.</p>
        <section v-else-if="!started" class="card prestart">
          <h3>No games have kicked off yet</h3>
          <p class="note">The table goes live at the first kickoff. Picks stay hidden until each game starts.</p>
          <ul class="inlist">
            <li v-for="r in rows" :key="r.id" :class="{ me: r.me }" @click="emit('open', r.id)"><span class="ok">✓</span>{{ r.name }}</li>
            <li v-for="n in data.noPicks" :key="n" class="missing"><span>·</span>{{ n }} <small>no picks yet</small></li>
          </ul>
        </section>

        <section v-else class="table" role="table" aria-label="Week standings">
          <div :class="['tr', 'th', { one: !isLive }]" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">Player</span>
            <button v-if="isLive" role="columnheader" :aria-sort="key === 'projected' ? (sortDir < 0 ? 'descending' : 'ascending') : 'none'"
                    :class="['num', 'sort', { on: key === 'projected' }]" title="Score if every game ended now. Tap to sort." @click="sortBy('projected')">
              <i class="ldot"></i>Live score <span class="arr">{{ arrow('projected') }}</span>
            </button>
            <button role="columnheader" :aria-sort="key === 'score' ? (sortDir < 0 ? 'descending' : 'ascending') : 'none'"
                    :class="['num', 'sort', { on: key === 'score' }]" title="Tap to sort" @click="sortBy('score')">
              Score <span class="arr">{{ arrow('score') }}</span>
            </button>
          </div>
          <button
            v-for="r in sorted" :key="r.id" type="button" role="row"
            :class="['tr', { one: !isLive, me: r.me, first: rankOf(r) === 1 }]"
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
              <b>{{ r.name }}<em v-if="r.me">you</em><span v-if="weekOver && r.rank === 1" class="crown" title="Week winner">👑</span></b>
              <small>
                {{ rec(r) }}
                <template v-if="liveRec(r)"> · <span class="lv"><i class="ldot"></i>{{ liveRec(r) }} live</span></template>
                <template v-if="r.pending && !isLive"> · {{ r.pending }} to play · max {{ r.max }}</template>
                <template v-if="r.penalties"> · <span class="neg">−{{ r.penalties }} pen.</span></template>
              </small>
            </span>
            <span v-if="isLive" :class="['num', 'proj', { on: key === 'projected' }]">
              <b :class="{ neg: r.projected < 0 }">{{ r.projected }}</b>
              <small v-if="r.projected !== r.score" :class="r.projected > r.score ? 'pos' : 'neg'">{{ sign(r.projected - r.score) }}</small>
            </span>
            <span :class="['num', 'score', { neg: r.score < 0, on: key === 'score' }]">{{ r.score }}</span>
          </button>
          <p v-if="data.noPicks.length" class="nopicks">No picks this week: {{ data.noPicks.join(', ') }}</p>
        </section>
        <p v-if="started" class="note foot">Tap a player to see their picks. Picks on games that haven’t started stay hidden.</p>
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
          <span role="columnheader" class="num wins" title="Weeks won">Wk wins</span>
        </div>
        <button v-for="r in season.rows" :key="r.id" type="button" role="row" :class="['tr', { me: r.me, first: r.rank === 1 }]" @click="emit('open', r.id)">
          <span class="rank">{{ r.rank }}</span>
          <span class="who">
            <b>{{ r.name }}<em v-if="r.me">you</em></b>
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
      <p v-if="season?.rows.length" class="note foot">Week wins count finished weeks only. Tap a player for their picks and stats.</p>
    </template>
  </div>
</template>

<style scoped>
.standings { display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.seg { display: inline-flex; background: #e2e8f0; border-radius: 12px; padding: 3px; }
.seg button { border: 0; background: none; padding: 7px 18px; border-radius: 9px; font-weight: 700; color: #475569; cursor: pointer; }
.seg button.on { background: #fff; color: #0f172a; box-shadow: 0 1px 3px #0002; }
.stepper { display: inline-flex; align-items: center; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
.stepper button { width: 40px; height: 38px; border: 0; background: none; font-size: 1.3rem; cursor: pointer; color: #0f172a; }
.stepper button:hover:not(:disabled) { background: #f1f5f9; }
.stepper button:disabled { color: #cbd5e1; cursor: default; }
.stepper span { min-width: 92px; text-align: center; font-weight: 800; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.stepper small { font-size: .6rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #2563eb; }

.livebar, .donebar { margin: 0; display: flex; align-items: center; gap: 4px 10px; flex-wrap: wrap; font-size: .8rem; color: #64748b; }
.livebar b { color: #b91c1c; }
.donebar { font-weight: 700; color: #334155; }

.mine { display: flex; align-items: center; gap: 14px; background: #0f172a; color: #fff; border-radius: 18px; padding: 14px 18px; }
.mine .big { font-size: 2.2rem; font-weight: 800; letter-spacing: -.03em; line-height: 1; }
.mine .txt { display: flex; flex-direction: column; gap: 2px; }
.mine small { color: #94a3b8; font-size: .8rem; }
.mine.up .big { color: #4ade80; } .mine.down .big { color: #fca5a5; }

.table { background: #fff; border-radius: 18px; box-shadow: 0 1px 2px #0000000d, 0 4px 14px #0000000a; overflow: hidden; }
.tr {
  display: grid; grid-template-columns: 56px minmax(0, 1fr) 104px 72px; align-items: center; gap: 8px;
  width: 100%; padding: 11px 16px; border: 0; border-top: 1px solid #f1f5f9; background: #fff; font: inherit; color: inherit; text-align: left;
}
.tr.one { grid-template-columns: 56px minmax(0, 1fr) 80px; }
.season .tr { grid-template-columns: 56px minmax(0, 1fr) 84px 64px 70px; }
.th .sort {
  border: 0; background: none; padding: 0; font: inherit; color: inherit; text-transform: inherit; letter-spacing: inherit;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: flex-end; gap: 5px; white-space: nowrap;
}
.th .sort:hover { color: #475569; }
.th .sort.on { color: #0f172a; }
.th .sort:focus-visible { outline: 2px solid #93c5fd; border-radius: 4px; }
.arr { display: inline-block; min-width: .7em; font-size: .6rem; }
button.tr { cursor: pointer; transition: background .12s; }
button.tr:hover { background: #f8fafc; }
button.tr:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }
.tr.me { background: #eff6ff; box-shadow: inset 4px 0 0 #2563eb; }
.tr.me:hover { background: #e0ecff; }
.th { border-top: 0; background: #f8fafc; padding-top: 9px; padding-bottom: 9px; font-size: .64rem; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; color: #94a3b8; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.rank { font-weight: 800; font-size: 1.05rem; color: #334155; display: inline-flex; align-items: center; gap: 4px; font-variant-numeric: tabular-nums; }
.first .rank { color: #b45309; }
.mv { font-style: normal; font-size: .62rem; font-weight: 800; }
.mv.up { color: #15803d; } .mv.down { color: #b91c1c; }
.who { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
.who b { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who em { font-style: normal; font-size: .58rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; background: #2563eb; color: #fff; padding: 1px 6px; border-radius: 99px; margin-left: 6px; vertical-align: 2px; }
.who small { font-size: .74rem; color: #64748b; font-variant-numeric: tabular-nums; }
.crown { margin-left: 6px; }
.lv { display: inline-flex; align-items: center; gap: 4px; color: #b91c1c; font-weight: 700; }
.score { font-weight: 800; font-size: 1.1rem; color: #94a3b8; }
.score.on { color: #0f172a; }
.proj b { color: #94a3b8; } .proj.on b { color: #0f172a; }
.proj { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.1; }
.proj b { font-size: 1.25rem; font-weight: 800; }
.proj small { font-size: .7rem; font-weight: 700; }
.season .score { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.15; color: #0f172a; }
.season .score small { font-size: .7rem; }
.avg, .wins { color: #475569; font-weight: 700; }
.pos { color: #15803d; }
.neg { color: #b91c1c; }
.score.neg, .proj b.neg, .season .score b.neg { color: #b91c1c; }
.mobile-only { display: none; }
.nopicks { margin: 0; padding: 10px 16px; border-top: 1px solid #f1f5f9; font-size: .78rem; color: #94a3b8; }

.card { background: #fff; border-radius: 18px; padding: 16px 18px; box-shadow: 0 1px 2px #0000000d; }
.card h3 { margin: 0; font-size: 1rem; }
.inlist { list-style: none; padding: 0; margin: 12px 0 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; }
.inlist li { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 10px; background: #f8fafc; font-weight: 600; font-size: .88rem; cursor: pointer; }
.inlist li.me { background: #eff6ff; }
.inlist li.missing { color: #94a3b8; cursor: default; font-weight: 500; }
.inlist small { font-size: .7rem; }
.ok { color: #16a34a; font-weight: 800; }
.note { font-size: .75rem; color: #94a3b8; margin: 4px 0 0; }
.foot { margin: 0 2px; }
.loading, .empty { color: #64748b; text-align: center; padding: 34px 10px; }
.err { color: #b91c1c; }

@media (max-width: 520px) {
  .tr { grid-template-columns: 40px minmax(0, 1fr) 84px 54px; padding: 10px 12px; gap: 6px; }
  .tr.one { grid-template-columns: 40px minmax(0, 1fr) 64px; }
  .season .tr { grid-template-columns: 40px minmax(0, 1fr) 74px 46px; }
  .season .avg { display: none; }
  .mobile-only { display: inline; }
  .th .sort { letter-spacing: .03em; }
  .mine { padding: 12px 14px; }
  .mine .big { font-size: 1.9rem; }
  .head { gap: 8px; }
}
</style>
