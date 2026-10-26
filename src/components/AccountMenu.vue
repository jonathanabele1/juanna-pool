<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { changePassword, logout } from '../api.js'
import { MAIL_APPS } from '../mail.js'
import { mailPrefs, loadMailPrefs } from '../mailPrefs.js'
import { THEMES, theme } from '../theme.js'
import MailSettingsDialog from './MailSettingsDialog.vue'

defineProps({ user: Object, adminMode: Boolean, demoLive: Boolean })
const emit = defineEmits(['logout', 'demo', 'admin'])

const open = ref(false)
const pwOpen = ref(false)
const current = ref('')
const next = ref('')
const msg = ref('')
const err = ref('')
const mailOpen = ref(false)
const root = ref(null)
// tap anywhere outside closes the menu
const onDocTap = e => { if (open.value && !root.value?.contains(e.target)) open.value = false }
onMounted(() => { document.addEventListener('pointerdown', onDocTap); loadMailPrefs() })
onUnmounted(() => document.removeEventListener('pointerdown', onDocTap))
const mailLabel = () => MAIL_APPS.find(a => a.id === mailPrefs.app)?.label || 'Not set'

async function savePassword() {
  msg.value = ''; err.value = ''
  try {
    await changePassword(current.value, next.value)
    msg.value = 'Password changed.'
    current.value = ''; next.value = ''
  } catch (e) { err.value = e.message }
}
async function doLogout() {
  await logout().catch(() => {})
  emit('logout')
}
</script>

<template>
  <div ref="root" class="acct">
    <button :class="['who', { on: open }]" @click="open = !open; loadMailPrefs()" :aria-expanded="open" aria-label="Account">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="3.75" /><path d="M4.75 19.5c1.2-3.4 4-5 7.25-5s6.05 1.6 7.25 5" /></svg>
      <i v-if="adminMode" class="admdot" title="Admin mode"></i>
    </button>
    <div v-if="open" class="menu">
      <div class="ident">
        <b>{{ mailPrefs.teamName || user.displayName }}</b>
        <small v-if="mailPrefs.teamName || adminMode">{{ [mailPrefs.teamName && user.displayName, adminMode && 'admin'].filter(Boolean).join(' · ') }}</small>
      </div>
      <button v-if="user.isAdmin" class="item demo" role="switch" :aria-checked="adminMode" @click="emit('admin', !adminMode)">
        <span>Admin mode<small>Off: see it as a player</small></span>
        <b :class="{ on: adminMode }">{{ adminMode ? 'On' : 'Off' }}</b>
      </button>
      <button v-if="adminMode" class="item demo" role="switch" :aria-checked="demoLive" @click="emit('demo', !demoLive); open = false">
        <span>🧪 Test live mode<small>Fake scores, only you see them</small></span>
        <b :class="{ on: demoLive }">{{ demoLive ? 'On' : 'Off' }}</b>
      </button>
      <div class="item theme">
        <span>Theme</span>
        <div class="seg3" role="radiogroup" aria-label="Appearance">
          <button v-for="t in THEMES" :key="t.id" type="button" role="radio" :aria-checked="theme === t.id"
                  :class="{ on: theme === t.id }" @click="theme = t.id">{{ t.label }}</button>
        </div>
      </div>
      <button class="item mail" @click="mailOpen = true; open = false">
        <span>✉ Email settings<small>Send picks with: {{ mailLabel() }}</small></span>
      </button>
      <button class="item" @click="pwOpen = !pwOpen">Change password</button>
      <form v-if="pwOpen" class="pw" @submit.prevent="savePassword">
        <input v-model="current" type="password" placeholder="Current password" autocomplete="current-password" required />
        <input v-model="next" type="password" placeholder="New password (6+ characters)" autocomplete="new-password" required minlength="6" />
        <button class="btn primary sm">Save</button>
        <p v-if="msg" class="ok">{{ msg }}</p>
        <p v-if="err" class="err">{{ err }}</p>
      </form>
      <button class="item" @click="doLogout">Log out</button>
    </div>
    <MailSettingsDialog v-if="mailOpen" @close="mailOpen = false" />
  </div>
</template>

<style scoped>
.acct { position: relative; }
.who { position: relative; width: 40px; height: 40px; display: grid; place-items: center; padding: 0; border: 1px solid var(--line); border-radius: 50%; background: var(--card); color: var(--text-2); cursor: pointer; transition: background .15s, border-color .15s; }
.who:hover, .who.on { background: var(--soft); border-color: var(--line-strong); }
.who:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }
.who svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; }
.admdot { position: absolute; top: 1px; right: 1px; width: 10px; height: 10px; border-radius: 50%; background: var(--ink); border: 2px solid var(--card); }
.ident { display: flex; flex-direction: column; gap: 1px; padding: 8px 10px 10px; margin-bottom: 4px; border-bottom: 1px solid var(--line-soft); min-width: 0; }
.ident b { font-size: .95rem; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ident small { font-size: .74rem; color: var(--faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 40; width: min(260px, calc(100vw - 28px)); background: var(--card); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 12px 30px #0f172a1f; padding: 6px; display: flex; flex-direction: column; }
.item { text-align: left; border: 0; background: none; padding: 9px 10px; border-radius: 9px; cursor: pointer; color: var(--text-2); }
.item:hover { background: var(--soft); }
.item.demo { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.item.demo span, .item.mail span { display: flex; flex-direction: column; }
.item.demo small, .item.mail small { font-size: .72rem; color: var(--faint); }
.item.demo b { font-size: .7rem; padding: 2px 8px; border-radius: 99px; background: var(--soft); color: var(--muted); }
.item.demo b.on { background: var(--ink); color: var(--on-ink); }
.item.demo + .item.demo b.on { background: #7c3aed; }
.item.theme { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 10px; cursor: default; }
.item.theme:hover { background: none; }
.seg3 { display: inline-flex; gap: 2px; padding: 2px; border-radius: 9px; background: var(--chip); }
.seg3 button { border: 0; background: none; padding: 4px 8px; border-radius: 7px; font-size: .74rem; font-weight: 700; color: var(--muted); cursor: pointer; }
.seg3 button.on { background: var(--raised); color: var(--text); box-shadow: 0 1px 2px #0000001f; }
.seg3 button:focus-visible { outline: 2px solid #93c5fd; outline-offset: 1px; }
.pw { display: flex; flex-direction: column; gap: 6px; padding: 4px 10px 10px; }
.pw input { padding: 8px 10px; border: 1px solid var(--line-strong); border-radius: 9px; }
.ok { margin: 0; color: var(--pos); font-size: .8rem; }
.err { margin: 0; color: var(--neg); font-size: .8rem; }
</style>
