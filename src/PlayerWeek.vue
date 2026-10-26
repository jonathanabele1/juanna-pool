<script setup>
// Another player's picks for one week, read-only (the Picks tab while you're viewing them). Their picks on games
// that haven't kicked off yet come back from the server hidden.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { accuracyRows } from './lines.js'
import { getLines, getPlayerWeek, getPool, getWeek } from './api.js'
import { gameKey, poolByKey } from './pool.js'
import { groupByKickoff } from './schedule.js'
import { resolveGame } from './lines.js'
import { compareWeeks } from './compare.js'
import { gamePop, pickLabel } from './gamepop.js'
import GameRow from './components/GameRow.vue'
import AccuracyDialog from './components/AccuracyDialog.vue'

const props = defineProps({ player: Object, week: Number })
const emit = defineEmits(['scored', 'mine'])

const w = ref(null)
const mine = ref(null)      // your own saved week, to compare against
const events = ref([])
const pool = ref({})
const error = ref('')
let timer

async function load(quiet = false) {
  clearTimeout(timer)
  try {
    const [pw, lines, pl, my] = await Promise.all([
      getPlayerWeek(props.player.id, props.week),
      getLines(props.week).catch(() => ({ events: [] })),
      getPool(props.week).catch(() => null),
      getWeek(props.week).catch(() => null),
    ])
    w.value = pw
    mine.value = my
    events.value = lines.events || []
    pool.value = poolByKey(pl)
    error.value = ''
  } catch (e) {
    if (!quiet) error.value = e.message
  }
  // games on: keep their score (and the week bar) live
  if (events.value.some(e => e.state === 'in')) timer = setTimeout(() => { load(true); emit('scored') }, 30 * 1000)
}
const onVisible = () => { if (document.visibilityState === 'visible' && w.value) load(true) }
onMounted(() => { load(); document.addEventListener('visibilitychange', onVisible) })
onUnmounted(() => { clearTimeout(timer); document.removeEventListener('visibilitychange', onVisible) })

const games = computed(() => w.value?.games || [])
const isLive = computed(() => events.value.some(e => e.state === 'in'))
const score = computed(() => w.value?.score || null)
const groups = computed(() => groupByKickoff(games.value.map((g, i) => ({ g, i })), events.value))
const liveRec = computed(() => score.value?.live || { wins: 0, losses: 0, pushes: 0 })
const liveGames = computed(() => liveRec.value.wins + liveRec.value.losses + liveRec.value.pushes)
const hasResults = computed(() => !!score.value && score.value.wins + score.value.losses + score.value.pushes + liveGames.value > 0)
const poolFor = g => pool.value[gameKey(g)]?.revealed ? pool.value[gameKey(g)] : null
const accOpen = ref(false)
const accRows = computed(() => accuracyRows(games.value, score.value?.games, events.value))
const resultFor = i => (score.value?.games?.[i]?.outcome === 'hidden' ? null : score.value?.games?.[i])

// ---- you vs them: both weeks side by side, game by game (their picks only once each game kicks off) ----
const myGames = computed(() => (mine.value?.picksSaved ? mine.value.games : null))
const comparing = ref(false)   // closed by default: their page first, the comparison on request
const cmp = computed(() => (w.value?.picksSaved ? compareWeeks(myGames.value, games.value) : null))
const name = computed(() => (props.player.displayName || 'Them').trim().split(/\s+/)[0])
const initial = computed(() => name.value.charAt(0).toUpperCase())
// a pill's color: the same as your own strip on the Picks tab
function segOf(g, res) {
  if (g?.hidden) return { cls: 'hidden', text: '' }
  if (!g?.pick) return { cls: res?.outcome === 'skipped' ? 'skipped' : 'open', text: '' }
  const live = res?.outcome === 'pending' ? res?.live : null
  return { cls: live ? `live-${live}` : res?.outcome || 'pending', text: g.points, loy: Number(g.points) === 50 }
}
const MATCH_TEXT = { same: 'same pick', pts: 'same side, different points', diff: 'opposite sides', one: 'only one of you picked', none: 'neither of you picked', hidden: 'their pick is hidden until kickoff or Sunday 1 PM ET' }
const abbrOf = (g, key) => (resolveGame(g, events.value)[key === 'fav' ? 'favTeam' : 'dogTeam']?.abbr || g[key] || '').toUpperCase()
const pickText = g => (g?.hidden ? 'hidden' : g?.pick ? `${abbrOf(g, g.pick)} ${g.points}` : 'no pick')
const cols = computed(() => (cmp.value?.rows || []).map(r => ({
  i: r.i, match: r.match,
  theirs: segOf(r.theirs, resultFor(r.i)),
  mine: segOf(r.mine, mine.value?.score?.games?.[r.i]),
  label: `${r.theirs.fav} / ${r.theirs.dog}: ${name.value} ${pickText(r.theirs)}, you ${pickText(r.mine)} (${MATCH_TEXT[r.match]})`,
  theirLabel: `${r.theirs.fav} / ${r.theirs.dog}: ${pickText(r.theirs)}`,
})))
const matchPct = computed(() => (cmp.value?.match == null ? null : Math.round(cmp.value.match * 100)))
// head to head this week (as it stands, while games are on)
const h2h = computed(() => {
  const a = mine.value?.score, b = score.value
  if (!a || !b || !hasResults.value) return null
  const live = liveGames.value > 0 || (a.live?.wins + a.live?.losses + a.live?.pushes) > 0
  const me = live ? a.ifEndedNow : a.score, them = live ? b.ifEndedNow : b.score
  const d = me - them
  return { me, them, live, text: !d ? 'Dead even' : d > 0 ? `You by ${d}` : `${name.value} by ${-d}`, lead: d > 0 ? 'pos' : d < 0 ? 'neg' : '' }
})
// ---- tap a pill: the same game popover as your own week card; tap the popover to jump to that game ----
const pop = ref(null)          // { i, left, arrow } (px, inside the strip)
const stripEl = ref(null)
const POP_W = 210
function togglePop(i, col) {
  if (pop.value?.i === i) { pop.value = null; return }
  const strip = stripEl.value.getBoundingClientRect(), b = col.getBoundingClientRect()
  const center = b.left + b.width / 2 - strip.left
  const wd = Math.min(POP_W, strip.width)
  const left = Math.max(0, Math.min(strip.width - wd, center - wd / 2))
  pop.value = { i, left, arrow: center - left }
}
// any other tap closes it (taps on a pill are handled by the pill itself)
const onDocTap = e => { if (pop.value && !e.target.closest?.('.cmp-col, .gpop')) pop.value = null }
onMounted(() => document.addEventListener('pointerdown', onDocTap))
onUnmounted(() => document.removeEventListener('pointerdown', onDocTap))
const popInfo = computed(() => {
  const i = pop.value?.i, g = games.value[i], c = cols.value.find(x => x.i === i)
  if (!g || !c) return null
  const info = gamePop(g, resultFor(i), events.value, { odds: w.value.odds?.[g.eventId] })
  // comparing: your pick on that game too
  const you = comparing.value && myGames.value ? `You: ${pickLabel(myGames.value[i], events.value)}` : ''
  return { ...info, you, cls: c.theirs.cls, label: comparing.value ? c.label : c.theirLabel }
})
function goToGame(i) {
  pop.value = null
  const el = document.querySelector(`[data-game="${i}"]`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash')
  setTimeout(() => el.classList.remove('flash'), 1600)
}
</script>

<template>
  <p v-if="error" class="err">Couldn’t load this week: {{ error }}</p>
  <p v-else-if="!w" class="loading">Loading week {{ week }}…</p>
  <template v-else>
    <section class="weekhead">
      <div class="wh-top">
        <div class="wh-id">
          <p class="wh-who"><b>{{ player.displayName }}</b><template v-if="player.teamName"> · {{ player.teamName }}</template></p>
          <div class="wh-title">
            <h2>Week {{ week }}</h2>
            <span v-if="isLive" class="wh-live" title="Games on now. The red numbers are if they ended as they stand"><i class="ldot"></i>Live</span>
          </div>
          <p v-if="!w.picksSaved" class="wh-sub">
            {{ w.saved ? 'No picks saved for this week.' : 'Lines aren’t posted for this week yet.' }}
          </p>
        </div>
        <button class="btn ghost sm" @click="emit('mine')">My picks</button>
      </div>
      <div v-if="hasResults" class="wh-results">
        <dl class="wh-stats">
          <div :class="['stat', 'score', score.score > 0 ? 'pos' : score.score < 0 ? 'neg' : '']">
            <dt>Score</dt><dd>{{ score.score }}</dd>
            <span v-if="liveGames" class="stat-live">{{ score.ifEndedNow }}</span>
          </div>
          <div class="stat">
            <dt>Record</dt><dd>{{ score.wins }}–{{ score.losses }}<template v-if="score.pushes">–{{ score.pushes }}</template></dd>
            <span v-if="liveGames" class="stat-live">{{ score.wins + liveRec.wins }}–{{ score.losses + liveRec.losses }}<template v-if="score.pushes + liveRec.pushes">–{{ score.pushes + liveRec.pushes }}</template></span>
          </div>
          <div v-if="score.pending" class="stat">
            <dt>Max possible</dt><dd>{{ score.maxScore }}</dd>
            <span v-if="liveGames && score.liveMax != null" class="stat-live">{{ score.liveMax }}</span>
          </div>
          <div v-if="score?.accuracy != null || score?.liveAccuracy != null" class="stat tap" role="button" tabindex="0" aria-haspopup="dialog"
               :aria-label="`Accuracy ${score.accuracy == null ? 'not rated yet' : Math.round(score.accuracy) + '%'}. Show how it's worked out`"
               @click="accOpen = true" @keydown.enter.prevent="accOpen = true" @keydown.space.prevent="accOpen = true">
            <dt>Accuracy<svg class="stat-go" viewBox="0 0 8 12" aria-hidden="true"><path d="M2 2l4 4-4 4" /></svg></dt>
            <dd>{{ score.accuracy == null ? '—' : `${Math.round(score.accuracy)}%` }}</dd>
            <span v-if="score.liveAccuracy != null" class="stat-live" title="If the games on now ended as they stand">{{ Math.round(score.liveAccuracy) }}%</span>
          </div>
        </dl>
      </div>

      <!-- their pills, like your own strip on the Picks tab; "Compare" adds a row of yours and how the two weeks line up -->
      <div v-if="cmp" :class="['wh-results', 'cmp', { open: comparing }]">
        <!-- on top, so it stays where it is when the comparison opens underneath -->
        <button type="button" class="cmp-toggle" role="switch" :aria-checked="comparing" @click="comparing = !comparing">
          <span>Compare with my picks</span>
          <i :class="['sw', { on: comparing }]" aria-hidden="true"></i>
        </button>
        <div ref="stripEl" class="wh-strip cmp-strip" role="group" :aria-label="comparing ? `Your picks next to ${name}'s` : `${name}'s picks`">
          <div v-if="comparing" class="cmp-who" aria-hidden="true">
            <span class="who them" :title="player.displayName">{{ initial }}</span>
            <span class="who you">You</span>
          </div>
          <button v-for="c in cols" :key="c.i" type="button" :class="['cmp-col', c.match]" :aria-label="comparing ? c.label : c.theirLabel"
                  :aria-expanded="pop?.i === c.i" @click="togglePop(c.i, $event.currentTarget)">
            <span :class="['seg', c.theirs.cls, { loy: c.theirs.loy, sel: pop?.i === c.i }]">
              <svg v-if="c.theirs.cls === 'hidden'" viewBox="0 0 10 12" aria-hidden="true"><rect x="1.5" y="5" width="7" height="6" rx="1" /><path d="M3 5V3.5a2 2 0 0 1 4 0V5" /></svg>
              <template v-else>{{ c.theirs.text }}</template>
            </span>
            <span v-if="comparing" :class="['seg', c.mine.cls, { loy: c.mine.loy }]">{{ c.mine.text }}</span>
          </button>
          <button v-if="popInfo" type="button" :class="['gpop', popInfo.cls]" :style="{ left: pop.left + 'px', '--arrow': pop.arrow + 'px' }"
                  :aria-label="`${popInfo.label}. Go to this game.`" @click="goToGame(pop.i)">
            <span class="gp-teams">
              <span v-for="t in popInfo.teams" :key="t.abbr" :class="['gp-team', { mine: t.mine }]">
                <img v-if="t.logo" :src="t.logo" alt="" /><b>{{ t.abbr }}</b><span v-if="t.score != null" class="gp-sc">{{ t.score }}</span>
              </span>
            </span>
            <span class="gp-foot">
              <span class="gp-when">{{ popInfo.when }}</span>
              <span class="gp-pick">{{ popInfo.pick }}</span>
            </span>
            <span v-if="popInfo.chance" class="gp-chance">{{ popInfo.chance }}</span>
            <span v-if="popInfo.you" class="gp-chance">{{ popInfo.you }}</span>
          </button>
        </div>
        <p v-if="hasResults" class="wh-legend">
          <span><i class="dot win"></i>Covered</span>
          <span><i class="dot loss"></i>Missed</span>
          <span class="cmp-tip">Tap a pill for the game</span>
        </p>
        <template v-if="comparing">
          <p v-if="!myGames" class="cmp-note">You have no picks saved this week.</p>
          <p v-else-if="cmp.compared < cmp.rows.length" class="cmp-note">🔒 {{ cmp.rows.length - cmp.compared }} of their picks still hidden</p>
          <dl v-if="myGames && cmp.compared" class="wh-stats">
            <div class="stat" title="Points you both put on the same side (the smaller of the two on each game), out of the points on the games you can compare">
              <dt>Match</dt><dd>{{ matchPct }}%</dd>
              <span class="stat-sub">{{ Math.round(cmp.common) }} of {{ Math.round(cmp.total) }} pts alike</span>
            </div>
            <div class="stat">
              <dt>Same side</dt><dd>{{ cmp.sameSide }}<small> / {{ cmp.both }}</small></dd>
              <span class="stat-sub">{{ cmp.exact }} exact · {{ cmp.atStake }} pts split</span>
            </div>
            <div v-if="h2h" :class="['stat', 'score', h2h.lead]">
              <dt>Head to head</dt><dd>{{ h2h.me }}<small> – {{ h2h.them }}</small></dd>
              <span :class="h2h.live ? 'stat-live' : 'stat-sub'">{{ h2h.text }}</span>
            </div>
          </dl>
        </template>
      </div>
    </section>

    <template v-if="w.picksSaved">
      <section v-for="grp in groups" :key="grp.key" class="group">
        <h2>{{ grp.day }} <small v-if="grp.when">{{ grp.when }}</small></h2>
        <GameRow
          v-for="x in grp.items"
          :key="x.i"
          :data-game="x.i"
          :game="x.g"
          :events="events"
          :result="resultFor(x.i)"
          :odds="w.odds?.[x.g.eventId]"
          :pool="poolFor(x.g)"
          :yours="comparing && myGames ? myGames[x.i] : null"
          :match="cmp?.rows[x.i]?.match"
          other-player
          readonly
        />
      </section>
    </template>

    <AccuracyDialog v-if="accOpen && (score?.accuracy ?? score?.liveAccuracy) != null" :week="week" :pct="score.accuracy" :live-pct="score.liveAccuracy" :rows="accRows"
                    :pending="score.pending" :who="player.displayName" @close="accOpen = false" />
  </template>
</template>

<style scoped>
.err { color: var(--neg); }

/* you vs them */
.cmp-toggle {
  display: inline-flex; align-items: center; gap: 10px; align-self: flex-start; min-height: 36px; margin: -6px 0 -4px;
  padding: 0; border: 0; background: none; font: inherit; font-size: .86rem; font-weight: 700; color: var(--text-2); cursor: pointer;
}
.cmp-toggle:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; border-radius: 6px; }
/* on/off switch */
.sw { flex: none; position: relative; width: 38px; height: 22px; border-radius: 99px; background: var(--chip); transition: background .15s; }
.sw::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px #0f172a40; transition: transform .15s; }
.sw.on { background: var(--blue); }
.sw.on::after { transform: translateX(16px); }
@media (prefers-reduced-motion: reduce) { .sw, .sw::after { transition: none; } }
.cmp-note { margin: 0; font-size: .78rem; color: var(--muted); }
.cmp-strip { align-items: stretch; }
.cmp-who { flex: none; display: flex; flex-direction: column; gap: 3px; padding: 0 4px 0 0; }
.who { height: 26px; min-width: 26px; display: grid; place-items: center; font-size: .62rem; font-weight: 800; color: var(--text-2); }
.who.them { width: 26px; border-radius: 50%; background: var(--blue); color: #fff; font-size: .74rem; }
/* one column per game: their pick on top, yours underneath */
.cmp-col { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; padding: 0; border: 0; border-radius: 6px; background: none; cursor: pointer; font: inherit; }
.cmp-col:focus-visible { outline: 2px solid #93c5fd; outline-offset: 1px; }
.cmp-col .seg { flex: none; width: 100%; cursor: inherit; }
.seg.hidden { background: var(--card); border: 1.5px solid var(--line); }
.seg.hidden svg { width: 9px; height: 11px; fill: none; stroke: var(--faint); stroke-width: 1.4; }
.cmp-tip { margin-left: auto; color: var(--faint); }
@media (max-width: 520px) {
  .cmp-col { gap: 2px; }
  .cmp-who { gap: 2px; padding: 0 3px 0 0; }
  .who { height: 28px; min-width: 24px; }
  .who.them { width: 24px; height: 24px; margin: 2px 0; }
  .cmp-tip { display: none; }
}
</style>
