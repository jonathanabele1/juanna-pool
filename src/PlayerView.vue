<script setup>
// Another player's picks (week by week, read-only) and season stats. Their picks on games that haven't
// kicked off yet come back from the server hidden.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getLines, getPlayerWeek, getPlayerWeeks, getPool } from './api.js'
import { gameKey, poolByKey } from './pool.js'
import { groupByKickoff } from './schedule.js'
import WeekBar from './components/WeekBar.vue'
import GameRow from './components/GameRow.vue'
import PlayerPicker from './components/PlayerPicker.vue'
import StatsView from './StatsView.vue'

const props = defineProps({ players: Array, playerId: Number, currentWeek: Number, week: Number })
const emit = defineEmits(['update:playerId', 'back', 'mine'])

const view = ref('picks')   // picks | stats
const week = ref(props.week || props.currentWeek || 1)
const summaries = ref([])
const w = ref(null)
const events = ref([])
const pool = ref({})
const error = ref('')
const refresh = ref(0)
let timer

const player = computed(() => props.players.find(p => p.id === props.playerId))
const isMe = computed(() => !!player.value?.me)

async function loadWeek(quiet = false) {
  clearTimeout(timer)
  const id = props.playerId, n = week.value
  if (!quiet) { w.value = null; error.value = '' }
  try {
    const [pw, lines, pl] = await Promise.all([
      getPlayerWeek(id, n),
      getLines(n).catch(() => ({ events: [] })),
      getPool(n).catch(() => null),
    ])
    if (id !== props.playerId || n !== week.value) return
    w.value = pw
    events.value = lines.events || []
    pool.value = poolByKey(pl)
  } catch (e) {
    if (!quiet) error.value = e.message
  }
  if (events.value.some(e => e.state === 'in')) {
    timer = setTimeout(() => { refresh.value++; loadWeek(true); loadSummaries() }, 30 * 1000)
  }
}
async function loadSummaries() {
  try { summaries.value = await getPlayerWeeks(props.playerId) } catch { summaries.value = [] }
}
onMounted(() => { loadWeek(); loadSummaries() })
onUnmounted(() => clearTimeout(timer))
watch(() => props.playerId, () => { loadWeek(); loadSummaries() })
watch(week, () => loadWeek())

const games = computed(() => w.value?.games || [])
const score = computed(() => w.value?.score || null)
const groups = computed(() => groupByKickoff(games.value.map((g, i) => ({ g, i })), events.value))
const liveRec = computed(() => score.value?.live || { wins: 0, losses: 0, pushes: 0 })
const liveGames = computed(() => liveRec.value.wins + liveRec.value.losses + liveRec.value.pushes)
const hasResults = computed(() => !!score.value && score.value.wins + score.value.losses + score.value.pushes + liveGames.value > 0)
const shownPoints = computed(() => games.value.filter(g => g.pick).reduce((s, g) => s + (Number(g.points) || 0), 0))
const poolFor = g => pool.value[gameKey(g)]?.revealed ? pool.value[gameKey(g)] : null
const resultFor = i => (score.value?.games?.[i]?.outcome === 'hidden' ? null : score.value?.games?.[i])
</script>

<template>
  <div class="player">
    <section class="ph">
      <button class="back" @click="emit('back')"><span aria-hidden="true">←</span> League</button>
      <PlayerPicker :players="players" :model-value="playerId" label="Player" @update:model-value="emit('update:playerId', $event)" />
    </section>

    <div class="subtabs" role="tablist">
      <button role="tab" :aria-selected="view === 'picks'" :class="{ on: view === 'picks' }" @click="view = 'picks'">Picks</button>
      <button role="tab" :aria-selected="view === 'stats'" :class="{ on: view === 'stats' }" @click="view = 'stats'">Season stats</button>
    </div>

    <template v-if="view === 'picks'">
      <WeekBar v-model="week" :current-week="currentWeek" :summaries="summaries" />

      <p v-if="error" class="err">Couldn’t load this week: {{ error }}</p>
      <p v-else-if="!w" class="loading">Loading…</p>
      <template v-else>
        <section class="weekhead">
          <div class="wh-top">
            <div class="wh-id">
              <div class="wh-title"><h2>{{ player?.displayName }} · Week {{ week }}</h2></div>
              <p class="wh-sub">
                <template v-if="!w.saved">Lines aren’t posted for this week yet.</template>
                <template v-else-if="!w.picksSaved">No picks saved for this week.</template>
                <template v-else-if="w.hiddenCount">
                  <span aria-hidden="true">🔒</span> {{ w.hiddenCount }} pick{{ w.hiddenCount > 1 ? 's' : '' }} hidden until {{ w.hiddenCount > 1 ? 'those games kick' : 'that game kicks' }} off
                </template>
                <template v-else-if="isMe">These are your picks. <button class="link" @click="emit('mine', week)">Edit on the Picks tab</button></template>
                <template v-else>All picks revealed · {{ shownPoints }} points used</template>
              </p>
            </div>
          </div>
          <div v-if="hasResults" class="wh-results">
            <dl class="wh-stats">
              <div :class="['stat', 'score', score.score > 0 ? 'pos' : score.score < 0 ? 'neg' : '']">
                <dt>Score</dt><dd>{{ score.score }}</dd>
                <span v-if="liveGames" class="stat-live"><i class="ldot"></i>Live {{ score.ifEndedNow }}</span>
              </div>
              <div class="stat">
                <dt>Record</dt><dd>{{ score.wins }}–{{ score.losses }}<template v-if="score.pushes">–{{ score.pushes }}</template></dd>
                <span v-if="liveGames" class="stat-live"><i class="ldot"></i>Live {{ score.wins + liveRec.wins }}–{{ score.losses + liveRec.losses }}<template v-if="score.pushes + liveRec.pushes">–{{ score.pushes + liveRec.pushes }}</template></span>
              </div>
              <div v-if="score.pending" class="stat">
                <dt>Max possible</dt><dd>{{ score.maxScore }}</dd>
                <span v-if="liveGames && score.liveMax != null" class="stat-live"><i class="ldot"></i>Live {{ score.liveMax }}</span>
              </div>
            </dl>
          </div>
        </section>

        <template v-if="w.picksSaved">
          <section v-for="grp in groups" :key="grp.key" class="group">
            <h2>{{ grp.day }} <small v-if="grp.when">{{ grp.when }}</small></h2>
            <GameRow
              v-for="x in grp.items"
              :key="x.i"
              :game="x.g"
              :events="events"
              :result="resultFor(x.i)"
              :pool="poolFor(x.g)"
              :other-player="!isMe"
              readonly
            />
          </section>
        </template>
      </template>
    </template>

    <StatsView v-else :user-id="playerId" :mine="isMe" :refresh="refresh" />
  </div>
</template>

<style scoped>
.player { display: flex; flex-direction: column; gap: 10px; }
.ph { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.back { border: 0; background: none; font: inherit; font-weight: 700; color: #2563eb; cursor: pointer; padding: 6px 2px; }
.back:hover { text-decoration: underline; }
.subtabs { margin: 0; }
.err { color: #b91c1c; }
.wh-sub .link { font-size: inherit; }
</style>
