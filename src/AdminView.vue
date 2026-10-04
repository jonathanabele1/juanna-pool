<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { admin, getAnnouncement } from './api.js'

const props = defineProps({ me: Object, currentWeek: Number })
const emit = defineEmits(['announcement'])

const fmt = iso => new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
const toInput = iso => { const d = new Date(iso); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
const flash = (obj, key, text) => { obj[key] = text; setTimeout(() => { if (obj[key] === text) obj[key] = '' }, 2500) }

// ---------------- week ----------------
const week = ref(props.currentWeek || 1)
const wk = ref(null)
const wkError = ref('')
const rows = ref([])            // editable copy of each player's adjustment/unlock
const dlEdit = reactive({})     // group id -> datetime-local value
const notes = reactive({})
const confirmLines = ref(false)

async function loadWeek() {
  wkError.value = ''
  try {
    const w = await admin.week(week.value)
    wk.value = w
    rows.value = w.players.map(p => ({ ...p, edit: { adjustment: p.adjustment, adjNote: p.adjNote } }))
    for (const g of w.deadlines) dlEdit[g.id] = toInput(g.deadline)
  } catch (e) { wkError.value = e.message }
}
watch(week, () => { confirmLines.value = false; if (week.value >= 1 && week.value <= 22) loadWeek() })

async function saveDeadline(g, reset = false) {
  try {
    const groups = await admin.setDeadlines(week.value, { [g.id]: reset ? null : new Date(dlEdit[g.id]).toISOString() })
    wk.value.deadlines = groups
    for (const x of groups) dlEdit[x.id] = toInput(x.deadline)
    flash(notes, `dl-${g.id}`, reset ? 'Back to automatic' : 'Saved')
  } catch (e) { flash(notes, `dl-${g.id}`, e.message) }
}

async function savePlayer(r) {
  try {
    await admin.setPick(r.user.id, week.value, { ...r.edit, adjustment: Math.round(Number(r.edit.adjustment) || 0) })
    flash(notes, `p-${r.user.id}`, 'Saved')
    loadWeek()
  } catch (e) { flash(notes, `p-${r.user.id}`, e.message) }
}

async function deleteLines() {
  await admin.deleteLines(week.value)
  confirmLines.value = false
  loadWeek()
}

// ---------------- accounts ----------------
const users = ref([])
const nu = reactive({ username: '', displayName: '', password: '', isAdmin: false })
const nuMsg = ref('')
const nuErr = ref('')
const resetFor = ref(null)
const resetPw = ref('')

const loadUsers = async () => { users.value = await admin.users() }

const signupCfg = reactive({ open: true, code: '' })
async function saveSignup() {
  try {
    Object.assign(signupCfg, await admin.setSignup({ ...signupCfg }))
    flash(notes, 'signup', 'Saved')
  } catch (e) { flash(notes, 'signup', e.message) }
}
function randomPassword() {
  const words = ['blitz', 'punt', 'spiral', 'huddle', 'sack', 'snap', 'redzone', 'endzone', 'gridiron', 'kickoff']
  nu.password = `${words[Math.floor(Math.random() * words.length)]}${Math.floor(100 + Math.random() * 900)}`
}
async function addUser() {
  nuErr.value = ''; nuMsg.value = ''
  try {
    const u = await admin.createUser({ ...nu })
    nuMsg.value = `Created ${u.username}. Send them: username “${u.username}”, password “${nu.password}”.`
    Object.assign(nu, { username: '', displayName: '', password: '', isAdmin: false })
    loadUsers(); loadWeek()
  } catch (e) { nuErr.value = e.message }
}
async function patchUser(u, body, msg) {
  try {
    await admin.updateUser(u.id, body)
    flash(notes, `u-${u.id}`, msg)
    loadUsers()
  } catch (e) { flash(notes, `u-${u.id}`, e.message) }
}
async function doReset(u) {
  await patchUser(u, { password: resetPw.value }, `New password: ${resetPw.value}`)
  resetFor.value = null; resetPw.value = ''
}

// ---------------- announcement + backup ----------------
const announcement = ref('')
async function saveAnnouncement() {
  const r = await admin.setAnnouncement(announcement.value)
  emit('announcement', r.text)
  flash(notes, 'ann', r.text ? 'Posted' : 'Cleared')
}

const restoreFile = ref(null)
const restoreConfirm = ref(false)
const restoreMsg = ref('')
async function doRestore() {
  restoreMsg.value = 'Restoring…'
  try {
    await admin.restore(restoreFile.value)
    restoreMsg.value = 'Restored. Reloading…'
    setTimeout(() => location.reload(), 800)
  } catch (e) { restoreMsg.value = e.message }
}

onMounted(() => {
  loadWeek()
  loadUsers()
  admin.signup().then(c => Object.assign(signupCfg, c)).catch(() => {})
  getAnnouncement().then(a => (announcement.value = a.text)).catch(() => {})
})
</script>

<template>
  <div class="admin">
    <!-- ============ WEEK ============ -->
    <section class="card">
      <div class="head">
        <h3>Week</h3>
        <div class="weekpick">
          <button class="btn ghost sm" :disabled="week <= 1" @click="week--">‹</button>
          <input type="number" v-model.number="week" min="1" max="22" aria-label="Week" />
          <button class="btn ghost sm" :disabled="week >= 22" @click="week++">›</button>
        </div>
      </div>
      <p v-if="wkError" class="err">{{ wkError }}</p>
      <template v-else-if="wk">
        <p class="muted">
          <template v-if="wk.games">{{ wk.games }} games on the sheet{{ wk.hasImage ? ' · image uploaded' : '' }}.</template>
          <template v-else>No lines posted yet.</template>
          Upload or edit lines on the <b>Picks</b> tab. Saving there posts them for everyone.
        </p>

        <h4>Pick deadlines</h4>
        <p v-if="!wk.deadlines.length" class="muted">No schedule for this week (ESPN unreachable?).</p>
        <div v-for="g in wk.deadlines" :key="g.id" class="dl">
          <div class="dl-what">
            <b>{{ g.label }}</b> <small>{{ g.games }} game{{ g.games > 1 ? 's' : '' }}</small>
            <span :class="['when', { ov: g.overridden }]">{{ fmt(g.deadline) }}<template v-if="g.overridden"> · custom (auto: {{ fmt(g.auto) }})</template></span>
          </div>
          <div class="dl-edit">
            <input type="datetime-local" v-model="dlEdit[g.id]" />
            <button class="btn ghost sm" @click="saveDeadline(g)">Set</button>
            <button v-if="g.overridden" class="btn ghost sm" @click="saveDeadline(g, true)">Use automatic</button>
            <small class="note">{{ notes[`dl-${g.id}`] }}</small>
          </div>
        </div>

        <h4>Players</h4>
        <div class="tablewrap">
          <table>
            <thead><tr><th>Player</th><th>Picks</th><th>Score</th><th>Adjustment</th><th>Note</th><th></th></tr></thead>
            <tbody>
              <tr v-for="r in rows" :key="r.user.id" :class="{ inactive: !r.user.active }">
                <td>{{ r.user.displayName }}</td>
                <td>
                  <span v-if="r.saved" :class="['tot', { bad: r.total !== 100 }]">{{ r.total }}/100</span>
                  <span v-else class="muted">—</span>
                </td>
                <td>{{ r.score ?? '—' }}</td>
                <td><input class="num" type="number" v-model.number="r.edit.adjustment" /></td>
                <td><input class="txt" v-model="r.edit.adjNote" placeholder="e.g. late (−10)" /></td>
                <td><button class="btn ghost sm" @click="savePlayer(r)">Save</button> <small class="note">{{ notes[`p-${r.user.id}`] }}</small></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="wk.games || wk.hasImage" class="danger">
          <button v-if="!confirmLines" class="btn ghost danger sm" @click="confirmLines = true">Remove week {{ week }} lines &amp; sheet…</button>
          <template v-else>
            <span>Remove the lines and sheet image for <b>everyone</b>? Saved picks are kept in case you re-upload.</span>
            <button class="btn danger-solid sm" @click="deleteLines">Remove</button>
            <button class="btn ghost sm" @click="confirmLines = false">Cancel</button>
          </template>
        </div>
      </template>
    </section>

    <!-- ============ ACCOUNTS ============ -->
    <section class="card">
      <h3>Accounts</h3>
      <div class="signup">
        <label class="chk"><input type="checkbox" v-model="signupCfg.open" /> Players can create their own accounts</label>
        <label v-if="signupCfg.open" class="code">Join code <input v-model="signupCfg.code" placeholder="optional, e.g. blitz26" /></label>
        <button class="btn ghost sm" @click="saveSignup">Save</button>
        <small class="note">{{ notes.signup }}</small>
      </div>
      <p class="muted">
        <template v-if="!signupCfg.open">Sign-ups are closed, so add players below.</template>
        <template v-else-if="signupCfg.code">New players need the join code to sign up. Send it with the link.</template>
        <template v-else>Anyone with the link can sign up. Add a join code to keep strangers out.</template>
      </p>
      <h4>Add a player yourself</h4>
      <form class="newuser" @submit.prevent="addUser">
        <input v-model="nu.displayName" placeholder="Name (e.g. Mike S.)" />
        <input v-model="nu.username" placeholder="Username" autocapitalize="none" required />
        <div class="pwrow">
          <input v-model="nu.password" placeholder="Temporary password" required minlength="6" />
          <button type="button" class="btn ghost sm" @click="randomPassword">Generate</button>
        </div>
        <label class="chk"><input type="checkbox" v-model="nu.isAdmin" /> Admin</label>
        <button class="btn primary sm">Add player</button>
      </form>
      <p v-if="nuMsg" class="ok">{{ nuMsg }}</p>
      <p v-if="nuErr" class="err">{{ nuErr }}</p>

      <ul class="users">
        <li v-for="u in users" :key="u.id" :class="{ inactive: !u.active }">
          <div class="u-who">
            <b>{{ u.displayName }}</b> <small>@{{ u.username }}</small>
            <span v-if="u.isAdmin" class="tag">admin</span>
            <span v-if="!u.active" class="tag off">deactivated</span>
          </div>
          <div class="u-actions">
            <template v-if="resetFor === u.id">
              <input v-model="resetPw" placeholder="New password" minlength="6" />
              <button class="btn primary sm" :disabled="resetPw.length < 6" @click="doReset(u)">Set</button>
              <button class="btn ghost sm" @click="resetFor = null">Cancel</button>
            </template>
            <template v-else>
              <button class="btn ghost sm" @click="resetFor = u.id; resetPw = ''">Reset password</button>
              <template v-if="u.id !== me.id">
                <button class="btn ghost sm" @click="patchUser(u, { isAdmin: !u.isAdmin }, u.isAdmin ? 'No longer admin' : 'Now an admin')">{{ u.isAdmin ? 'Remove admin' : 'Make admin' }}</button>
                <button class="btn ghost sm" :class="{ danger: u.active }" @click="patchUser(u, { active: !u.active }, u.active ? 'Deactivated' : 'Reactivated')">{{ u.active ? 'Deactivate' : 'Reactivate' }}</button>
              </template>
            </template>
            <small class="note">{{ notes[`u-${u.id}`] }}</small>
          </div>
        </li>
      </ul>
    </section>

    <!-- ============ ANNOUNCEMENT ============ -->
    <section class="card">
      <h3>Announcement</h3>
      <p class="muted">Shown at the top of the site for everyone. Leave blank to hide it.</p>
      <textarea v-model="announcement" rows="2" placeholder="e.g. Thanksgiving picks are due Wednesday at 11 AM"></textarea>
      <div class="row"><button class="btn primary sm" @click="saveAnnouncement">Post</button> <small class="note">{{ notes.ann }}</small></div>
    </section>

    <!-- ============ BACKUP ============ -->
    <section class="card">
      <h3>Backup</h3>
      <p class="muted">Download the whole season (accounts, lines, picks, sheet images) as one file.</p>
      <a class="btn ghost sm" href="/api/admin/backup">⬇ Download backup</a>
      <h4>Restore</h4>
      <p class="muted">Replaces <b>everything</b> on the site with a backup file. Everyone may need to log in again.</p>
      <div class="row">
        <input type="file" accept=".db" @change="restoreFile = $event.target.files[0]; restoreConfirm = false" />
        <button v-if="restoreFile && !restoreConfirm" class="btn ghost danger sm" @click="restoreConfirm = true">Restore…</button>
        <template v-if="restoreConfirm">
          <span>Replace all site data with <b>{{ restoreFile.name }}</b>?</span>
          <button class="btn danger-solid sm" @click="doRestore">Yes, restore</button>
          <button class="btn ghost sm" @click="restoreConfirm = false">Cancel</button>
        </template>
      </div>
      <p v-if="restoreMsg" class="muted">{{ restoreMsg }}</p>
    </section>
  </div>
</template>

<style scoped>
.admin { display: flex; flex-direction: column; gap: 14px; }
.card { background: #fff; border-radius: 18px; padding: 16px; box-shadow: 0 1px 2px #0000000d; }
.head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
h3 { margin: 0 0 8px; font-size: 1.05rem; }
.head h3 { margin: 0; }
h4 { margin: 18px 0 8px; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; color: #64748b; }
.muted { color: #64748b; font-size: .85rem; margin: 6px 0; }
.weekpick { display: flex; align-items: center; gap: 4px; }
.weekpick input { width: 56px; text-align: center; padding: 5px; border: 1px solid #cbd5e1; border-radius: 8px; }
input, textarea { border: 1px solid #cbd5e1; border-radius: 9px; padding: 7px 9px; }
textarea { width: 100%; resize: vertical; }
.dl { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; padding: 10px 0; border-top: 1px solid #f1f5f9; }
.dl-what { display: flex; flex-direction: column; gap: 2px; }
.dl-what small { color: #94a3b8; }
.when { font-size: .85rem; color: #334155; }
.when.ov { color: #b45309; }
.dl-edit { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th { text-align: left; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: #64748b; padding: 6px; }
td { padding: 6px; border-top: 1px solid #f1f5f9; white-space: nowrap; }
td.c { text-align: center; }
.num { width: 64px; }
.txt { width: 150px; }
.tot { font-weight: 700; color: #15803d; }
.tot.bad { color: #b45309; }
tr.inactive, li.inactive { opacity: .55; }
.danger { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px; font-size: .85rem; }
.signup { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.code { display: flex; align-items: center; gap: 6px; font-size: .85rem; }
.code input { width: 160px; }
.newuser { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.newuser input { flex: 1 1 150px; min-width: 0; }
.pwrow { display: flex; gap: 6px; flex: 1 1 220px; }
.pwrow input { flex: 1; min-width: 0; }
.chk { display: flex; align-items: center; gap: 5px; font-size: .85rem; }
.users { list-style: none; padding: 0; margin: 12px 0 0; }
.users li { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; padding: 9px 0; border-top: 1px solid #f1f5f9; }
.u-who small { color: #94a3b8; }
.u-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.u-actions input { width: 140px; }
.tag { font-size: .65rem; text-transform: uppercase; letter-spacing: .06em; background: #0f172a; color: #fff; padding: 2px 6px; border-radius: 6px; margin-left: 4px; }
.tag.off { background: #94a3b8; }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 8px; }
.note { color: #64748b; }
.ok { color: #15803d; font-size: .85rem; }
.err { color: #b91c1c; font-size: .85rem; }
a.btn { display: inline-block; text-decoration: none; }
</style>
