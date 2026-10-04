<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { getLines, getWeeks, getMe, getAnnouncement } from './api.js'
import WeekBar from './components/WeekBar.vue'
import Countdown from './components/Countdown.vue'
import AccountMenu from './components/AccountMenu.vue'
import PicksView from './PicksView.vue'
import StatsView from './StatsView.vue'
import AdminView from './AdminView.vue'
import LoginView from './LoginView.vue'

const params = new URLSearchParams(location.search)
const TABS = ['picks', 'stats', 'admin']
const tab = ref(TABS.includes(params.get('tab')) ? params.get('tab') : 'picks')
const user = ref(null)
const checked = ref(false)
const week = ref(null)
const currentWeek = ref(null)
const summaries = ref([])
const statsKey = ref(0)
const announcement = ref('')

async function refreshSummaries() {
  try { summaries.value = await getWeeks() } catch { /* API offline: pills just show no scores */ }
  statsKey.value++
}

async function start() {
  try {
    currentWeek.value = (await getLines()).week
  } catch { /* handled inside the picks view */ }
  week.value = week.value || Number(params.get('week')) || currentWeek.value || 1
  refreshSummaries()
  getAnnouncement().then(a => (announcement.value = a.text)).catch(() => {})
}

function onLogin(u) {
  user.value = u
  start()
}
const onLoggedOut = () => { user.value = null }

onMounted(async () => {
  window.addEventListener('pool:logged-out', onLoggedOut)
  try { user.value = await getMe() } catch { /* not logged in */ }
  checked.value = true
  if (user.value) start()
})
onUnmounted(() => window.removeEventListener('pool:logged-out', onLoggedOut))
watch(user, u => { if (u && !u.isAdmin && tab.value === 'admin') tab.value = 'picks' })
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
        <AccountMenu :user="user" @logout="onLoggedOut" />
      </header>
      <div class="tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'picks'" :class="{ on: tab === 'picks' }" @click="tab = 'picks'">Picks</button>
        <button role="tab" :aria-selected="tab === 'stats'" :class="{ on: tab === 'stats' }" @click="tab = 'stats'">Season stats</button>
        <button v-if="user.isAdmin" role="tab" :aria-selected="tab === 'admin'" :class="{ on: tab === 'admin' }" @click="tab = 'admin'">Admin</button>
      </div>

      <p v-if="announcement" class="announce">📣 {{ announcement }}</p>
      <Countdown />

      <template v-if="week">
        <div v-show="tab === 'picks'">
          <WeekBar v-model="week" :current-week="currentWeek" :summaries="summaries" />
          <PicksView :key="week" :week="week" :current-week="currentWeek" :is-admin="user.isAdmin" @saved="refreshSummaries" />
        </div>
        <StatsView v-if="tab === 'stats'" :key="statsKey" />
        <AdminView v-if="tab === 'admin' && user.isAdmin" :me="user" :current-week="currentWeek || week" @announcement="announcement = $event" />
      </template>
    </div>
  </template>
</template>
