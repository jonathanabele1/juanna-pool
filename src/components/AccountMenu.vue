<script setup>
import { ref } from 'vue'
import { changePassword, logout } from '../api.js'

defineProps({ user: Object, adminMode: Boolean })
const emit = defineEmits(['logout'])

const open = ref(false)
const pwOpen = ref(false)
const current = ref('')
const next = ref('')
const msg = ref('')
const err = ref('')

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
  <div class="acct">
    <button class="btn ghost who" @click="open = !open" :aria-expanded="open">
      {{ user.displayName }}<span v-if="adminMode" class="adm">admin</span> ▾
    </button>
    <div v-if="open" class="menu">
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
  </div>
</template>

<style scoped>
.acct { position: relative; }
.who { display: flex; align-items: center; gap: 6px; }
.adm { font-size: .65rem; text-transform: uppercase; letter-spacing: .06em; background: #0f172a; color: #fff; padding: 2px 6px; border-radius: 6px; }
.menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 40; width: 250px; background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; box-shadow: 0 12px 30px #0f172a1f; padding: 6px; display: flex; flex-direction: column; }
.item { text-align: left; border: 0; background: none; padding: 9px 10px; border-radius: 9px; cursor: pointer; color: #334155; }
.item:hover { background: #f1f5f9; }
.pw { display: flex; flex-direction: column; gap: 6px; padding: 4px 10px 10px; }
.pw input { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 9px; }
.ok { margin: 0; color: #15803d; font-size: .8rem; }
.err { margin: 0; color: #b91c1c; font-size: .8rem; }
</style>
