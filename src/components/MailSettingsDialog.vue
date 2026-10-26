<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { MAIL_APPS, platform } from '../mail.js'
import { mailPrefs, saveMailPrefs } from '../mailPrefs.js'

// sending: opened by the first tap on Send picks (it opens the email right after saving)
const props = defineProps({ sending: Boolean })
const emit = defineEmits(['close', 'saved'])

const desktop = platform() === 'desktop'
const choice = ref(MAIL_APPS.some(a => a.id === mailPrefs.app) ? mailPrefs.app : '')
const address = ref(mailPrefs.sender)
const teamName = ref(mailPrefs.teamName)
const error = ref('')
const msg = ref('')
// desktop Gmail opens whichever Google account is first in the browser unless it knows which one to use
const askSender = computed(() => desktop && choice.value === 'gmail')

const onKey = e => e.key === 'Escape' && emit('close')
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function save() {
  error.value = ''; msg.value = ''
  const sender = askSender.value ? address.value.trim() : mailPrefs.sender
  if (sender && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(sender)) { error.value = 'That doesn’t look like an email address.'; return }
  const prefs = { app: choice.value, sender, teamName: teamName.value.trim() }
  const saving = saveMailPrefs(prefs)
  if (props.sending) {
    // the email has to open straight from the tap (after an await a new tab would be blocked)
    saving.catch(() => { /* kept for this visit; asks again next time */ })
    emit('saved', prefs)
    return
  }
  saving.then(() => { msg.value = 'Saved'; setTimeout(() => emit('close'), 600) }).catch(e => { error.value = e.message })
}
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <form class="dialog" role="dialog" aria-modal="true" aria-label="Email settings" @submit.prevent="save">
      <header>
        <h3>{{ sending ? 'Send your picks with…' : 'Email settings' }}</h3>
        <button type="button" class="x" aria-label="Close" @click="$emit('close')">✕</button>
      </header>
      <p class="sub">
        Send picks opens a new email from your own account to that week’s league address, ready to send.
        <template v-if="sending">You can change this later from your name at the top.</template>
      </p>

      <div class="apps" role="radiogroup" aria-label="Email app">
        <label v-for="a in MAIL_APPS" :key="a.id" :class="['app', { on: choice === a.id }]">
          <input type="radio" name="mailapp" :value="a.id" v-model="choice" />
          <span><b>{{ a.label }}</b><small v-if="a.note">{{ a.note }}</small></span>
        </label>
      </div>
      <p v-if="!desktop && choice && choice !== 'default'" class="note">Needs the {{ choice === 'gmail' ? 'Gmail' : 'Outlook' }} app. If it isn’t installed, the website opens instead.</p>

      <label v-if="askSender" class="field">
        Your Gmail address <small>(optional: opens the right account if you use more than one)</small>
        <input v-model="address" type="email" inputmode="email" autocapitalize="none" placeholder="you@gmail.com" />
      </label>
      <label class="field">
        Team name <small>(goes in the email)</small>
        <input v-model="teamName" maxlength="60" placeholder="Your pool team name" />
      </label>
      <p v-if="error" class="err">{{ error }}</p>

      <footer>
        <small v-if="msg" class="ok">{{ msg }}</small>
        <button type="button" class="btn ghost" @click="$emit('close')">Cancel</button>
        <button class="btn primary" :disabled="!choice">{{ sending ? 'Open email' : 'Save' }}</button>
      </footer>
    </form>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; z-index: 50; display: grid; place-items: center; padding: 16px; background: #0f172a8c; backdrop-filter: blur(3px); }
.dialog { width: min(440px, 100%); max-height: calc(100dvh - 32px); overflow-y: auto; background: var(--card); border-radius: 20px; padding: 18px; box-shadow: 0 20px 60px #0006; display: flex; flex-direction: column; gap: 12px; }
header { display: flex; justify-content: space-between; align-items: center; }
h3 { margin: 0; font-size: 1.05rem; }
.x { border: 0; background: var(--soft); width: 30px; height: 30px; border-radius: 50%; cursor: pointer; color: var(--text-2); }
.x:hover { background: var(--chip); }
.sub { margin: 0; font-size: .85rem; color: var(--muted); }
.apps { display: flex; flex-direction: column; gap: 8px; }
.app { display: flex; align-items: center; gap: 10px; padding: 12px; border: 1.5px solid var(--line); border-radius: 14px; cursor: pointer; }
.app.on { border-color: #2563eb; background: var(--blue-tint); }
.app input { width: 18px; height: 18px; accent-color: var(--blue); margin: 0; }
.app span { display: flex; flex-direction: column; gap: 1px; }
.app small { color: var(--muted); font-size: .78rem; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: .78rem; font-weight: 600; color: var(--muted); }
.field small { font-weight: 400; }
.field input { padding: 10px 11px; border: 1px solid var(--line); border-radius: 10px; font-size: 1rem; color: var(--text); }
.note { margin: 0; font-size: .78rem; color: var(--faint); }
.err { margin: 0; font-size: .85rem; color: var(--neg); }
.ok { color: var(--pos); margin-right: auto; align-self: center; }
footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
