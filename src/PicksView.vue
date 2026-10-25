<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { parseSpreads, parseWeek } from './parse.js'
import { currentLine, resolveGame } from './lines.js'
import { getLines, getWeek, saveWeek, deleteWeek, uploadImage, getTeamCovers, getPool, getSplits } from './api.js'
import { MAIL_APPS, openMail, platform } from './mail.js'
import { mailPrefs, loadMailPrefs } from './mailPrefs.js'
import { gameKey, poolByKey } from './pool.js'
import GameRow from './components/GameRow.vue'
import GameTile from './components/GameTile.vue'
import UploadDialog from './components/UploadDialog.vue'
import MailSettingsDialog from './components/MailSettingsDialog.vue'
import ScheduleList from './components/ScheduleList.vue'
import { gamesFromEvents, groupByKickoff } from './schedule.js'
import { SAMPLE } from './sample.js'

const props = defineProps({ week: Number, currentWeek: Number, isAdmin: Boolean })
const emit = defineEmits(['saved', 'scored'])

const TARGET = 100
const saved = (k, d) => { try { return localStorage.getItem(k) ?? d } catch { return d } }
const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '')

const loading = ref(true)
const imageUrl = ref('')
const pendingFile = ref(null)   // newly uploaded image, persisted on save
const status = ref('')
const busy = ref(false)
const games = ref([])
const adjustment = ref(0)
const adjNote = ref('')
const fixNames = ref(false)
const uploadOpen = ref(false)
const scored = ref(null)        // server-side scoring of the saved picks
const snapshot = ref('')
const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)

// A week with saved picks opens read-only until you press "Edit picks".
const hasSaved = ref(false)
const editMode = ref(true)
const serverCopy = ref(null)    // last saved version, so "Cancel" can put things back

// ---- live lines + results for this week (DraftKings via ESPN, through the local API) ----
const events = ref([])
const ats = ref({})            // team cover records from your saved sheets, before this week
const linesError = ref('')
const loadingLines = ref(false)
let timer
const LIVE_POLL = 30 * 1000      // a game is on: matches the server's ESPN cache
const IDLE_POLL = 5 * 60 * 1000  // nothing live: lines barely move

async function refreshLines() {
  loadingLines.value = true
  try {
    const j = await getLines(props.week)
    events.value = j.events
    linesError.value = ''
  } catch (e) {
    linesError.value = `Current lines unavailable (${e.message}). Is the API running? Try: npm run api`
  } finally {
    loadingLines.value = false
  }
}

const nowLines = computed(() => games.value.map(g => currentLine(g, events.value)))
const hasStarted = g => { const ev = resolveGame(g, events.value).event; return !!ev && ev.state !== 'pre' }
const resultFor = i => scored.value?.games?.[i]
const liveCount = computed(() => events.value.filter(e => e.state === 'in').length)

// ---- the pool's picks (each game's revealed at kickoff) + DraftKings public betting ----
const pool = ref({})
const splits = ref({})
async function refreshPool() {
  try { pool.value = poolByKey(await getPool(props.week)) } catch { /* no pool yet */ }
}
async function refreshSplits() {
  if (!events.value.some(e => e.state === 'pre')) return  // public betting only moves before kickoff
  try { splits.value = await getSplits(props.week) } catch { /* DraftKings unavailable: no public row */ }
}
// before kickoff the card just says the pool's picks are coming (not while you're picking: less noise)
const poolFor = g => { const p = pool.value[gameKey(g)]; return p && (p.revealed || !editMode.value) ? p : null }
const splitFor = g => splits.value[g.eventId ?? resolveGame(g, events.value).event?.id] || null

// While games are on, re-check scores every 30s (and right away when you come back to the tab).
async function poll() {
  clearTimeout(timer)
  const wasLive = liveCount.value > 0
  await refreshLines()
  refreshPool()
  if (!liveCount.value) refreshSplits()
  if (hasSaved.value && (wasLive || liveCount.value)) {
    const w = await getWeek(props.week).catch(() => null)
    if (w?.score) { scored.value = w.score; emit('scored') }
  }
  timer = setTimeout(poll, liveCount.value ? LIVE_POLL : IDLE_POLL)
}
const onVisible = () => { if (document.visibilityState === 'visible' && !loading.value) poll() }


// ---- load saved week ----
const imageSrc = w => (w.hasImage ? `/api/weeks/${props.week}/image?ts=${encodeURIComponent(w.imageVersion || '')}` : '')

// w: the week's lines merged with your saved picks (or defaults, if you haven't saved yet)
function hydrate(w) {
  games.value = w.games.map(g => ({ ...g }))
  hasSaved.value = w.picksSaved
  adjustment.value = w.adjustment || 0
  adjNote.value = w.adjNote || ''
  scored.value = w.score
  serverCopy.value = w
  editMode.value = !w.picksSaved
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
  refreshPool()
  refreshSplits()
  if (w?.hasImage) imageUrl.value = imageSrc(w)
  if (w?.saved) {
    hydrate(w)
    settle(w)
  } else {
    snapshot.value = ''   // no lines yet: admins upload the sheet (or start from the schedule on purpose)
  }
  loading.value = false
  timer = setTimeout(poll, liveCount.value ? LIVE_POLL : IDLE_POLL)
  document.addEventListener('visibilitychange', onVisible)
  if (props.isAdmin && location.search.includes('demo') && !games.value.length) loadText(SAMPLE)
})
onUnmounted(() => { clearTimeout(timer); document.removeEventListener('visibilitychange', onVisible) })

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
  return { points: old.points, pick: old.pick ? pick : null, kept: true }
}

function scaffold() {
  games.value = gamesFromEvents(events.value)
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
    return old ? { ...base, ...carryOver(old, g) } : { ...base, pick: null, points: 2 }
  })
  if (!parsed.length) {
    status.value = 'No games found. Try a clearer or larger image.'
    return false
  }
  const kept = parsed.filter(g => g.kept).length
  parsed.forEach(g => delete g.kept)
  games.value = parsed
  editMode.value = true
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

// ---- search / sort / filter (default = kickoff order, grouped by kickoff slot) ----
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

const liveRec = computed(() => scored.value?.live || { wins: 0, losses: 0, pushes: 0, points: 0 })
const liveGames = computed(() => liveRec.value.wins + liveRec.value.losses + liveRec.value.pushes)
const hasResults = computed(() => !!scored.value && scored.value.wins + scored.value.losses + scored.value.pushes + liveGames.value > 0)
// the week card always shows; before anything's scored (or saved) it's 0 and 0–0
const card = computed(() => scored.value || { score: 0, wins: 0, losses: 0, pushes: 0, pending: 0, adjustment: 0 })
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
    skip: !g.pick,
    outcome: res?.outcome || 'pending',
    live: res?.outcome === 'pending' ? res?.live || null : null,  // covering right now, game still on
    text: [g.fav, g.dog, ...teams].join(' ').toLowerCase(),
    pickHome: g.pick === 'fav' ? r.favHome : !r.favHome,
    moved: Math.abs(now?.delta || 0) + (now?.flipped ? 100 : 0),
    signed: res?.outcome === 'win' ? pts : res?.outcome === 'loss' ? -pts : res?.outcome === 'push' ? pts / 2 : 0,
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
// kickoff order: grouped by kickoff slot (Sunday 1:00 PM, Sunday 4:05 / 4:25 PM, ...)
const groups = computed(() => groupByKickoff(visible.value, events.value))
const activeFilters = computed(() => [fPick.value, fResult.value, fTen.value, fMoved.value].filter(Boolean).length)
const isFiltered = computed(() => !!query.value.trim() || activeFilters.value > 0)

// ---- list (default) or grid layout; grid is a desktop-only option ----
const wideMq = window.matchMedia('(min-width: 900px)')
const wide = ref(wideMq.matches)
const onWide = e => { wide.value = e.matches }
onMounted(() => wideMq.addEventListener('change', onWide))
onUnmounted(() => wideMq.removeEventListener('change', onWide))
const layout = ref(saved('gamesLayout', 'list'))
watch(layout, v => { try { localStorage.setItem('gamesLayout', v) } catch {} })
const gridView = computed(() => wide.value && layout.value === 'grid' && !fixNames.value)

function clearFilters() { query.value = ''; fPick.value = ''; fResult.value = ''; fTen.value = false; fMoved.value = false }

// ---- totals + validation (email + already-sent games make up the week's 100) ----
const picked = computed(() => games.value.filter(g => g.pick))
const total = computed(() => picked.value.reduce((s, g) => s + (Number(g.points) || 0), 0))
const doubleDigits = computed(() => picked.value.filter(g => Number(g.points) >= 10).length)
const diff = computed(() => TARGET - total.value)
const state = computed(() => (total.value === TARGET ? 'good' : total.value > TARGET ? 'bad' : 'warn'))
const pct = computed(() => Math.min(100, (total.value / TARGET) * 100))

const pickName = g => (g.pick === 'fav' ? g.fav : g.dog)
const warnings = computed(() => {
  const w = []
  if (total.value > TARGET) w.push(`Over 100 by ${total.value - TARGET}`)
  if (doubleDigits.value === 4) w.push('Exactly 4 double-digit picks')
  for (const g of picked.value) {
    const p = Number(g.points)
    if (!(Number.isInteger(p) && ((p >= 2 && p <= 20) || p === 50))) w.push(`${pickName(g)}: ${g.points} not allowed (2–20, or 50)`)
  }
  return w
})

// ---- the picks email: your *saved* picks, raw sheet names, sheet order ----
// Games that already kicked off went in an earlier email (e.g. Thursday's), so they're left out, unless every
// pick has kicked off.
const savedPicks = computed(() => (serverCopy.value?.picksSaved ? serverCopy.value.games.filter(g => g.pick) : []))
const outGames = computed(() => {
  const notStarted = savedPicks.value.filter(g => !hasStarted(g))
  return notStarted.length ? notStarted : savedPicks.value
})
const header = computed(() => `${outGames.value.length < savedPicks.value.length ? 'Rest of week' : 'Week'} ${props.week}.`)
const output = computed(() =>
  [header.value, `Team name: ${mailPrefs.teamName}`, '', '', ...outGames.value.map(g => `${pickName(g)} ${g.points}`)].join('\n'))

// ---- "Send picks": opens their own email to this week's league address (set by the admin) ----
const os = platform()
const mailOpen = ref(false)
const mailNote = ref('')
const leagueEmail = computed(() => serverCopy.value?.leagueEmail || '')
const mailApp = computed(() => MAIL_APPS.find(a => a.id === mailPrefs.app))
const message = () => ({
  to: leagueEmail.value,
  subject: [header.value.replace(/\.$/, ''), 'picks', mailPrefs.teamName && `– ${mailPrefs.teamName}`].filter(Boolean).join(' '),
  body: output.value,
  sender: mailPrefs.sender,
})
function launchMail() {
  mailNote.value = openMail(mailPrefs.app, message(), os) ? '' : 'Your browser blocked the new tab. Allow pop-ups for this site, then try again.'
}
function sendPicks() {
  if (mailApp.value) launchMail()
  else mailOpen.value = true
}
function mailChosen() {
  mailOpen.value = false
  launchMail()
}
onMounted(loadMailPrefs)

function resetPoints() { games.value.forEach(g => { g.points = 2 }) }

// ---- saving ----
const payload = computed(() => ({
  label: header.value,
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

const blocker = computed(() =>
  total.value > TARGET ? `Over 100 by ${total.value - TARGET}. Take points off before saving.`
    : doubleDigits.value === 4 ? 'Exactly 4 double-digit picks isn\'t allowed. Use 3 or 5+.' : '')
async function save() {
  saveError.value = ''
  if (blocker.value) { saveError.value = blocker.value; return }
  saving.value = true
  try {
    if (pendingFile.value) {
      await uploadImage(props.week, pendingFile.value)
      pendingFile.value = null
    }
    const w = await saveWeek(props.week, payload.value)
    hydrate(w)
    snapshot.value = JSON.stringify(payload.value)
    emit('saved')
  } catch (e) {
    saveError.value = `Save failed: ${e.message}`
  } finally {
    saving.value = false
  }
}
const weekState = computed(() =>
  dirty.value ? { cls: 'editing', text: 'Unsaved changes' }
    : hasSaved.value ? { cls: 'sent', text: '✓ Saved' } : { cls: 'new', text: 'No picks yet' })
const OUTCOME_TEXT = { win: 'covered', loss: 'missed', push: 'push', pending: 'not played yet', skipped: 'no pick', open: 'no pick yet' }
const LIVE_TEXT = { win: 'live, covering', loss: 'live, not covering', push: 'live, on the number' }
const tally = computed(() => {
  const t = { win: 0, loss: 0, push: 0, pending: 0, liveWin: 0, liveLoss: 0 }
  for (const x of rowInfo.value) {
    if (x.skip) continue
    if (x.live === 'win') t.liveWin++
    else if (x.live) t.liveLoss++   // losing or dead even: not cashing yet
    else if (x.outcome in t) t[x.outcome]++
  }
  return t
})
// no pick: a −20 skip once the game kicks off, until then just an open slot
const segClass = x => (x.skip ? (x.outcome === 'skipped' ? 'skipped' : 'open') : x.live ? `live-${x.live}` : x.outcome)
const segText = x => (x.skip ? `${x.g.fav} / ${x.g.dog}: ${OUTCOME_TEXT[x.outcome] || 'no pick'}`
  : `${pickName(x.g)} ${x.pts}: ${x.live ? LIVE_TEXT[x.live] : OUTCOME_TEXT[x.outcome]}`)

// ---- tap a pill in the strip: a small score popover; tap the popover to jump to that game ----
const pop = ref(null)          // { i, left, arrow } (px, inside the strip)
const stripEl = ref(null)
const popEl = ref(null)
const POP_W = 210
function togglePop(i, seg) {
  if (pop.value?.i === i) { pop.value = null; return }
  const strip = stripEl.value.getBoundingClientRect(), b = seg.getBoundingClientRect()
  const center = b.left + b.width / 2 - strip.left
  const w = Math.min(POP_W, strip.width)
  const left = Math.max(0, Math.min(strip.width - w, center - w / 2))
  pop.value = { i, left, arrow: center - left }
}
// any other tap closes it (taps on a pill are handled by the pill itself)
const onDocTap = e => { if (pop.value && !e.target.closest?.('.wh-strip .seg, .gpop')) pop.value = null }
onMounted(() => document.addEventListener('pointerdown', onDocTap))
onUnmounted(() => document.removeEventListener('pointerdown', onDocTap))
const popInfo = computed(() => {
  const x = pop.value && rowInfo.value[pop.value.i]
  if (!x) return null
  const r = resolveGame(x.g, events.value), ev = r.event, res = resultFor(x.i)
  const scoreOf = key => {
    if (!ev || ev.state === 'pre') return null
    const team = key === 'fav' ? r.favTeam : r.dogTeam
    return ev.scores?.[team === ev.home ? 'home' : 'away'] ?? res?.[`${key}Score`] ?? null
  }
  const side = key => {
    const t = key === 'fav' ? r.favTeam : r.dogTeam
    return { abbr: t?.abbr || (x.g[key] || '').toUpperCase(), logo: t?.logo, score: scoreOf(key), mine: x.g.pick === key }
  }
  const teams = r.favHome ? [side('dog'), side('fav')] : [side('fav'), side('dog')]   // away first
  const l = ev?.live
  const when = !ev ? `${x.g.day || ''} ${x.g.time || ''}`.trim()
    : ev.state === 'post' ? (/OT/.test(ev.detail || '') ? 'Final · OT' : 'Final')
    : ev.state === 'in' ? (l?.halftime ? 'Halftime' : [l?.quarter, l?.clock].filter(Boolean).join(' · ') || 'Live')
    : new Date(ev.kickoff).toLocaleString([], { weekday: 'short', hour: 'numeric', minute: '2-digit' })
  const line = x.g.hasLine === false ? '' : !x.g.spread ? ' PK' : x.g.pick === 'fav' ? ` −${x.g.spread}` : ` +${x.g.spread}`
  const pick = x.skip ? 'No pick' : `${side(x.g.pick).abbr}${line} · ${x.pts} pts`
  return { teams, when, pick, cls: segClass(x), label: segText(x) }
})
async function goToGame(i) {
  pop.value = null
  if (!visible.value.some(x => x.i === i)) clearFilters()
  await nextTick()
  const el = document.querySelector(`[data-game="${i}"]`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash')
  setTimeout(() => el.classList.remove('flash'), 1600)
}

function startEdit() { editMode.value = true }
// Switching modes adds/removes things above the games; keep this card where it was on screen
async function keepInPlace(card, fn) {
  const before = card?.getBoundingClientRect().top
  fn()
  await nextTick()
  if (card?.isConnected && before != null) window.scrollBy(0, card.getBoundingClientRect().top - before)
}
const editFromCard = card => keepInPlace(card, startEdit)
// Cancel in the bottom bar: undo unsaved changes without losing your place in the list
const firstCardOnScreen = () => [...document.querySelectorAll('article.game, article.tile')].find(a => a.getBoundingClientRect().bottom > 0)
const cancelFromBar = () => keepInPlace(firstCardOnScreen(), cancelEdit)
function cancelEdit() {
  saveError.value = ''
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
    games.value = []; scored.value = null; serverCopy.value = null
    hasSaved.value = false; editMode.value = true
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
const adjText = computed(() => [
  ...penaltyRows.value.map(([n, v]) => `${n} −${v}`),
  ...(scored.value?.adjustment ? [`Adjustment ${signed(scored.value.adjustment)}${adjNote.value ? ` (${adjNote.value})` : ''}`] : []),
].join(' · '))
</script>

<template>
  <p v-if="loading" class="loading">Loading week {{ week }}…</p>
  <template v-else>
    <!-- no schedule or sheet for this week yet -->
    <!-- one card: who/what/when on top, the week's results underneath -->
    <section class="weekhead">
      <div class="wh-top">
        <div class="wh-id">
          <div class="wh-title">
            <h2>Week {{ week }}</h2>
            <span v-if="!games.length" class="badge new">Lines not posted yet</span>
            <span v-else :class="['badge', weekState.cls]">{{ weekState.text }}</span>
          </div>
          <p v-if="status || !games.length || scheduled || !hasSaved" class="wh-sub">
            <template v-if="status">{{ status }}</template>
            <template v-else-if="!games.length && isAdmin">Upload the spreads sheet. Saving posts the lines for everyone.</template>
            <template v-else-if="!games.length">Here’s the schedule. You can pick once the lines are posted.</template>
            <template v-else-if="scheduled && isAdmin">NFL schedule with DraftKings lines. Upload the sheet when it’s posted.</template>
            <template v-else-if="scheduled">DraftKings lines for now. The official sheet isn’t posted yet.</template>
            <template v-else>Make your picks, then save.</template>
          </p>
        </div>
        <div v-if="isAdmin" class="wh-actions">
          <template v-if="isAdmin">
            <a v-if="imageUrl" :href="imageUrl" target="_blank" rel="noopener" class="btn ghost sm" title="Open the uploaded sheet">🖼 Sheet</a>
            <button v-if="editMode || !games.length" :class="['btn', games.length ? 'ghost sm' : 'primary']" @click="uploadOpen = true">📷 {{ imageUrl ? 'Replace sheet' : 'Upload sheet' }}</button>
            <button v-if="!games.length && events.length" class="btn ghost" @click="scaffold" title="Use the NFL schedule with DraftKings lines until the sheet is out">Use DraftKings lines</button>
          </template>
        </div>
      </div>

      <div v-if="games.length" class="wh-results">
        <dl class="wh-stats">
          <div :class="['stat', 'score', card.score > 0 ? 'pos' : card.score < 0 ? 'neg' : '']">
            <dt>Score</dt><dd>{{ card.score }}</dd>
            <span v-if="liveGames" class="stat-live" title="Your score if every game on now ended as it stands">
              <i class="ldot"></i>Live {{ scored.ifEndedNow }}
            </span>
          </div>
          <div class="stat">
            <dt>Record</dt><dd>{{ card.wins }}–{{ card.losses }}<template v-if="card.pushes">–{{ card.pushes }}</template></dd>
            <span v-if="liveGames" class="stat-live" title="Your record if every game on now ended as it stands">
              <i class="ldot"></i>Live {{ card.wins + liveRec.wins }}–{{ card.losses + liveRec.losses }}<template v-if="card.pushes + liveRec.pushes">–{{ card.pushes + liveRec.pushes }}</template>
            </span>
          </div>
          <div v-if="hasResults && card.pending" class="stat">
            <dt>Max possible</dt><dd>{{ card.maxScore }}</dd>
            <span v-if="liveGames && scored.liveMax != null" class="stat-live" title="Games on now end as they stand, every game not started yet covers">
              <i class="ldot"></i>Live {{ scored.liveMax }}
            </span>
          </div>
          <div v-else-if="!hasResults" :class="['stat', 'used', state]">
            <dt>Points used</dt><dd>{{ total }}<small> / {{ TARGET }}</small></dd>
            <span class="stat-sub">{{ state === 'good' ? '✓ all in' : diff > 0 ? `${diff} left` : `${-diff} over` }}</span>
          </div>
        </dl>

        <div ref="stripEl" class="wh-strip" :aria-label="`${tally.win} covered, ${tally.loss} missed, ${tally.liveWin + tally.liveLoss} live, ${tally.pending} still to play`">
          <button v-for="x in rowInfo" :key="x.i" type="button" :class="['seg', segClass(x), { loy: x.pts === 50, sel: pop?.i === x.i }]"
                  :aria-label="segText(x)" :aria-expanded="pop?.i === x.i" @click="togglePop(x.i, $event.currentTarget)">{{ x.skip ? '' : x.pts }}</button>
          <button v-if="popInfo" ref="popEl" type="button" :class="['gpop', popInfo.cls]" :style="{ left: pop.left + 'px', '--arrow': pop.arrow + 'px' }"
                  :aria-label="`${popInfo.label}. Go to this game.`" @click="goToGame(pop.i)">
            <span class="gp-teams">
              <span v-for="t in popInfo.teams" :key="t.abbr" :class="['gp-team', { mine: t.mine }]">
                <img v-if="t.logo" :src="t.logo" alt="" /><b>{{ t.abbr }}</b><span v-if="t.score != null" class="gp-sc">{{ t.score }}</span>
              </span>
            </span>
            <span class="gp-foot">
              <span class="gp-when">{{ popInfo.when }}</span>
              <span v-if="popInfo.pick" class="gp-pick">{{ popInfo.pick }}</span>
            </span>
          </button>
        </div>
        <p v-if="!hasResults" class="wh-legend">
          <span><i class="dot pending"></i>{{ picked.length }} picked</span>
          <span v-if="games.length - picked.length"><i class="dot open"></i>{{ games.length - picked.length }} to pick</span>
          <span v-if="penaltyRows.length" class="wh-adj">{{ adjText }}</span>
        </p>
        <p v-else class="wh-legend">
          <span><i class="dot win"></i>{{ tally.win }} covered</span>
          <span><i class="dot loss"></i>{{ tally.loss }} missed</span>
          <span v-if="tally.push"><i class="dot push"></i>{{ tally.push }} push</span>
          <span v-if="tally.liveWin"><i class="dot live-win"></i>{{ tally.liveWin }} covering live</span>
          <span v-if="tally.liveLoss"><i class="dot live-loss"></i>{{ tally.liveLoss }} not covering live</span>
          <span v-if="tally.pending"><i class="dot pending"></i>{{ tally.pending }} to play</span>
          <span v-if="penaltyRows.length || card.adjustment" class="wh-adj">
            {{ adjText }}
          </span>
        </p>
      </div>

      <div v-if="games.length && (!editMode || hasSaved)" class="wh-foot">
        <div class="acts">
          <template v-if="!editMode">
            <button v-if="outGames.length" class="act send" @click="sendPicks">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5.5h14v9H3z M3.5 6l6.5 5 6.5-5" /></svg>Send picks
            </button>
            <button class="act edit" @click="startEdit">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M13.5 3.5l3 3L8 15H5v-3z" /></svg>Edit picks
            </button>
          </template>
          <button v-else class="act" @click="cancelEdit">Cancel</button>
        </div>
        <p v-if="mailNote" class="wh-note">{{ mailNote }}</p>
      </div>
    </section>

    <!-- no lines yet: still show the week's games -->
    <template v-if="!games.length">
      <ScheduleList v-if="events.length" :events="events" />
      <p v-else-if="linesError" class="empty">{{ linesError }}</p>
    </template>

    <template v-if="games.length">
      <p v-if="!editMode && dirty" class="banner">
        <span>You have unsaved updates to this week.</span>
        <button class="btn primary sm" :disabled="saving" @click="save()">{{ saving ? 'Saving…' : 'Save' }}</button>
      </p>
      <p v-if="!editMode && dirty && saveError" class="err">{{ saveError }}</p>

      <!-- edit tools: admins only, while editing -->
      <section v-if="editMode && isAdmin" class="edittools">
        <div class="et-row">
          <b>Edit tools</b>
          <div class="tools">
            <button class="btn ghost" :disabled="loadingLines" @click="refreshLines">{{ loadingLines ? 'Refreshing…' : '↻ Refresh lines' }}</button>
            <button v-if="scheduled" class="btn ghost" :disabled="loadingLines" @click="refreshLines().then(syncLines)" title="Replace the spreads with DraftKings' latest, keeping your picks">↻ Use latest DraftKings lines</button>
            <button class="btn ghost" @click="resetPoints">Reset to 2</button>
            <button :class="['btn', 'ghost', { active: fixNames }]" @click="fixNames = !fixNames">✎ Fix names</button>
          </div>
        </div>
        <div class="r-adj">
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

      <!-- ============ GAMES ============ -->
      <p v-if="linesError" class="linesbar">
        <span class="err">{{ linesError }}</span>
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
        <div v-if="wide" class="layoutswitch" role="group" aria-label="Layout">
          <button :class="{ on: layout === 'list' }" :aria-pressed="layout === 'list'" title="List" @click="layout = 'list'">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 3.5h12M2 8h12M2 12.5h12" /></svg>
          </button>
          <button :class="{ on: layout === 'grid' }" :aria-pressed="layout === 'grid'" title="Grid: every game at once" @click="layout = 'grid'">
            <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="2" width="5" height="5" rx="1" /><rect x="9" y="2" width="5" height="5" rx="1" /><rect x="2" y="9" width="5" height="5" rx="1" /><rect x="9" y="9" width="5" height="5" rx="1" /></svg>
          </button>
        </div>
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

      <section v-if="gridView" class="gamegrid">
        <GameTile
          v-for="x in visible"
          :key="x.i"
          :data-game="x.i"
          :game="x.g"
          :events="events"
          :now="nowLines[x.i]"
          :result="resultFor(x.i)"
          :readonly="!editMode"
          :editable="!editMode"
          @edit="editFromCard"
          :pool="poolFor(x.g)"
          :split="splitFor(x.g)"
        />
      </section>
      <section v-else-if="flat" class="group">
        <GameRow
          v-for="x in visible"
          :key="x.i"
          :data-game="x.i"
          :game="x.g"
          :events="events"
          :now="nowLines[x.i]"
          :result="resultFor(x.i)"
          :ats="ats"
          :editing="fixNames && editMode"
          :readonly="!editMode"
          :editable="!editMode"
          @edit="editFromCard"
          :pool="poolFor(x.g)"
          :split="splitFor(x.g)"
          show-day
        />
      </section>
      <section v-else v-for="grp in groups" :key="grp.key" class="group">
        <h2>{{ grp.day }} <small v-if="grp.when">{{ grp.when }}</small></h2>
        <GameRow
          v-for="x in grp.items"
          :key="x.i"
          :data-game="x.i"
          :game="x.g"
          :events="events"
          :now="nowLines[x.i]"
          :result="resultFor(x.i)"
          :ats="ats"
          :editing="fixNames && editMode"
          :readonly="!editMode"
          :editable="!editMode"
          @edit="editFromCard"
          :pool="poolFor(x.g)"
          :split="splitFor(x.g)"
        />
      </section>
      <p v-if="!visible.length" class="empty">No games match. <button class="link" @click="clearFilters">Clear filters</button></p>

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
          <span class="dd">{{ picked.length }} of {{ games.length }} picked · {{ doubleDigits }} double-digit</span>
          <span class="tb-actions">
          <button v-if="hasSaved" class="btn ghost cancel" :disabled="saving" :title="dirty ? 'Undo your changes and go back to your saved picks' : 'Stop editing'" @click="cancelFromBar">Cancel</button>
          <button :class="['btn', dirty ? 'primary' : 'ghost']" :disabled="saving || !dirty" @click="save()">{{ saving ? '…' : dirty ? 'Save' : 'Saved ✓' }}</button>
          </span>
        </div>
        <ul v-if="warnings.length" class="warnings"><li v-for="w in warnings" :key="w">{{ w }}</li></ul>
        <p v-if="saveError" class="err">{{ saveError }}</p>
      </footer>
    </template>

    <MailSettingsDialog v-if="mailOpen" sending @close="mailOpen = false" @saved="mailChosen" />
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
