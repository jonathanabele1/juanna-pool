<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getLines, getWeeks, getMe, getAnnouncement, getPlayers, isDemoLive, setDemoLive } from './api.js'
import WeekBar from './components/WeekBar.vue'
import Countdown from './components/Countdown.vue'
import AccountMenu from './components/AccountMenu.vue'
import PicksView from './PicksView.vue'
import StatsView from './StatsView.vue'
import StandingsView from './StandingsView.vue'
import PlayerView from './PlayerView.vue'
import PlayerPicker from './components/PlayerPicker.vue'
import AdminView from './AdminView.vue'
import LoginView from './LoginView.vue'

const params = new URLSearchParams(location.search)
const TABS = ['picks', 'stats', 'league', 'admin']
const tab = ref(TABS.includes(params.get('tab')) ? params.get('tab') : 'picks')
const user = ref(null)
const checked = ref(false)
const week = ref(null)
const currentWeek = ref(null)
const summaries = ref([])
const statsRefresh = ref(0)     // bumped as live scores come in: the stats page reloads in place
const players = ref([])
const viewing = ref(null)       // player opened from the league table
const statsPlayer = ref(null)   // whose season the stats tab shows (null: yours)
const announcement = ref('')

// admins can switch admin mode off to see (and use) the site exactly as a regular player does
const adminMode = ref((() => { try { return localStorage.getItem('adminMode') !== 'off' } catch { return true } })())
watch(adminMode, v => { try { localStorage.setItem('adminMode', v ? 'on' : 'off') } catch {} })
const asAdmin = computed(() => !!user.value?.isAdmin && adminMode.value)

// test live mode (admins): fake live scores everywhere, only for you. Reload so every view refetches.
const demoLive = ref(isDemoLive())
function toggleDemo(on) { setDemoLive(on); location.reload() }
watch(asAdmin, on => { if (!on && user.value && demoLive.value) toggleDemo(false) })

async function refreshSummaries() {
  try { summaries.value = await getWeeks() } catch { /* API offline: pills just show no scores */ }
  statsRefresh.value++
}

async function start() {
  try {
    currentWeek.value = (await getLines()).week
  } catch { /* handled inside the picks view */ }
  week.value = week.value || Number(params.get('week')) || currentWeek.value || 1
  refreshSummaries()
  refreshPlayers()
  getAnnouncement().then(a => (announcement.value = a.text)).catch(() => {})
}

function onLogin(u) {
  user.value = u
  start()
}
const onLoggedOut = () => { user.value = null }

// reloaded whenever a tab that lists players opens, so hiding/deleting an account shows up right away
async function refreshPlayers() {
  try { players.value = await getPlayers() } catch { return }
  const ids = new Set(players.value.map(p => p.id))
  if (statsPlayer.value && !ids.has(statsPlayer.value)) statsPlayer.value = null   // back to you
  if (viewing.value && !ids.has(viewing.value)) viewing.value = null              // back to the league table
}
watch(tab, t => { if (user.value && (t === 'stats' || t === 'league')) refreshPlayers() })

function openTab(t) {
  if (t === 'league' && tab.value === 'league') viewing.value = null  // tapping the tab again goes back to the table
  tab.value = t
}
function editMine(w) { week.value = w; viewing.value = null; tab.value = 'picks' }
const me = computed(() => players.value.find(p => p.me))
const statsFor = computed(() => statsPlayer.value ?? me.value?.id ?? null)

onMounted(async () => {
  window.addEventListener('pool:logged-out', onLoggedOut)
  try { user.value = await getMe() } catch { /* not logged in */ }
  checked.value = true
  if (user.value) start()
})
onUnmounted(() => window.removeEventListener('pool:logged-out', onLoggedOut))
watch(asAdmin, on => { if (!on && user.value && tab.value === 'admin') tab.value = 'picks' }, { immediate: true })
</script>

<template>
  <template v-if="checked">
    <LoginView v-if="!user" @done="onLogin" />

    <div v-else class="page">
      <header class="top">
        <div>
          <h1>🏈 Pool Picks</h1>
          <p class="sub">2026 season</p>
        </div>
        <div class="topright">
          <button v-if="user.isAdmin" :class="['modeswitch', { on: adminMode }]" role="switch" :aria-checked="adminMode"
                  :title="adminMode ? 'Turn off to see the site as a regular player' : 'Turn on admin tools'" @click="adminMode = !adminMode">
            <span class="knob"></span>Admin mode
          </button>
          <AccountMenu :user="user" :admin-mode="asAdmin" :demo-live="demoLive" @logout="onLoggedOut" @demo="toggleDemo" />
        </div>
      </header>
      <div class="tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'picks'" :class="{ on: tab === 'picks' }" @click="openTab('picks')">Picks</button>
        <button role="tab" :aria-selected="tab === 'stats'" :class="{ on: tab === 'stats' }" @click="openTab('stats')">Season stats</button>
        <button role="tab" :aria-selected="tab === 'league'" :class="{ on: tab === 'league' }" @click="openTab('league')">League</button>
        <button v-if="asAdmin" role="tab" :aria-selected="tab === 'admin'" :class="{ on: tab === 'admin' }" @click="openTab('admin')">Admin</button>
      </div>

      <p v-if="demoLive && asAdmin" class="demobar">
        <span><b>🧪 Test live mode</b> Scores are fake and only you see them. Other players’ picks on games that haven’t really started are made up. Live games move every 30s.</span>
        <button class="btn sm" @click="toggleDemo(false)">Turn off</button>
      </p>
      <p v-if="announcement" class="announce">📣 {{ announcement }}</p>
      <Countdown />

      <template v-if="week">
        <div v-show="tab === 'picks'">
          <WeekBar v-model="week" :current-week="currentWeek" :summaries="summaries" />
          <PicksView :key="`${week}-${asAdmin}`" :week="week" :current-week="currentWeek" :is-admin="asAdmin" @saved="refreshSummaries" @scored="refreshSummaries" />
        </div>
        <template v-if="tab === 'league'">
          <PlayerView v-if="viewing" v-model:player-id="viewing" :players="players" :current-week="currentWeek" :week="week"
                      @back="viewing = null" @mine="editMine" />
          <StandingsView v-else :current-week="currentWeek" @open="viewing = $event" />
        </template>
        <template v-if="tab === 'stats'">
          <div v-if="players.length > 1" class="statsfor">
            <PlayerPicker :model-value="statsFor" :players="players" @update:model-value="statsPlayer = $event" />
          </div>
          <StatsView :user-id="statsFor" :mine="!statsPlayer || statsPlayer === me?.id" :refresh="statsRefresh" />
        </template>
        <AdminView v-if="tab === 'admin' && asAdmin" :me="user" :current-week="currentWeek || week" @announcement="announcement = $event" />
      </template>
    </div>
  </template>
</template>
