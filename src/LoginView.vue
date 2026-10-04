<script setup>
import { ref } from 'vue'
import { login } from './api.js'

const emit = defineEmits(['done'])
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    emit('done', await login(username.value, password.value))
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="loginwrap">
    <form class="login" @submit.prevent="submit">
      <h1>🏈 Pool Picks</h1>
      <p class="sub">Log in to make your picks.</p>
      <label>Username <input v-model="username" autocomplete="username" autocapitalize="none" required autofocus /></label>
      <label>Password <input v-model="password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="err">{{ error }}</p>
      <button class="btn primary big" :disabled="busy">{{ busy ? 'Logging in…' : 'Log in' }}</button>
      <p class="hint">No account? Ask the pool admin to set one up for you.</p>
    </form>
  </div>
</template>

<style scoped>
.loginwrap { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.login { width: min(380px, 100%); background: #fff; border-radius: 20px; padding: 26px 22px; box-shadow: 0 10px 40px #0f172a14; display: flex; flex-direction: column; gap: 12px; }
h1 { margin: 0; font-size: 1.5rem; }
.sub { margin: -6px 0 6px; color: #64748b; }
label { display: flex; flex-direction: column; gap: 4px; font-size: .85rem; font-weight: 600; color: #334155; }
input { padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 1rem; }
input:focus { outline: 2px solid #2563eb; border-color: transparent; }
.err { margin: 0; color: #b91c1c; font-size: .85rem; }
.hint { margin: 0; color: #94a3b8; font-size: .8rem; text-align: center; }
</style>
