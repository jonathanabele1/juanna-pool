<script setup>
// Another player's picks for one week, read-only (the Picks tab while you're viewing them). Their picks on games
// that haven't kicked off yet come back from the server hidden.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getLines, getPlayerWeek, getPool } from './api.js'
import { gameKey, poolByKey } from './pool.js'
import { groupByKickoff } from './schedule.js'
import GameRow from './components/GameRow.vue'

const props = defineProps({ player: Object, week: Number })
const emit = defineEmits(['scored', 'mine'])

const w = ref(null)
const events = ref([])
const pool = ref({})
const error = ref('')
let timer

async function load(quiet = false) {
  clearTimeout(timer)
  try {
    const [pw, lines, pl] = await Promise.all([
      getPlayerWeek(props.player.id, props.week),
      getLines(props.week).catch(() => ({ events: [] })),
      getPool(props.week).catch(() => null),
    ])
    w.value = pw
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
const score = computed(() => w.value?.score || null)
const groups = computed(() => groupByKickoff(games.value.map((g, i) => ({ g, i })), events.value))
const liveRec = computed(() => score.value?.live || { wins: 0, losses: 0, pushes: 0 })
const liveGames = computed(() => liveRec.value.wins + liveRec.value.losses + liveRec.value.pushes)
const hasResults = computed(() => !!score.value && score.value.wins + score.value.losses + score.value.pushes + liveGames.value > 0)
const poolFor = g => pool.value[gameKey(g)]?.revealed ? pool.value[gameKey(g)] : null
const resultFor = i => (score.value?.games?.[i]?.outcome === 'hidden' ? null : score.value?.games?.[i])
</script>

<template>
  <p v-if="error" class="err">Couldn’t load this week: {{ error }}</p>
  <p v-else-if="!w" class="loading">Loading week {{ week }}…</p>
  <template v-else>
    <section class="weekhead">
      <div class="wh-top">
        <div class="wh-id">
          <p class="wh-who"><b>{{ player.displayName }}</b><template v-if="player.teamName"> · {{ player.teamName }}</template></p>
          <div class="wh-title"><h2>Week {{ week }}</h2></div>
          <p v-if="!w.picksSaved || w.hiddenCount" class="wh-sub">
            <template v-if="!w.saved">Lines aren’t posted for this week yet.</template>
            <template v-else-if="!w.picksSaved">No picks saved for this week.</template>
            <template v-else-if="w.hiddenCount">
              <span aria-hidden="true">🔒</span> {{ w.hiddenCount }} pick{{ w.hiddenCount > 1 ? 's' : '' }} hidden until {{ w.hiddenCount > 1 ? 'those games kick' : 'that game kicks' }} off
            </template>
          </p>
        </div>
        <button class="btn ghost sm" @click="emit('mine')">My picks</button>
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
          <div v-if="score.accuracy != null" class="stat">
            <dt>Accuracy</dt><dd>{{ Math.round(score.accuracy) }}%</dd>
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
          :odds="w.odds?.[x.g.eventId]"
          :pool="poolFor(x.g)"
          other-player
          readonly
        />
      </section>
    </template>
  </template>
</template>

<style scoped>
.err { color: var(--neg); }
</style>
