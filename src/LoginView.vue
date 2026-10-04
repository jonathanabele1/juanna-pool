<script setup>
import { ref, computed, onMounted } from 'vue'
import { login, signup, getSignupInfo } from './api.js'

const emit = defineEmits(['done'])
const mode = ref('login')        // login | signup
const info = ref({ open: false, needsCode: false })
const username = ref('')
const password = ref('')
const confirm = ref('')
const code = ref('')
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  try { info.value = await getSignupInfo() } catch { /* sign-up link just stays hidden */ }
})

const isSignup = computed(() => mode.value === 'signup')
function switchMode(m) { mode.value = m; error.value = '' }

async function submit() {
  error.value = ''
  if (isSignup.value && password.value !== confirm.value) {
    error.value = "Passwords don't match"
    return
  }
  busy.value = true
  try {
    emit('done', isSignup.value
      ? await signup({ username: username.value, password: password.value, code: code.value })
      : await login(username.value, password.value))
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
      <p class="sub">{{ isSignup ? 'Create your account.' : 'Log in to make your picks.' }}</p>
      <label>{{ isSignup ? 'Username (your pool team name works well)' : 'Username' }}
        <input v-model="username" autocomplete="username" autocapitalize="none" required autofocus />
      </label>
      <label>Password
        <input v-model="password" type="password" :autocomplete="isSignup ? 'new-password' : 'current-password'" required :minlength="isSignup ? 6 : null" />
      </label>
      <template v-if="isSignup">
        <label>Confirm password <input v-model="confirm" type="password" autocomplete="new-password" required /></label>
        <label v-if="info.needsCode">Join code <small>(ask the pool admin)</small>
          <input v-model="code" autocapitalize="none" required />
        </label>
      </template>
      <p v-if="error" class="err">{{ error }}</p>
      <button class="btn primary big" :disabled="busy">
        {{ busy ? (isSignup ? 'Creating…' : 'Logging in…') : (isSignup ? 'Create account' : 'Log in') }}
      </button>
      <p v-if="isSignup" class="hint">Already have an account? <button type="button" class="link" @click="switchMode('login')">Log in</button></p>
      <p v-else-if="info.open" class="hint">New here? <button type="button" class="link" @click="switchMode('signup')">Create an account</button></p>
      <p v-else class="hint">No account? Ask the pool admin to set one up for you.</p>
    </form>
  </div>
</template>

<style scoped>
.loginwrap { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.login { width: min(380px, 100%); background: #fff; border-radius: 20px; padding: 26px 22px; box-shadow: 0 10px 40px #0f172a14; display: flex; flex-direction: column; gap: 12px; }
h1 { margin: 0; font-size: 1.5rem; }
.sub { margin: -6px 0 6px; color: #64748b; }
label { display: flex; flex-direction: column; gap: 4px; font-size: .85rem; font-weight: 600; color: #334155; }
label small { font-weight: 400; color: #94a3b8; }
input { padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 1rem; }
input:focus { outline: 2px solid #2563eb; border-color: transparent; }
.err { margin: 0; color: #b91c1c; font-size: .85rem; }
.hint { margin: 0; color: #64748b; font-size: .85rem; text-align: center; }
.link { border: 0; background: none; color: #2563eb; font-weight: 600; cursor: pointer; padding: 0; }
</style>
