<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getLines, getWeeks, getMe, getAnnouncement, getPlayers, getPlayerWeeks, isDemoLive, setDemoLive } from './api.js'
import { mailPrefs } from './mailPrefs.js'
import WeekBar from './components/WeekBar.vue'
import AccountMenu from './components/AccountMenu.vue'
import ViewingMenu from './components/ViewingMenu.vue'
import PicksView from './PicksView.vue'
import PlayerWeek from './PlayerWeek.vue'
import StatsView from './StatsView.vue'
import StandingsView from './StandingsView.vue'
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
const viewing = ref(null)       // whose picks and season the Picks and Season stats tabs show (null: yours)
const theirSummaries = ref([])  // the week bar's scores while viewing someone else
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
  if (viewing.value && !ids.has(viewing.value)) viewing.value = null   // hidden or deleted: back to you
}
watch(tab, t => { if (user.value && (t === 'stats' || t === 'league')) refreshPlayers() })

const openTab = t => { tab.value = t }

// ---- viewing: you, or another player (the switcher in the header, or a tap on the League tab) ----
// your own team name comes from your email settings, so a change there shows right away
const me = computed(() => {
  const p = players.value.find(x => x.me)
  return p ? { ...p, teamName: mailPrefs.teamName || p.teamName } : null
})
const other = computed(() => players.value.find(p => p.id === viewing.value && !p.me) || null)
const shown = computed(() => other.value || me.value)

function view(id) {
  viewing.value = id === me.value?.id ? null : id
  if (tab.value !== 'stats') tab.value = 'picks'   // from League or Admin: straight to their picks
}
// League: tap a player for their picks (that week's, from the week table)
function openPlayer(id, w) {
  if (w) week.value = w
  view(id)
  tab.value = 'picks'
  window.scrollTo({ top: 0 })
}
async function refreshTheirs() {
  const id = viewing.value
  if (!id) return
  try {
    const s = await getPlayerWeeks(id)
    if (id === viewing.value) theirSummaries.value = s
  } catch { theirSummaries.value = [] }
  statsRefresh.value++
}
watch(() => other.value?.id, () => { theirSummaries.value = []; refreshTheirs() })

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
          <ViewingMenu v-if="players.length > 1" :model-value="shown?.id" :players="players" @update:model-value="view" />
          <AccountMenu :user="user" :admin-mode="asAdmin" :demo-live="demoLive" @logout="onLoggedOut" @demo="toggleDemo" @admin="adminMode = $event" />
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

      <template v-if="week">
        <!-- yours stays mounted while you look at someone else, so unsaved edits are still there when you come back -->
        <div v-show="tab === 'picks'">
          <WeekBar v-model="week" :current-week="currentWeek" :summaries="other ? theirSummaries : summaries" />
          <PlayerWeek v-if="other" :key="`${other.id}-${week}`" :player="other" :week="week" @scored="refreshTheirs" @mine="viewing = null" />
          <div v-show="!other">
            <PicksView :key="`${week}-${asAdmin}`" :week="week" :current-week="currentWeek" :is-admin="asAdmin" @saved="refreshSummaries" @scored="refreshSummaries" />
          </div>
        </div>
        <StandingsView v-if="tab === 'league'" :current-week="currentWeek" @open="openPlayer" />
        <StatsView v-if="tab === 'stats'" :user-id="shown?.id" :mine="!other" :player="shown" :refresh="statsRefresh" @mine="viewing = null" />
        <AdminView v-if="tab === 'admin' && asAdmin" :me="user" :current-week="currentWeek || week" @announcement="announcement = $event" />
      </template>
    </div>
  </template>
</template>
