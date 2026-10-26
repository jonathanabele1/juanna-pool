<script setup>
// A last look before Send picks opens the email: how many games are picked, the points used, where it's going.
import { computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  week: Number,
  gameCount: Number,     // games on the week's sheet
  saved: Array,          // every saved pick this week
  out: Array,            // the picks this email carries (games already kicked off went in an earlier one)
  to: String,            // this week's league address
  appLabel: String,      // Gmail / Outlook / Mail app, or '' when not chosen yet
  body: String,
  target: { type: Number, default: 100 },
})
const emit = defineEmits(['close', 'send', 'change'])

const points = computed(() => props.saved.reduce((s, g) => s + (Number(g.points) || 0), 0))
const allPicked = computed(() => props.saved.length === props.gameCount)
const pointsOk = computed(() => points.value === props.target)
const earlier = computed(() => props.saved.length - props.out.length)
const notes = computed(() => {
  const n = []
  const open = props.gameCount - props.saved.length
  if (open > 0) n.push(`${open} game${open > 1 ? 's' : ''} without a pick.`)
  if (points.value < props.target) n.push(`${props.target - points.value} points left to use.`)
  if (points.value > props.target) n.push(`${points.value - props.target} points over ${props.target}.`)
  if (props.saved.filter(g => Number(g.points) >= 10).length === 4) n.push('4 double-digit picks.')
  if (!props.to) n.push('No league address for this week yet, so add one in the email.')
  return n
})

const onKey = e => e.key === 'Escape' && emit('close')
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="send-title">
      <header>
        <h3 id="send-title">Send week {{ week }} picks?</h3>
        <button type="button" class="x" aria-label="Close" @click="emit('close')">✕</button>
      </header>

      <dl class="nums">
        <div :class="['num', allPicked ? 'good' : 'warn']">
          <dt>Picks</dt>
          <dd>{{ saved.length }}<small>/{{ gameCount }}</small></dd>
          <span>{{ allPicked ? '✓ every game' : 'not every game' }}</span>
        </div>
        <div :class="['num', pointsOk ? 'good' : 'warn']">
          <dt>Points</dt>
          <dd>{{ points }}<small>/{{ target }}</small></dd>
          <span>{{ pointsOk ? '✓ all in' : points < target ? `${target - points} left` : `${points - target} over` }}</span>
        </div>
      </dl>

      <ul v-if="notes.length" class="notes">
        <li v-for="n in notes" :key="n">{{ n }}</li>
      </ul>
      <p v-if="earlier > 0" class="sub">
        This email has the {{ out.length }} pick{{ out.length > 1 ? 's' : '' }} that haven’t kicked off.
        The other {{ earlier }} already started, so they went in an earlier email.
      </p>

      <dl class="route">
        <div><dt>To</dt><dd>{{ to || '—' }}</dd></div>
        <div>
          <dt>With</dt>
          <dd>{{ appLabel || 'Not chosen yet' }} <button v-if="appLabel" type="button" class="link" @click="emit('change')">Change</button></dd>
        </div>
      </dl>

      <details class="preview">
        <summary>Show the email</summary>
        <pre>{{ body }}</pre>
      </details>

      <p class="sub">It opens ready to go. You still press send, from your own email.</p>
      <footer>
        <button type="button" class="btn ghost" @click="emit('close')">Cancel</button>
        <button type="button" class="btn primary" @click="emit('send')">{{ appLabel ? `Open ${appLabel}` : 'Choose email app' }}</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; z-index: 50; display: grid; place-items: center; padding: 16px; background: #0f172a8c; backdrop-filter: blur(3px); }
.dialog { width: min(420px, 100%); max-height: calc(100dvh - 32px); overflow-y: auto; background: var(--card); border-radius: 20px; padding: 18px; box-shadow: 0 20px 60px #0006; display: flex; flex-direction: column; gap: 12px; animation: pop .16s ease-out; }
@keyframes pop { from { opacity: 0; transform: translateY(6px) scale(.98); } }
@media (prefers-reduced-motion: reduce) { .dialog { animation: none; } }
header { display: flex; justify-content: space-between; align-items: center; }
h3 { margin: 0; font-size: 1.1rem; }
.x { border: 0; background: var(--soft); width: 30px; height: 30px; border-radius: 50%; cursor: pointer; color: var(--text-2); }
.x:hover { background: var(--chip); }

.nums { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0; }
.num { display: flex; flex-direction: column; gap: 3px; padding: 12px 14px; border-radius: 14px; background: var(--card-2); border: 1px solid var(--line-soft); }
.num dt { font-size: .66rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--faint); }
.num dd { margin: 0; font-size: 1.9rem; font-weight: 800; line-height: 1.05; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.num dd small { font-size: 1rem; font-weight: 700; color: var(--faint); letter-spacing: 0; }
.num span { font-size: .74rem; font-weight: 700; }
.num.good { background: var(--green-tint); border-color: var(--green-line); }
.num.good span { color: var(--pos); }
.num.warn { background: var(--amber-tint); border-color: var(--amber-line); }
.num.warn span { color: var(--amber-ink); }

.notes { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: .84rem; font-weight: 600; color: var(--amber-ink); }
.notes li::before { content: '⚠︎ '; }
.sub { margin: 0; font-size: .82rem; color: var(--muted); }

.route { margin: 0; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.route div { display: flex; align-items: baseline; gap: 10px; padding: 9px 12px; }
.route div + div { border-top: 1px solid var(--line-soft); }
.route dt { flex: none; width: 38px; font-size: .74rem; font-weight: 700; color: var(--faint); }
.route dd { margin: 0; min-width: 0; font-size: .9rem; font-weight: 600; overflow-wrap: anywhere; }
.route .link { margin-left: 6px; font-size: .82rem; color: var(--blue); }

.preview summary { cursor: pointer; font-size: .84rem; font-weight: 700; color: var(--blue); }
.preview pre { margin: 8px 0 0; padding: 10px 12px; border-radius: 12px; background: var(--card-2); border: 1px solid var(--line-soft); font-family: ui-monospace, "SF Mono", monospace; font-size: .82rem; line-height: 1.45; white-space: pre-wrap; max-height: 220px; overflow-y: auto; }

footer { display: flex; justify-content: flex-end; gap: 8px; }
footer .btn { min-height: 44px; }
footer .btn.primary { flex: 1; }
</style>
