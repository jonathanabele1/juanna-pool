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
})
defineEmits(['select', 'update:raw'])

const broken = ref(false)
const OUTCOME_COLOR = { win: '#16a34a', loss: '#dc2626', push: '#64748b' }
const accent = computed(() => OUTCOME_COLOR[props.outcome] || (props.team?.color ? `#${props.team.color}` : '#16a34a'))

const pickem = computed(() => !props.spread)
const spreadText = computed(() => (props.noLine ? '—' : pickem.value ? 'PK' : props.role === 'fav' ? `−${props.spread}` : `+${props.spread}`))
const roleText = computed(() => (props.noLine ? 'NO LINE YET' : pickem.value ? "PICK'EM" : props.role === 'fav' ? '★ FAVORITE' : 'UNDERDOG'))
const city = computed(() => props.team?.location || '')
const nick = computed(() => props.team?.name || props.raw?.toUpperCase())
const dash = s => s?.replace(/-/g, '–')
const atsText = computed(() => {
  const a = props.ats
  return a && a.w + a.l + a.p ? `${a.w}–${a.l}${a.p ? `–${a.p}` : ''}` : null
})
</script>

<template>
  <button
    type="button"
    :class="['team', role, outcome, { selected, dimmed, pickem, static: readonly }]"
    :style="{ '--accent': accent }"
    :aria-pressed="selected"
    :aria-label="`Pick ${team ? team.location + ' ' + team.name : raw}, ${roleText} ${spreadText}`"
    :tabindex="readonly ? -1 : 0"
    @click="!readonly && $emit('select')"
  >
    <span class="strip">
      <span class="role">{{ roleText }}</span>
      <span class="sp">{{ spreadText }}</span>
    </span>

    <span class="body">
      <img v-if="team?.logo && !broken" :src="team.logo" :alt="team.abbr" class="logo" @error="broken = true" />
      <span v-else class="logo fallback">{{ (raw || '?').slice(0, 2).toUpperCase() }}</span>
      <span class="names">
        <span class="city">
          {{ city }}
          <span :class="['where', home ? 'home' : 'away']">{{ home ? '⌂ HOME' : '✈ AWAY' }}</span>
        </span>
        <span class="nick">{{ nick }}</span>
        <span v-if="team?.record || atsText" class="rec">
          <span v-if="team?.record" class="su" title="Overall record going into this game">{{ dash(team.record) }}</span>
          <span v-if="atsText" class="ats" title="Cover record against your sheet lines (weeks before this one)">ATS {{ atsText }}</span>
        </span>
      </span>
      <span v-if="score != null" class="score">{{ score }}</span>
      <span v-if="selected && !editing" :class="['check', { end: score == null }]" aria-hidden="true">{{ outcome === 'loss' ? '✗' : outcome === 'push' ? '=' : '✓' }}</span>
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
.check {
  flex: none; width: 22px; height: 22px; border-radius: 50%;
  display: grid; place-items: center; background: var(--accent); color: #fff; font-size: .8rem; font-weight: 800;
}
.check.end { margin-left: auto; }
.raw { font: inherit; font-size: .8rem; padding: 4px 6px; margin: 0 12px 10px; border: 1px dashed #94a3b8; border-radius: 6px; width: calc(100% - 24px); box-sizing: border-box; }
</style>
