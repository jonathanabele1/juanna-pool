<script setup>
// The whole pool: this week's leaderboard (live while games are on), then the season table. Tap a player to open
// their picks on the Picks tab (that week's, from the week table).
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getWeekStandings, getSeasonStandings } from './api.js'
import { pctText } from './odds.js'

const props = defineProps({ currentWeek: Number })
const emit = defineEmits(['open'])

const week = ref(props.currentWeek || 1)
watch(() => props.currentWeek, w => { if (w && !data.value) week.value = w })

const data = ref(null)      // this week's standings
const season = ref(null)
const error = ref('')
let timer
const LIVE_POLL = 30 * 1000

async function loadWeek() {
  const n = week.value
  const d = await getWeekStandings(n)
  if (n === week.value) data.value = d
}
async function load(quiet = false) {
  clearTimeout(timer)
  try {
    await Promise.all([loadWeek(), getSeasonStandings().then(d => { season.value = d })])
    error.value = ''
  } catch (e) {
    if (!quiet) error.value = e.message
  }
  // keep it live while games are on (the season table moves with the live week too)
  if (live.value) timer = setTimeout(() => load(true), LIVE_POLL)
}
const onVisible = () => { if (document.visibilityState === 'visible') load(true) }
onMounted(() => { load(); document.addEventListener('visibilitychange', onVisible) })
onUnmounted(() => { clearTimeout(timer); document.removeEventListener('visibilitychange', onVisible) })
watch(week, () => { data.value = null; loadWeek().catch(e => { error.value = e.message }) })

const seasonRows = computed(() => season.value?.rows || [])
const live = computed(() => (data.value?.games.live || 0) > 0 || seasonRows.value.some(r => r.projected !== r.total))
const g = computed(() => data.value?.games || { total: 0, live: 0, final: 0 })
const started = computed(() => g.value.live + g.value.final > 0)
const weekOver = computed(() => g.value.total > 0 && g.value.final === g.value.total)
const isLive = computed(() => g.value.live > 0)
const rows = computed(() => data.value?.rows || [])
const statusText = computed(() => {
  if (!data.value) return ''
  if (!data.value.posted) return 'No lines yet'
  if (weekOver.value) return 'Final'
  if (isLive.value) return ''   // the Live column and the live records already say it
  if (!started.value) return 'Not started'
  return `${g.value.final} of ${g.value.total} final`
})

// Week columns: Score always; Live while games are on; Win % while the week's still being decided; Max and Live max
// while games are left to play (Live max: games on now end as they stand, every game not started covers; it makes
// way for Win % on phones); Acc once a pick is final (not on phones while games are on). Tap a header to sort by it, tap it again to flip. Default: Live while games are on,
// otherwise Score.
const COLS = { score: 'Score', projected: 'Live', win: 'Win %', max: 'Max', liveMax: 'Live max', accuracy: 'Acc' }
const anyPending = computed(() => rows.value.some(r => r.pending))
const hasWin = computed(() => rows.value.some(r => r.win != null))
const hasAcc = computed(() => rows.value.some(r => r.accuracy != null))
const phoneMq = window.matchMedia('(max-width: 520px)')
const phone = ref(phoneMq.matches)
const onPhone = e => { phone.value = e.matches }
onMounted(() => phoneMq.addEventListener('change', onPhone))
onUnmounted(() => phoneMq.removeEventListener('change', onPhone))
const cols = computed(() => ['score', isLive.value && 'projected', hasWin.value && 'win', anyPending.value && 'max',
  isLive.value && anyPending.value && !(phone.value && hasWin.value) && 'liveMax',
  hasAcc.value && !(phone.value && isLive.value) && 'accuracy'].filter(Boolean))
// the simulation says never/certain only when it's settled (1 or 0); anything else stays off 0% and 100%
const cell = (r, c) => (r[c] == null ? '—' : c === 'accuracy' ? `${Math.round(r[c])}%` : c !== 'win' ? r[c] : r[c] === 1 ? '100%' : r[c] === 0 ? '0%' : pctText(r[c]))
const ACC_TITLE = 'Accuracy: how close the final picks came, weighted by points. A cover or push is 100%, and a miss loses about 7% a point, down to 0% at 14 (the LOY counts as 20 points here). An app stat, not a league one.'
const WIN_TITLE = 'Chance to finish first this week among the players here (record breaks a tie). Games on now play out at their cover odds; picks on games that haven’t started are still hidden, so those count as coin flips.'
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
const seasonMove = r => (r.lastRank ? r.lastRank - r.rank : 0)   // places gained since the week before
const ord = n => `${n}${['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) ? 0 : n % 10] || 'th'}`
const names = list => (list.length > 2 ? `${list[0].name} +${list.length - 1}` : list.map(r => r.name).join(' & '))

// ---- the three numbers above each table ----
// week: who's on top (live while games are on), where you stand, the pool's average
const weekTiles = computed(() => {
  const list = rows.value
  if (!started.value || !list.length) return []
  const by = isLive.value ? 'projected' : 'score', rk = isLive.value ? 'projectedRank' : 'rank'
  const top = list.filter(r => r[rk] === 1)
  const me = list.find(r => r.me)
  const avg = Math.round((list.reduce((t, r) => t + r[by], 0) / list.length) * 10) / 10
  return [
    { label: weekOver.value ? 'Winner' : 'Leading', value: top[0][by], sub: names(top), crown: weekOver.value },
    me ? { label: 'You', value: ord(me[rk]), sub: `of ${list.length} · ${me[by]} pts`, me: true }
      : { label: 'Players', value: list.length, sub: `${data.value.noPicks.length} without picks` },
    { label: 'Pool average', value: avg, sub: isLive.value ? 'if it ended now' : weekOver.value ? 'final' : 'so far' },
  ]
})
// season: the leader, where you stand, the best single week
const seasonTiles = computed(() => {
  const list = seasonRows.value
  if (!list.length) return []
  const top = list.filter(r => r.rank === 1)
  const second = list.find(r => r.rank > 1)
  const me = list.find(r => r.me)
  const best = list.filter(r => r.best).reduce((a, b) => (!a || b.best.score > a.best.score ? b : a), null)
  return [
    { label: 'Leader', value: top[0].total, sub: second ? `${names(top)} · +${top[0].total - second.total}` : names(top) },
    me ? { label: 'You', value: ord(me.rank), sub: me.rank === 1 ? 'in the lead' : `${top[0].total - me.total} back`, me: true }
      : { label: 'Players', value: list.length, sub: 'this season' },
    best && { label: 'Best week', value: best.best.score, sub: `${best.name} · wk ${best.best.week}` },
  ].filter(Boolean)
})
const behind = r => seasonRows.value[0].total - r.total
</script>

<template>
  <div class="standings">
    <p v-if="error" class="err">Couldn’t load the league: {{ error }}</p>

    <!-- ================= WEEK ================= -->
    <section class="lg">
      <header class="lg-head">
        <div class="lg-title">
          <h2>Week {{ week }}</h2>
          <span v-if="statusText" :class="['lg-status', { final: weekOver }]">{{ statusText }}</span>
        </div>
        <div class="stepper" aria-label="Choose week">
          <button :disabled="week <= 1" aria-label="Previous week" @click="week--">‹</button>
          <button :disabled="week >= 18" aria-label="Next week" @click="week++">›</button>
        </div>
      </header>

      <p v-if="!data" class="loading">Loading week {{ week }}…</p>
      <p v-else-if="!data.posted" class="empty">Week {{ week }}’s lines aren’t posted yet.</p>
      <div v-else-if="!started" class="prestart">
        <p class="pre-note">No games have kicked off yet. {{ rows.length }} of {{ rows.length + data.noPicks.length }} have picks in.</p>
        <ul class="inlist">
          <li v-for="r in rows" :key="r.id" :class="{ me: r.me }" @click="emit('open', r.id, week)"><span class="ok">✓</span>{{ r.name }}</li>
          <li v-for="n in data.noPicks" :key="n" class="missing"><span>·</span>{{ n }} <small>no picks yet</small></li>
        </ul>
      </div>

      <template v-else>
        <dl v-if="weekTiles.length" class="tiles">
          <div v-for="t in weekTiles" :key="t.label" :class="['tile', { me: t.me }]">
            <dt>{{ t.label }}</dt>
            <dd>{{ t.value }}<span v-if="t.crown" class="crown">👑</span></dd>
            <span class="tile-sub">{{ t.sub }}</span>
          </div>
        </dl>
        <div class="table" role="table" aria-label="Week standings" :style="{ '--cols': cols.length }">
          <div class="tr th" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">Player</span>
            <button v-for="c in cols" :key="c" type="button" role="columnheader" :aria-sort="ariaSort(c)"
                    :class="['num', 'sort', { on: key === c }]" @click="sortBy(c)">
              <span :title="c === 'win' ? WIN_TITLE : c === 'accuracy' ? ACC_TITLE : null">{{ COLS[c] }}</span><i class="arr" :class="{ up: key === c && sortDir > 0 }"></i>
            </button>
          </div>
          <button
            v-for="r in sorted" :key="r.id" type="button" role="row"
            :class="['tr', { me: r.me, first: rankOf(r) === 1 }]"
            @click="emit('open', r.id, week)"
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
            <span v-for="c in cols" :key="c" :class="['num', 'val', { pct: c === 'accuracy', on: key === c, neg: c !== 'win' && r[c] < 0, out: c === 'win' && r.win === 0 }]">{{ cell(r, c) }}</span>
          </button>
          <p v-if="data.noPicks.length" class="nopicks">No picks: {{ data.noPicks.join(', ') }}</p>
        </div>
      </template>
    </section>

    <!-- ================= SEASON ================= -->
    <section class="lg">
      <header class="lg-head">
        <div class="lg-title">
          <h2>Season</h2>
          <span v-if="season?.latestWeek" class="lg-status">Through week {{ season.latestWeek }}</span>
        </div>
      </header>

      <p v-if="!season" class="loading">Adding up the season…</p>
      <p v-else-if="!seasonRows.length" class="empty">No scored weeks yet.</p>
      <template v-else>
        <dl class="tiles">
          <div v-for="t in seasonTiles" :key="t.label" :class="['tile', { me: t.me }]">
            <dt>{{ t.label }}</dt>
            <dd>{{ t.value }}</dd>
            <span class="tile-sub">{{ t.sub }}</span>
          </div>
        </dl>
        <div class="table season" role="table" aria-label="Season standings">
          <div class="tr th" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">Player</span>
            <span role="columnheader" class="num">Total</span>
            <span role="columnheader" class="num avg">Avg</span>
            <span role="columnheader" class="num acc" :title="ACC_TITLE">Acc</span>
            <span role="columnheader" class="num wins" title="Weeks won (finished weeks)">Wins</span>
          </div>
          <button v-for="r in seasonRows" :key="r.id" type="button" role="row" :class="['tr', { me: r.me, first: r.rank === 1 }]" @click="emit('open', r.id)">
            <span class="rank">
              {{ r.rank }}
              <i v-if="seasonMove(r) > 0" class="mv up" :title="`Up ${seasonMove(r)} since last week`">▲{{ seasonMove(r) }}</i>
              <i v-else-if="seasonMove(r) < 0" class="mv down" :title="`Down ${-seasonMove(r)} since last week`">▼{{ -seasonMove(r) }}</i>
            </span>
            <span class="who">
              <b>{{ r.name }}</b>
              <small>
                {{ r.record.wins }}–{{ r.record.losses }}<template v-if="r.record.pushes">–{{ r.record.pushes }}</template>
                <template v-if="r.record.pct != null"> · {{ r.record.pct }}%</template>
                <span class="mobile-only"> · avg {{ r.average }}</span>
              </small>
            </span>
            <span class="num score">
              <b :class="{ neg: r.total < 0 }">{{ r.total }}</b>
              <small v-if="r.projected !== r.total" :class="['lv', r.projected > r.total ? 'pos' : 'neg']" title="If the games on now ended as they stand"><i class="ldot"></i>{{ r.projected }}</small>
              <small v-else-if="behind(r)" class="back" :title="`${behind(r)} behind the leader`">−{{ behind(r) }}</small>
            </span>
            <span class="num avg">{{ r.average }}</span>
            <span class="num acc pct">{{ r.accuracy == null ? '—' : `${Math.round(r.accuracy)}%` }}</span>
            <span class="num wins">{{ r.weeklyWins || '—' }}</span>
          </button>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.standings { display: flex; flex-direction: column; gap: 16px; }

/* one card per section: title, three highlight numbers, then the table */
.lg { background: var(--card); border-radius: 18px; box-shadow: 0 1px 2px #0000000d, 0 4px 14px #0000000a; overflow: hidden; }
.lg-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 14px 12px 18px; }
.lg-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-width: 0; }
.lg-title h2 { margin: 0; font-size: 1.25rem; font-weight: 800; letter-spacing: -.02em; color: var(--text); text-transform: none; }
.lg-status { display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 10px; border-radius: 999px; background: var(--soft); color: var(--text-2); font-size: .7rem; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.lg-status.final { background: var(--ink); color: var(--on-ink); text-transform: uppercase; letter-spacing: .05em; }
.stepper { display: inline-flex; flex: none; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.stepper button { width: 38px; height: 36px; border: 0; background: var(--card); font-size: 1.3rem; cursor: pointer; color: var(--text); }
.stepper button + button { border-left: 1px solid var(--line); }
.stepper button:hover:not(:disabled) { background: var(--soft); }
.stepper button:disabled { color: var(--faintest); cursor: default; }

.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0; padding: 12px 14px; background: var(--card-2); border-top: 1px solid var(--line-soft); }
.tile { min-width: 0; background: var(--card); border: 1px solid var(--line-soft); border-radius: 14px; padding: 9px 11px; display: flex; flex-direction: column; gap: 3px; }
.tile.me { border-color: var(--blue-line); background: var(--blue-tint); }
.tile dt { font-size: .62rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--faint); }
.tile dd { margin: 0; font-size: 1.35rem; font-weight: 800; line-height: 1.1; letter-spacing: -.02em; color: var(--text); font-variant-numeric: tabular-nums; }
.tile-sub { font-size: .74rem; font-weight: 600; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* table: # | player | one column per number (Score, Live, Max, Live max) */
.table { border-top: 1px solid var(--line-soft); }
.tr {
  display: grid; grid-template-columns: 40px minmax(0, 1fr) repeat(var(--cols, 1), 62px); align-items: center; gap: 0 4px;
  width: 100%; min-height: 56px; padding: 8px 14px 8px 12px; border: 0; border-top: 1px solid var(--line-soft); background: var(--card); font: inherit; color: inherit; text-align: left;
}
.season .tr { grid-template-columns: 40px minmax(0, 1fr) 76px 56px 56px 56px; }
.th { min-height: 0; border-top: 0; background: var(--card-2); padding-top: 8px; padding-bottom: 8px; font-size: .62rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--faint); }
.th .sort {
  align-self: stretch; border: 0; background: none; padding: 4px 0; margin: -4px 0; font: inherit; color: inherit; text-transform: inherit; letter-spacing: inherit;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: flex-end; gap: 3px; line-height: 1.15; text-align: right;
}
.th .sort:hover { color: var(--text-2); }
.th .sort.on { color: var(--blue); }
.th .sort:focus-visible { outline: 2px solid #93c5fd; border-radius: 4px; }
.arr { width: 0; height: 0; border-left: 3.5px solid transparent; border-right: 3.5px solid transparent; border-top: 4px solid currentColor; opacity: 0; flex: none; }
.sort.on .arr { opacity: 1; }
.arr.up { transform: rotate(180deg); }
button.tr { cursor: pointer; transition: background .12s; }
button.tr:hover { background: var(--card-2); }
button.tr:focus-visible { outline: 2px solid #93c5fd; outline-offset: -2px; }
.tr.me { background: var(--blue-tint); box-shadow: inset 3px 0 0 #2563eb; }
.tr.me:hover { background: var(--blue-tint-2); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.rank { font-weight: 800; font-size: 1rem; color: var(--muted); display: flex; flex-direction: column; align-items: flex-start; line-height: 1.05; font-variant-numeric: tabular-nums; }
.first .rank { color: var(--amber-ink); }
.mv { font-style: normal; font-size: .6rem; font-weight: 800; }
.mv.up { color: var(--pos); } .mv.down { color: var(--neg); }
.who { display: flex; flex-direction: column; min-width: 0; gap: 2px; }
.who b { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who small { font-size: .72rem; color: var(--faint); font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.crown { margin-left: 5px; }
.lv { color: var(--neg); font-weight: 700; }
.val { font-size: 1rem; font-weight: 700; color: var(--faint); }
.val.on { font-size: 1.12rem; font-weight: 800; color: var(--text); }
.val.neg { color: #f87171; } .val.on.neg { color: var(--neg); }
.val.out { color: var(--faintest); }
.score { font-weight: 800; font-size: 1.1rem; color: var(--text); }
.season .score { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.15; }
.season .score small { font-size: .7rem; display: inline-flex; align-items: center; gap: 4px; }
.season .score small.back { color: var(--faint); font-weight: 600; }
.avg, .acc, .wins { color: var(--text-2); font-weight: 700; }
.pos { color: var(--pos); }
.neg { color: var(--neg); }
.season .score b.neg { color: var(--neg); }
.mobile-only { display: none; }
.nopicks { margin: 0; padding: 10px 14px; border-top: 1px solid var(--line-soft); font-size: .76rem; color: var(--faint); }

.prestart { padding: 12px 14px 14px; border-top: 1px solid var(--line-soft); }
.pre-note { margin: 0; font-size: .85rem; color: var(--muted); }
.inlist { list-style: none; padding: 0; margin: 10px 0 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; }
.inlist li { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 10px; background: var(--card-2); font-weight: 600; font-size: .88rem; cursor: pointer; }
.inlist li.me { background: var(--blue-tint); }
.inlist li.missing { color: var(--faint); cursor: default; font-weight: 500; }
.inlist small { font-size: .7rem; }
.ok { color: var(--pos); font-weight: 800; }
.loading, .empty { margin: 0; color: var(--muted); text-align: center; padding: 28px 10px; border-top: 1px solid var(--line-soft); }
.err { color: var(--neg); }

@media (max-width: 520px) {
  .tr { grid-template-columns: 26px minmax(0, 1fr) repeat(var(--cols, 1), 46px); padding: 8px 10px; gap: 0 3px; min-height: 52px; }
  .season .tr { grid-template-columns: 26px minmax(0, 1fr) 64px 48px 48px; }
  .season .avg { display: none; }
  .pct, .val.on.pct { font-size: .82rem; }
  .mobile-only { display: inline; }
  .th { font-size: .56rem; letter-spacing: .03em; }
  .val { font-size: .92rem; } .val.on { font-size: 1rem; }
  .lg-head { padding: 12px 10px 10px 14px; }
  .tiles { padding: 10px; gap: 6px; }
  .tile { padding: 8px 9px; }
  .tile dd { font-size: 1.15rem; }
  .tile-sub { font-size: .68rem; }
}
</style>
