<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  raw: String,           // name exactly as on the sheet (what goes in the email)
  team: Object,          // ESPN team (logo, location, name, color, record) or null
  role: String,          // 'fav' | 'dog'
  home: Boolean,
  spread: Number,
  selected: Boolean,
  dimmed: Boolean,
  editing: Boolean,
  score: Number,         // final/live score, when known
  outcome: String,       // 'win' | 'loss' | 'push' (picked card only, once final)
  ats: Object,           // {w,l,p} cover record on your sheets going into this week
  readonly: Boolean,     // view mode: shows the pick but can't change it
  noLine: Boolean,       // scheduled game with no spread posted yet
  live: String,          // 'win' | 'loss' | 'push': picked card while the game is on, covering or not
  possession: Boolean,   // this team has the ball
  trailing: Boolean,     // final, and this team lost
  points: [Number, String], // points wagered (picked card only)
  peekable: Boolean,     // press and hold (or double-click) shows the team's season stats
})
const emit = defineEmits(['select', 'update:raw', 'peek'])

// press and hold (or double-click): 'peek'. A hold doesn't also pick; GameRow undoes a double-click's two picks.
const HOLD_MS = 450
let holdTimer = null, holdFrom = null, held = false
function onDown(e) {
  held = false
  if (!props.peekable || e.button > 0) return
  holdFrom = [e.clientX, e.clientY]
  clearTimeout(holdTimer)
  holdTimer = setTimeout(() => { held = true; holdFrom = null; navigator.vibrate?.(8); emit('peek') }, HOLD_MS)
}
function onMove(e) { if (holdFrom && Math.hypot(e.clientX - holdFrom[0], e.clientY - holdFrom[1]) > 10) endHold() }  // scrolling
function endHold() { clearTimeout(holdTimer); holdFrom = null }
function onClick(e) {
  if (held) { held = false; return }
  if (props.readonly || e.detail > 1) return   // a double-click's second click: dblclick handles it
  emit('select')
}
function onDbl() { if (props.peekable) emit('peek', { undo: true }) }

const broken = ref(false)
const OUTCOME_COLOR = { win: '#16a34a', loss: '#dc2626', push: '#d97706' }
const LIVE_COLOR = { win: '#4ade80', loss: '#f87171', push: '#facc15' }  // lighter shades of the final colors
const accent = computed(() => OUTCOME_COLOR[props.outcome] || LIVE_COLOR[props.live] || (props.team?.color ? `#${props.team.color}` : '#16a34a'))

const pickem = computed(() => !props.spread)
const spreadText = computed(() => (props.noLine ? '—' : pickem.value ? 'PK' : props.role === 'fav' ? `−${props.spread}` : `+${props.spread}`))
const roleText = computed(() => (props.noLine ? 'NO LINE YET' : pickem.value ? "PICK'EM" : props.role === 'fav' ? '★ FAVORITE' : 'UNDERDOG'))
const city = computed(() => props.team?.location || '')
const nick = computed(() => props.team?.name || props.raw?.toUpperCase())
const dash = s => s?.replace(/-/g, '–')
// the wager chip: a solid disc in team colors (gold for the Lock of the Year) on the team you backed,
// until the game starts; then the result takes over
const wager = computed(() => Number(props.points) || 0)
const isLoy = computed(() => wager.value === 50)
const chipColor = computed(() => (isLoy.value ? '#eab308' : props.team?.color ? `#${props.team.color}` : '#334155'))
// dark text on light team colors (e.g. Saints gold), white on the rest
const chipInk = computed(() => {
  const h = chipColor.value.slice(1)
  const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16))
  return isLoy.value || 0.299 * r + 0.587 * g + 0.114 * b > 170 ? '#0f172a' : '#fff'
})
const showChip = computed(() => props.selected && !props.editing && wager.value > 0 && props.score == null && !props.outcome && !props.live)
const mark = computed(() => (props.outcome === 'loss' ? '✗' : props.outcome === 'push' ? '=' : props.live === 'loss' ? '!' : '✓'))

const atsText = computed(() => {
  const a = props.ats
  return a && a.w + a.l + a.p ? `${a.w}–${a.l}${a.p ? `–${a.p}` : ''}` : null
})
</script>

<template>
  <button
    type="button"
    :class="['team', role, outcome, { selected, dimmed, pickem, static: readonly, peekable }]"
    :style="{ '--accent': accent }"
    :aria-pressed="selected"
    :aria-label="`Pick ${team ? team.location + ' ' + team.name : raw}, ${roleText} ${spreadText}`"
    :tabindex="readonly ? -1 : 0"
    @click="onClick"
    @dblclick="onDbl"
    @pointerdown="onDown"
    @pointermove="onMove"
    @pointerup="endHold"
    @pointercancel="endHold"
    @pointerleave="endHold"
    @contextmenu="peekable && $event.preventDefault()"
  >
    <span class="strip">
      <span class="role">{{ roleText }}</span>
      <span class="sp">{{ spreadText }}</span>
    </span>

    <span class="body">
      <img v-if="team?.logo && !broken" :src="team.logo" :alt="team.abbr" class="logo" draggable="false" @error="broken = true" />
      <span v-else class="logo fallback">{{ (raw || '?').slice(0, 2).toUpperCase() }}</span>
      <span class="names">
        <span class="city">
          {{ city }}
          <span :class="['where', home ? 'home' : 'away']">{{ home ? '⌂ HOME' : '✈ AWAY' }}</span>
        </span>
        <span class="nick">{{ nick }}<i v-if="possession" class="ball" title="Has the ball">🏈</i></span>
        <span v-if="team?.record || atsText" class="rec">
          <span v-if="team?.record" class="su" title="Overall record going into this game">{{ dash(team.record) }}</span>
          <span v-if="atsText" class="ats" title="Cover record against your sheet lines (weeks before this one)">ATS {{ atsText }}</span>
        </span>
      </span>
      <span v-if="score != null" :class="['score', { trailing }]">{{ score }}</span>
      <span
        v-if="showChip"
        :class="['chip', { loy: isLoy }]"
        :style="{ '--chip': chipColor, '--ink': chipInk }"
        :title="`${wager} points on ${nick}`"
      >
        <i v-if="isLoy" class="star" aria-hidden="true">★</i>
        <b :key="wager">{{ wager }}</b>
        <small>{{ isLoy ? 'LOY' : 'PTS' }}</small>
      </span>
      <span v-else-if="selected && !editing" :class="['check', { end: score == null }]" aria-hidden="true">{{ mark }}</span>
    </span>

    <input
      v-if="editing"
      class="raw"
      :value="raw"
      spellcheck="false"
      @click.stop
      @input="$emit('update:raw', $event.target.value)"
    />
  </button>
</template>

<style scoped>
.team {
  position: relative; display: flex; flex-direction: column; text-align: left; width: 100%; padding: 0; overflow: hidden;
  background: #fff; border: 2px solid #e5e7eb; border-radius: 14px; cursor: pointer;
  font: inherit; color: inherit; transition: border-color .15s, box-shadow .15s, transform .08s, opacity .15s, background .15s;
}
/* press and hold opens the team's stats: no text selection or iOS callout while holding */
.team.peekable { -webkit-touch-callout: none; -webkit-user-select: none; user-select: none; touch-action: manipulation; }
.team:hover { border-color: #cbd5e1; box-shadow: 0 2px 8px #0000000f; }
.team:active { transform: scale(.985); }
.team:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }
.team.selected {
  border-color: var(--accent); background: color-mix(in srgb, var(--accent) 7%, #fff);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent);
}
.team.static { cursor: default; }
.team.static:hover { border-color: #e5e7eb; box-shadow: none; }
.team.static.selected:hover { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
.team.static:active { transform: none; }
.team.dimmed { opacity: .72; }
.team.dimmed:not(.static):hover { opacity: 1; }

/* favorite / underdog banner with the spread */
.strip { display: flex; justify-content: space-between; align-items: baseline; padding: 5px 12px; }
.role { font-size: .68rem; font-weight: 800; letter-spacing: .09em; }
.sp { font-size: 1.2rem; font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.fav .strip { background: #0f172a; color: #fff; }
.fav .sp { color: #fde047; }
.dog .strip { background: #ffedd5; color: #9a3412; }
.pickem .strip { background: #e2e8f0; color: #334155; }
.pickem .sp { color: #334155; }
.fav { border-color: #cbd5e1; }

.body { display: flex; align-items: center; gap: 12px; padding: 10px 12px 12px; }
.logo { width: 52px; height: 52px; object-fit: contain; flex: none; }
.logo.fallback { display: grid; place-items: center; border-radius: 50%; background: #e2e8f0; color: #475569; font-weight: 800; }
.names { display: flex; flex-direction: column; gap: 1px; line-height: 1.15; min-width: 0; }
.city { font-size: .75rem; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.where { font-size: .58rem; font-weight: 800; letter-spacing: .06em; padding: 1px 6px; border-radius: 999px; }
.where.home { background: #e0e7ff; color: #3730a3; }
.where.away { background: #f1f5f9; color: #475569; }
.nick { font-size: 1.1rem; font-weight: 800; overflow-wrap: anywhere; }
.rec { display: flex; gap: 6px; align-items: baseline; margin-top: 2px; font-size: .75rem; }
.su { font-weight: 700; color: #334155; font-variant-numeric: tabular-nums; }
.ats { color: #64748b; font-weight: 600; font-variant-numeric: tabular-nums; }

.score { margin-left: auto; font-size: 1.6rem; font-weight: 800; color: #334155; font-variant-numeric: tabular-nums; }
.score.trailing { color: #94a3b8; font-weight: 700; }
.ball { font-style: normal; font-size: .8rem; margin-left: 6px; vertical-align: 2px; }
.check {
  flex: none; width: 22px; height: 22px; border-radius: 50%;
  display: grid; place-items: center; background: var(--accent); color: #fff; font-size: .8rem; font-weight: 800;
}
.check.end { margin-left: auto; }
/* wager chip: the points you put on this team, before kickoff */
.chip {
  flex: none; margin-left: auto; width: 50px; height: 50px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1;
  background: var(--chip); color: var(--ink);
  box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--ink) 22%, transparent), 0 3px 8px #0f172a2e;
  animation: chip-drop .38s cubic-bezier(.2, 1.4, .4, 1) both;
}
.chip b { font-size: 1.4rem; font-weight: 900; font-variant-numeric: tabular-nums; letter-spacing: -.03em; animation: chip-pop .3s ease-out; }
.chip small { font-size: .52rem; font-weight: 800; letter-spacing: .1em; opacity: .8; margin-top: 2px; }
.chip.loy { background: linear-gradient(160deg, #fde047, #eab308); box-shadow: 0 0 0 3px #fde04766, 0 3px 10px #ca8a0466; }
.chip .star { font-style: normal; font-size: .55rem; margin-bottom: 1px; }
@keyframes chip-drop { from { transform: translateY(-14px) scale(1.25); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes chip-pop { 0% { transform: scale(1.35); } 100% { transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .chip, .chip b { animation: none; } }
.raw { font: inherit; font-size: .8rem; padding: 4px 6px; margin: 0 12px 10px; border: 1px dashed #94a3b8; border-radius: 6px; width: calc(100% - 24px); box-sizing: border-box; }
</style>
