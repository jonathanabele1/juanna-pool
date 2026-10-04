<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { parseSpreads, parseWeek } from './parse.js'
import { currentLine, resolveGame } from './lines.js'
import { getLines, getWeek, saveWeek, deleteWeek, uploadImage, getTeamCovers } from './api.js'
import GameRow from './components/GameRow.vue'
import UploadDialog from './components/UploadDialog.vue'
import { gamesFromEvents } from './schedule.js'
import { SAMPLE } from './sample.js'

const props = defineProps({ week: Number, currentWeek: Number, isAdmin: Boolean })
const emit = defineEmits(['saved'])

const TARGET = 100
const saved = (k, d) => { try { return localStorage.getItem(k) ?? d } catch { return d } }
const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '')
const isLocked = gs => gs.length > 0 && gs.every(g => g.status !== 'email') // everything already sent (or skipped)

const loading = ref(true)
const imageUrl = ref('')
const pendingFile = ref(null)   // newly uploaded image, persisted on save
const status = ref('')
const busy = ref(false)
const games = ref([])
const teamName = ref(saved('teamName', ''))
const label = ref('')
const labelTouched = ref(false)
const adjustment = ref(0)
const adjNote = ref('')
const copied = ref(false)
const fixNames = ref(false)
const uploadOpen = ref(false)
const scored = ref(null)        // server-side scoring of the saved picks
const snapshot = ref('')
const saving = ref(false)
const saveError = ref('')
const savedAt = ref(null)
const confirmDelete = ref(false)

// A week that has already been sent is read-only until you press "Edit picks".
const hasSaved = ref(false)
const savedLocked = ref(false)
const editMode = ref(true)
const dueGroups = ref([])       // this week's pick deadlines (reminders only; nothing locks)
const serverCopy = ref(null)    // last saved version, so "Cancel" can put things back
const tab = ref('games')        // games | email

// ---- live lines + results for this week (DraftKings via ESPN, through the local API) ----
const events = ref([])
const ats = ref({})            // team cover records from your saved sheets, before this week
const linesError = ref('')
const fetchedAt = ref(null)
const loadingLines = ref(false)
let timer

async function refreshLines() {
  loadingLines.value = true
  try {
    const j = await getLines(props.week)
    events.value = j.events
    fetchedAt.value = j.fetchedAt
    linesError.value = ''
  } catch (e) {
    linesError.value = `Current lines unavailable (${e.message}). Is the API running? Try: npm run api`
  } finally {
    loadingLines.value = false
  }
}

const nowLines = computed(() => games.value.map(g => currentLine(g, events.value)))
const changedCount = computed(() => nowLines.value.filter((n, i) => n.changed && games.value[i]?.status !== 'skip').length)
const fetchedLabel = computed(() => (fetchedAt.value ? new Date(fetchedAt.value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''))
const resultFor = i => scored.value?.games?.[i]
const showLinesbar = computed(() => !!linesError.value || events.value.some(e => e.state !== 'post'))

watch(teamName, v => { try { localStorage.setItem('teamName', v) } catch {} })

const anySent = computed(() => games.value.some(g => g.status === 'sent'))
watch(anySent, () => { if (!labelTouched.value) label.value = defaultLabel() })
const defaultLabel = () => `${anySent.value ? 'Rest of week' : 'Week'} ${props.week}.`

// ---- load saved week ----
const imageSrc = w => (w.hasImage ? `/api/weeks/${props.week}/image?ts=${encodeURIComponent(w.imageVersion || '')}` : '')

// w: the week's lines merged with your saved picks (or defaults, if you haven't saved yet)
function hydrate(w) {
  games.value = w.games.map(g => ({ ...g }))
  hasSaved.value = w.picksSaved
  label.value = w.picksSaved ? w.label : defaultLabel()
  labelTouched.value = w.picksSaved
  adjustment.value = w.adjustment || 0
  adjNote.value = w.adjNote || ''
  scored.value = w.score
  savedAt.value = w.updatedAt
  serverCopy.value = w
  savedLocked.value = w.picksSaved && isLocked(w.games)
  editMode.value = !savedLocked.value
  imageUrl.value = imageSrc(w)
}

// Saved games that couldn't be matched to an ESPN game earlier (OCR typos) can be resolved now: offer to save that.
function settle(w) {
  const fixable = props.isAdmin && w.games.some((g, i) => !g.eventId && payload.value.games[i]?.eventId)
  snapshot.value = fixable ? '' : JSON.stringify(payload.value)
}

onMounted(async () => {
  const [, w, covers] = await Promise.all([
    refreshLines(),
    getWeek(props.week).catch(() => null),
    getTeamCovers(props.week).catch(() => ({})),
  ])
  ats.value = covers
  dueGroups.value = w?.deadlines || []
  if (w?.hasImage) imageUrl.value = imageSrc(w)
  if (w?.saved) {
    hydrate(w)
    settle(w)
  } else {
    label.value = defaultLabel()   // no lines yet: admins upload the sheet (or start from the schedule on purpose)
    snapshot.value = ''
  }
  loading.value = false
  timer = setInterval(refreshLines, 5 * 60 * 1000)
  if (props.isAdmin && location.search.includes('demo') && !games.value.length) loadText(SAMPLE)
})
onUnmounted(() => clearInterval(timer))

// ---- picks carry over between sources (schedule scaffold <-> uploaded sheet) by game, following the *team* ----
const keyOf = g => {
  const id = g.eventId ?? resolveGame(g, events.value).event?.id
  return id ? `ev:${id}` : `nm:${norm(g.fav)}|${norm(g.dog)}`
}
const pickedAbbr = g => {
  const r = resolveGame(g, events.value)
  return g.pick === 'fav' ? (g.favAbbr ?? r.favTeam?.abbr) : (g.dogAbbr ?? r.dogTeam?.abbr)
}
function carryOver(old, nu) {
  const abbr = pickedAbbr(old)   // the favorite can differ between the sheet and DraftKings, so match on team
  const r = resolveGame(nu, events.value)
  const pick = abbr && r.favTeam?.abbr === abbr ? 'fav' : abbr && r.dogTeam?.abbr === abbr ? 'dog' : old.pick
  return { status: old.status, points: old.points, pick, kept: true }
}
// mid-week, games that already kicked off were probably sent earlier; for a past week, record everything
function startedToSent(arr) {
  const started = arr.map(g => !!currentLine(g, events.value).locked)
  if (started.some(s => !s)) arr.forEach((g, i) => { if (started[i] && !g.kept) g.status = 'sent' })
}

function scaffold() {
  const fresh = gamesFromEvents(events.value)
  startedToSent(fresh)
  games.value = fresh
  editMode.value = true
}

// swap in the latest DraftKings lines, keeping every pick
function syncLines() {
  const prev = new Map(games.value.map(g => [keyOf(g), g]))
  const fresh = gamesFromEvents(events.value).map(n => {
    const o = prev.get(keyOf(n))
    return o ? { ...n, ...carryOver(o, n) } : n
  })
  fresh.forEach(g => delete g.kept)
  games.value = fresh
}
const scheduled = computed(() => games.value.some(g => g.source === 'schedule'))

// ---- upload + OCR (re-uploading keeps picks for matchups that still exist) ----
async function loadText(text) {
  const ocrWeek = parseWeek(text)
  const prev = new Map(games.value.map(g => [keyOf(g), g]))
  const parsed = parseSpreads(text).map(g => {
    const base = { ...g, source: 'sheet' }
    const old = prev.get(keyOf(g))
    return old ? { ...base, ...carryOver(old, g) } : { ...base, status: 'email', pick: 'fav', points: 2 }
  })
  if (!parsed.length) {
    status.value = 'No games found. Try a clearer or larger image.'
    return false
  }
  startedToSent(parsed)
  const kept = parsed.filter(g => g.kept).length
  parsed.forEach(g => delete g.kept)
  games.value = parsed
  if (!labelTouched.value) label.value = defaultLabel()
  editMode.value = true
  tab.value = 'games'
  const notes = [`Found ${parsed.length} games.`]
  if (kept) notes.push(`Kept your picks for ${kept}.`)
  if (ocrWeek && ocrWeek !== props.week) notes.push(`⚠ The image says week ${ocrWeek}, but you're on week ${props.week}.`)
  status.value = notes.join(' ')
  return true
}

async function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) return
  uploadOpen.value = true
  const prevImage = imageUrl.value
  imageUrl.value = URL.createObjectURL(file)
  pendingFile.value = file
  busy.value = true
  status.value = 'Loading OCR engine…'
  try {
    const { recognize } = await import('tesseract.js')
    const { data } = await recognize(file, 'eng', {
      logger: m => { if (m.status) status.value = `${m.status} ${Math.round((m.progress || 0) * 100)}%` },
    })
    if (await loadText(data.text)) uploadOpen.value = false
    else { imageUrl.value = prevImage; pendingFile.value = null }
  } catch (e) {
    status.value = `OCR failed: ${e.message}`
  } finally {
    busy.value = false
  }
}
const onPaste = e => {
  const f = [...(e.clipboardData?.files || [])][0]
  if (f && editMode.value && props.isAdmin) handleFile(f)
}
onMounted(() => window.addEventListener('paste', onPaste))
onUnmounted(() => window.removeEventListener('paste', onPaste))

// ---- search / sort / filter (default = sheet order, grouped by day) ----
const DAY_NAMES = { Thurs: 'Thursday', Tues: 'Tuesday', Wed: 'Wednesday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday', Mon: 'Monday' }
const groupTitle = grp => DAY_NAMES[grp.day] || grp.day

const query = ref('')
const sortKey = ref('time')
const showFilters = ref(false)
const fPick = ref('')
const fResult = ref('')
const fTen = ref(false)
const fMoved = ref(false)

const PICK_CHIPS = [['fav', 'Favorite'], ['dog', 'Underdog'], ['home', 'Home team'], ['away', 'Away team']]
const RESULT_CHIPS = [['win', 'Covered'], ['loss', 'Missed'], ['push', 'Push'], ['pending', 'Pending']]
const SORTS = {
  ptsDesc: [x => (x.skip ? null : x.pts), -1],
  ptsAsc: [x => (x.skip ? null : x.pts), 1],
  spreadDesc: [x => x.g.spread, -1],
  spreadAsc: [x => x.g.spread, 1],
  moved: [x => x.moved, -1],
  best: [x => x.signed, -1],
  worst: [x => x.signed, 1],
}

const hasResults = computed(() => !!scored.value && scored.value.wins + scored.value.losses + scored.value.pushes > 0)
const sortOptions = computed(() => [
  ['time', 'Kickoff order'],
  ['ptsDesc', 'Points: high → low'],
  ['ptsAsc', 'Points: low → high'],
  ['spreadDesc', 'Spread: biggest first'],
  ['spreadAsc', 'Spread: smallest first'],
  ['moved', 'Line moved most'],
  ...(hasResults.value ? [['best', 'Best results first'], ['worst', 'Worst results first']] : []),
])

const rowInfo = computed(() => games.value.map((g, i) => {
  const r = resolveGame(g, events.value)
  const res = resultFor(i)
  const now = nowLines.value[i]
  const pts = Number(g.points) || 0
  const teams = [r.favTeam, r.dogTeam].flatMap(t => (t ? [t.location, t.name, t.abbr] : []))
  return {
    g, i, pts,
    skip: g.status === 'skip',
    outcome: res?.outcome || 'pending',
    text: [g.fav, g.dog, ...teams].join(' ').toLowerCase(),
    pickHome: g.pick === 'fav' ? r.favHome : !r.favHome,
    moved: Math.abs(now?.delta || 0) + (now?.flipped ? 100 : 0),
    signed: res?.outcome === 'win' ? pts : res?.outcome === 'loss' ? -pts : 0,
  }
}))

const visible = computed(() => {
  const tokens = query.value.toLowerCase().split(/\s+/).filter(Boolean)
  let rows = rowInfo.value.filter(x => {
    if (tokens.some(t => !x.text.includes(t))) return false
    if (fPick.value && x.skip) return false
    if (fPick.value === 'fav' && x.g.pick !== 'fav') return false
    if (fPick.value === 'dog' && x.g.pick !== 'dog') return false
    if (fPick.value === 'home' && !x.pickHome) return false
    if (fPick.value === 'away' && x.pickHome) return false
    if (fResult.value && x.outcome !== fResult.value) return false
    if (fTen.value && (x.skip || x.pts < 10)) return false
    if (fMoved.value && !x.moved) return false
    return true
  })
  const s = SORTS[sortKey.value]
  if (s) {
    const [key, dir] = s
    rows = [...rows].sort((a, b) => {
      const p = key(a), q = key(b)
      if (p == null && q == null) return a.i - b.i
      if (p == null) return 1
      if (q == null) return -1
      return (p - q) * dir || a.i - b.i
    })
  }
  return rows
})
const flat = computed(() => sortKey.value !== 'time')
const groups = computed(() => {
  const out = []
  for (const x of visible.value) {
    const key = `${x.g.day}|${x.g.time}`
    let grp = out.find(o => o.key === key)
    if (!grp) out.push((grp = { key, day: x.g.day, time: x.g.time, items: [] }))
    grp.items.push(x)
  }
  return out
})
const activeFilters = computed(() => [fPick.value, fResult.value, fTen.value, fMoved.value].filter(Boolean).length)
const isFiltered = computed(() => !!query.value.trim() || activeFilters.value > 0)
function clearFilters() { query.value = ''; fPick.value = ''; fResult.value = ''; fTen.value = false; fMoved.value = false }

// ---- totals + validation (email + already-sent games make up the week's 100) ----
const picked = computed(() => games.value.filter(g => g.status !== 'skip'))
const emailGames = computed(() => games.value.filter(g => g.status === 'email'))
const total = computed(() => picked.value.reduce((s, g) => s + (Number(g.points) || 0), 0))
const sentTotal = computed(() => games.value.filter(g => g.status === 'sent').reduce((s, g) => s + (Number(g.points) || 0), 0))
const skipped = computed(() => games.value.length - picked.value.length)
const doubleDigits = computed(() => picked.value.filter(g => Number(g.points) >= 10).length)
const diff = computed(() => TARGET - total.value)
const state = computed(() => (total.value === TARGET ? 'good' : total.value > TARGET ? 'bad' : 'warn'))
const pct = computed(() => Math.min(100, (total.value / TARGET) * 100))

const pickName = g => (g.pick === 'fav' ? g.fav : g.dog)
const warnings = computed(() => {
  const w = []
  if (total.value > TARGET) w.push(`Over 100 by ${total.value - TARGET}: −${Math.ceil((total.value - TARGET) / 10) * 20} penalty`)
  if (doubleDigits.value === 4) w.push('Exactly 4 double-digit picks: −20 penalty')
  if (skipped.value) w.push(`${skipped.value} skipped game${skipped.value > 1 ? 's' : ''}: −${skipped.value * 20}`)
  for (const g of picked.value) {
    const p = Number(g.points)
    if (!(Number.isInteger(p) && ((p >= 2 && p <= 20) || p === 50))) w.push(`${pickName(g)}: ${g.points} not allowed (2–20, or 50)`)
  }
  return w
})

// ---- email output: raw sheet names, sheet order ----
const includeSentOverride = ref(null)
const includeSent = computed(() => includeSentOverride.value ?? emailGames.value.length === 0)
const outGames = computed(() => games.value.filter(g => g.status === 'email' || (includeSent.value && g.status === 'sent')))
const output = computed(() => {
  const head = includeSent.value ? label.value.replace(/^rest of week/i, 'Week') : label.value
  return [head, `Team name: ${teamName.value}`, '', '', ...outGames.value.map(g => `${pickName(g)} ${g.points}`)].join('\n')
})
async function copy() {
  try {
    await navigator.clipboard.writeText(output.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1800)
  } catch {
    document.getElementById('out')?.select()
  }
}
function resetPoints() { games.value.forEach(g => { if (g.status === 'email') g.points = 2 }) }

// ---- saving ----
const payload = computed(() => ({
  label: label.value,
  adjustment: Math.round(Number(adjustment.value) || 0),
  adjNote: adjNote.value,
  games: games.value.map(g => {
    if (!props.isAdmin) return { ...g, points: Math.round(Number(g.points) || 0) }
    const r = resolveGame(g, events.value)
    return {
      ...g,
      points: Math.round(Number(g.points) || 0),
      eventId: r.event?.id ?? g.eventId ?? null,
      favAbbr: r.favTeam?.abbr ?? g.favAbbr ?? null,
      dogAbbr: r.dogTeam?.abbr ?? g.dogAbbr ?? null,
      favHome: r.favHome,
    }
  }),
}))
const dirty = computed(() => games.value.length > 0 && (JSON.stringify(payload.value) !== snapshot.value || !!pendingFile.value))

async function save({ markSent = false } = {}) {
  if (markSent) games.value.forEach(g => { if (g.status === 'email') g.status = 'sent' })
  saving.value = true
  saveError.value = ''
  try {
    if (pendingFile.value) {
      await uploadImage(props.week, pendingFile.value)
      pendingFile.value = null
    }
    const w = await saveWeek(props.week, payload.value)
    const keepLabel = label.value
    hydrate(w)
    label.value = keepLabel
    labelTouched.value = true
    snapshot.value = JSON.stringify(payload.value)
    emit('saved')
  } catch (e) {
    saveError.value = `Save failed: ${e.message}`
  } finally {
    saving.value = false
  }
}
const weekState = computed(() =>
  !hasSaved.value ? { cls: 'new', text: 'Not saved' }
    : editMode.value ? { cls: 'editing', text: 'Editing' }
      : savedLocked.value ? { cls: 'sent', text: '✓ Sent' } : { cls: 'draft', text: 'Draft' })
const fmtDue = iso => new Date(iso).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })
const dueChips = computed(() => {
  const now = Date.now()
  return dueGroups.value.map(g => ({ id: g.id, label: g.label, when: fmtDue(g.deadline), past: Date.parse(g.deadline) <= now }))
})
const savedLabel = computed(() => (savedAt.value ? new Date(savedAt.value.replace(' ', 'T') + 'Z').toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : ''))

function startEdit() { editMode.value = true; tab.value = 'games' }
function cancelEdit() {
  pendingFile.value = null
  confirmDelete.value = false
  fixNames.value = false
  status.value = ''
  if (serverCopy.value) { hydrate(serverCopy.value); settle(serverCopy.value) }
}

async function clearWeek() {
  try {
    await deleteWeek(props.week)
  } catch (e) {
    saveError.value = e.message
    confirmDelete.value = false
    return
  }
  pendingFile.value = null; confirmDelete.value = false; status.value = ''
  const w = await getWeek(props.week).catch(() => null)
  if (w?.saved) {
    hydrate(w)
  } else {
    games.value = []; scored.value = null; serverCopy.value = null; savedAt.value = null
    hasSaved.value = false; savedLocked.value = false; editMode.value = true
  }
  snapshot.value = ''
  emit('saved')
}

// ---- results summary ----
const penaltyRows = computed(() => {
  const p = scored.value?.penalties || {}
  return [['Over 100', p.over100], ['Four double-digits', p.fourDoubleDigits], ['Skipped games', p.missingGames]].filter(([, v]) => v)
})
const signed = n => (n > 0 ? `+${n}` : `${n}`)
</script>

<template>
  <p v-if="loading" class="loading">Loading week {{ week }}…</p>
  <template v-else>
    <!-- no schedule or sheet for this week yet -->
    <section v-if="!games.length" class="emptystate">
      <template v-if="isAdmin">
        <h3>No lines for week {{ week }} yet</h3>
        <p>Upload this week’s spreads sheet. Saving posts the lines for everyone.</p>
        <div class="es-actions">
          <button class="btn primary" @click="uploadOpen = true">📷 Upload sheet</button>
          <button v-if="events.length" class="btn ghost" @click="scaffold" title="Use the NFL schedule with DraftKings lines until the sheet is out">Start from the NFL schedule</button>
        </div>
      </template>
      <template v-else>
        <h3>Week {{ week }} lines aren’t posted yet</h3>
        <p>Check back once the admin uploads this week’s sheet.</p>
      </template>
    </section>

    <section v-else class="weekhead">
      <div class="wh-main">
        <div class="wh-title">
          <h2>Week {{ week }}</h2>
          <span :class="['badge', weekState.cls]">{{ weekState.text }}</span>
        </div>
        <ul v-if="dueChips.length" class="wh-due">
          <li v-for="d in dueChips" :key="d.id" :class="{ past: d.past }">
            <span class="dl">{{ d.label }}</span> {{ d.past ? 'was due' : 'due' }} <b>{{ d.when }}</b>
          </li>
        </ul>
        <p class="wh-sub">
          <template v-if="status">{{ status }}</template>
          <template v-else-if="scheduled && isAdmin">NFL schedule with DraftKings lines. Upload the sheet when it’s posted.</template>
          <template v-else-if="scheduled">DraftKings lines for now. The official sheet isn’t posted yet.</template>
          <template v-else-if="savedLabel">Saved {{ savedLabel }}</template>
          <template v-else>Make your picks, then save.</template>
        </p>
      </div>
      <div class="wh-actions">
        <template v-if="isAdmin">
          <a v-if="imageUrl" :href="imageUrl" target="_blank" rel="noopener" class="btn ghost sm" title="Open the uploaded sheet">🖼 Sheet</a>
          <button v-if="editMode" class="btn ghost sm" @click="uploadOpen = true">📷 {{ imageUrl ? 'Replace sheet' : 'Upload sheet' }}</button>
        </template>
        <button v-if="!editMode" class="btn primary" @click="startEdit">✎ Edit picks</button>
        <button v-else-if="hasSaved" class="btn ghost" @click="cancelEdit">Cancel</button>
      </div>
    </section>

    <template v-if="games.length">
      <p v-if="!editMode && dirty" class="banner">
        <span>You have unsaved updates to this week.</span>
        <button class="btn primary sm" :disabled="saving" @click="save()">{{ saving ? 'Saving…' : 'Save' }}</button>
      </p>

      <!-- results (compact) -->
      <section v-if="hasResults" class="results">
        <div class="r-main">
          <div>
            <div class="r-label">Week {{ week }} score</div>
            <div :class="['r-score', { neg: scored.score < 0 }]">{{ scored.score }}</div>
          </div>
          <dl class="r-stats">
            <div><dt>Record</dt><dd>{{ scored.wins }}–{{ scored.losses }}<template v-if="scored.pushes">–{{ scored.pushes }}</template></dd></div>
            <div><dt>Points won</dt><dd>{{ scored.earned }} <small>/ {{ scored.wagered }}</small></dd></div>
            <div v-if="scored.pending"><dt>Pending</dt><dd>{{ scored.pending }}</dd></div>
            <div v-if="scored.penaltyTotal"><dt>Penalties</dt><dd class="neg">−{{ scored.penaltyTotal }}</dd></div>
          </dl>
        </div>
        <p v-if="penaltyRows.length || scored.adjustment" class="r-pen">
          <span v-for="[n, v] in penaltyRows" :key="n">{{ n }} −{{ v }}</span>
          <span v-if="scored.adjustment" :class="scored.adjustment < 0 ? 'neg' : 'pos'">Adjustment {{ signed(scored.adjustment) }}<template v-if="adjNote"> · {{ adjNote }}</template></span>
        </p>
        <p v-if="!scored.complete" class="r-hint">Score so far; games in progress or unplayed are pending.</p>
      </section>

      <!-- edit tools: only while editing -->
      <section v-if="editMode" class="edittools">
        <div class="et-row">
          <b>Edit tools</b>
          <div class="tools">
            <button class="btn ghost" :disabled="loadingLines" @click="refreshLines">{{ loadingLines ? 'Refreshing…' : '↻ Refresh lines' }}</button>
            <button v-if="scheduled && isAdmin" class="btn ghost" :disabled="loadingLines" @click="refreshLines().then(syncLines)" title="Replace the spreads with DraftKings' latest, keeping your picks">↻ Use latest DK lines</button>
            <button class="btn ghost" @click="resetPoints">Reset to 2</button>
            <button v-if="isAdmin" :class="['btn', 'ghost', { active: fixNames }]" @click="fixNames = !fixNames">✎ Fix names</button>
          </div>
        </div>
        <div v-if="isAdmin" class="r-adj">
          <label>Adjustment <input type="number" v-model.number="adjustment" /></label>
          <label class="grow">Note <input v-model="adjNote" placeholder="e.g. 2nd late pick (−10)" /></label>
        </div>
        <div v-if="hasSaved" class="et-danger">
          <button v-if="!confirmDelete" class="btn ghost danger" @click="confirmDelete = true">Clear my picks…</button>
          <template v-else>
            <span>Clear your saved picks for week {{ week }}?</span>
            <button class="btn danger-solid" @click="clearWeek">Yes, delete</button>
            <button class="btn ghost" @click="confirmDelete = false">Keep</button>
          </template>
        </div>
      </section>

      <!-- Games | Email -->
      <div class="subtabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'games'" :class="{ on: tab === 'games' }" @click="tab = 'games'">Games <small>{{ games.length }}</small></button>
        <button role="tab" :aria-selected="tab === 'email'" :class="{ on: tab === 'email' }" @click="tab = 'email'">✉ Email</button>
      </div>

      <!-- ============ GAMES ============ -->
      <template v-if="tab === 'games'">
        <p v-if="showLinesbar" class="linesbar">
          <span v-if="fetchedLabel">DraftKings lines via ESPN · updated {{ fetchedLabel }}</span>
          <b v-if="changedCount" class="chg">⚠ {{ changedCount }} line{{ changedCount > 1 ? 's' : '' }} moved since your sheet</b>
          <span v-if="linesError" class="err">{{ linesError }}</span>
        </p>

        <section class="filterbar">
          <div class="search">
            <span aria-hidden="true">⌕</span>
            <input v-model="query" type="search" placeholder="Search a team…" aria-label="Search a team" />
          </div>
          <select v-model="sortKey" aria-label="Sort games">
            <option v-for="[v, t] in sortOptions" :key="v" :value="v">{{ t }}</option>
          </select>
          <button :class="['btn', 'ghost', { active: showFilters || activeFilters }]" @click="showFilters = !showFilters" aria-label="Filters">
            ⚙ Filters <span v-if="activeFilters" class="count">{{ activeFilters }}</span>
          </button>
        </section>

        <section v-if="showFilters" class="chips">
          <div class="chipgroup">
            <span class="cg">My pick</span>
            <button v-for="[v, t] in PICK_CHIPS" :key="v" :class="['chip', { on: fPick === v }]" @click="fPick = fPick === v ? '' : v">{{ t }}</button>
          </div>
          <div v-if="hasResults" class="chipgroup">
            <span class="cg">Result</span>
            <button v-for="[v, t] in RESULT_CHIPS" :key="v" :class="['chip', { on: fResult === v }]" @click="fResult = fResult === v ? '' : v">{{ t }}</button>
          </div>
          <div class="chipgroup">
            <span class="cg">Other</span>
            <button :class="['chip', { on: fTen }]" @click="fTen = !fTen">10+ points</button>
            <button :class="['chip', { on: fMoved }]" @click="fMoved = !fMoved">Line moved</button>
          </div>
        </section>

        <p v-if="isFiltered" class="showing">
          Showing {{ visible.length }} of {{ games.length }} games
          <button class="link" @click="clearFilters">Clear filters</button>
        </p>

        <section v-if="flat" class="group">
          <GameRow
            v-for="x in visible"
            :key="x.i"
            :game="x.g"
            :events="events"
            :now="nowLines[x.i]"
            :result="resultFor(x.i)"
            :ats="ats"
            :editing="fixNames && editMode"
            :readonly="!editMode"
            show-day
          />
        </section>
        <section v-else v-for="grp in groups" :key="grp.key" class="group">
          <h2>{{ groupTitle(grp) }} <small v-if="grp.time">{{ grp.time }}</small></h2>
          <GameRow
            v-for="x in grp.items"
            :key="x.i"
            :game="x.g"
            :events="events"
            :now="nowLines[x.i]"
            :result="resultFor(x.i)"
            :ats="ats"
            :editing="fixNames && editMode"
            :readonly="!editMode"
          />
        </section>
        <p v-if="!visible.length" class="empty">No games match. <button class="link" @click="clearFilters">Clear filters</button></p>
      </template>

      <!-- ============ EMAIL ============ -->
      <section v-else class="mail">
        <div :class="['mailtotal', state]">
          <span class="big">{{ total }}<small> / {{ TARGET }}</small></span>
          <span class="msg">
            <template v-if="state === 'good'">✓ Exactly 100</template>
            <template v-else-if="diff > 0">{{ diff }} to go</template>
            <template v-else>{{ -diff }} over</template>
          </span>
          <span class="dd">{{ doubleDigits }} double-digit</span>
        </div>
        <ul v-if="warnings.length" class="warnings"><li v-for="w in warnings" :key="w">{{ w }}</li></ul>

        <div class="mailcard">
          <div class="em-fields">
            <label>Header<input v-model="label" @input="labelTouched = true" /></label>
            <label>Team name<input v-model="teamName" placeholder="Your pool team name" /></label>
          </div>
          <label class="chk">
            <input type="checkbox" :checked="includeSent" @change="includeSentOverride = $event.target.checked" />
            Include games I’ve already sent
            <small v-if="sentTotal">({{ sentTotal }} pts)</small>
          </label>
          <textarea id="out" readonly :value="output" :rows="Math.min(24, outGames.length + 5)"></textarea>
          <p class="hint">Uses the team names exactly as written on the sheet.</p>
          <button class="btn primary big" @click="copy">{{ copied ? '✓ Copied' : 'Copy for email' }}</button>
          <div class="savebtns">
            <button class="btn ghost" :disabled="saving || !dirty" @click="save()">{{ saving ? 'Saving…' : dirty ? 'Save picks' : '✓ Saved' }}</button>
            <button class="btn ghost" :disabled="saving || !emailGames.length" @click="save({ markSent: true })" title="Saves, and flags the games waiting to be emailed as already sent">Save &amp; mark as sent</button>
          </div>
          <p v-if="saveError" class="err">{{ saveError }}</p>
        </div>
      </section>

      <!-- sticky total: only while editing -->
      <footer v-if="editMode" :class="['totalbar', state]">
        <div class="track"><div class="fill" :style="{ width: pct + '%' }"></div></div>
        <div class="tb-row">
          <span class="big">{{ total }}<small> / {{ TARGET }}</small></span>
          <span class="msg">
            <template v-if="state === 'good'">✓ Exactly 100</template>
            <template v-else-if="diff > 0">{{ diff }} to go</template>
            <template v-else>{{ -diff }} over</template>
          </span>
          <span class="dd">{{ doubleDigits }} double-digit<template v-if="sentTotal"> · {{ sentTotal }} sent</template></span>
          <button v-if="tab !== 'email'" class="btn ghost" @click="tab = 'email'">✉ Email</button>
          <button :class="['btn', dirty ? 'primary' : 'ghost']" :disabled="saving || !dirty" @click="save()">{{ saving ? '…' : dirty ? 'Save' : 'Saved ✓' }}</button>
        </div>
        <ul v-if="warnings.length && tab !== 'email'" class="warnings"><li v-for="w in warnings" :key="w">{{ w }}</li></ul>
        <p v-if="saveError" class="err">{{ saveError }}</p>
      </footer>
    </template>

    <UploadDialog
      v-if="uploadOpen && isAdmin"
      :week="week"
      :busy="busy"
      :status="status"
      :has-games="games.length > 0"
      @close="uploadOpen = false"
      @file="handleFile"
    />
  </template>
</template>
