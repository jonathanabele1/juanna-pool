<script setup>
// Everyone's pick on one game: a mini scoreboard, the pool/public split, then one list grouped by side.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { pct, teamColors, textColor } from '../pool.js'
import { isDark } from '../theme.js'

const props = defineProps({
  sides: Array,      // [{ key, abbr, name, logo, spread, color, alternateColor }] in display order (away, home)
  pool: Object,      // { fav: {count, points}, dog, none, picks: [{ id, name, me, pick, points, outcome, live, earned }] }
  split: Object,     // DraftKings public betting, if any
  status: String,    // "Final", "Q3 · 4:12", ...
  scores: Object,    // { fav, dog } when known
})
const emit = defineEmits(['close'])

const colors = computed(() => teamColors(...props.sides, isDark.value))
const ink = i => textColor(colors.value[i], isDark.value)
const picked = computed(() => props.pool.fav.count + props.pool.dog.count)
const poolPct = computed(() => props.sides.map(s => pct(props.pool[s.key].count, picked.value)))
const pub = computed(() => {
  const rows = props.sides.map(s => props.split?.sides?.[s.abbr])
  return rows.every(r => r?.bets != null) ? rows : null
})
const groups = computed(() => props.sides.map((s, i) => ({
  ...s, color: colors.value[i], count: props.pool[s.key].count, points: props.pool[s.key].points,
  picks: props.pool.picks.filter(p => p.pick === s.key),
})))
const none = computed(() => props.pool.picks.filter(p => !p.pick))
const anyLive = computed(() => props.pool.picks.some(p => p.live))
// once it's final, the losing score goes gray (like the game card)
const leader = computed(() => {
  if (!/final/i.test(props.status || '')) return null
  const [a, b] = props.sides.map(s => props.scores?.[s.key])
  return a == null || b == null || a === b ? null : a > b ? 0 : 1
})

// one pill per player: their points, colored by how the pick did
const num = n => String(n).replace('.5', '½')
function pill(p) {
  if (p.outcome === 'win') return { cls: 'win', mark: '✓', title: `Covered: +${num(p.earned)}` }
  if (p.outcome === 'loss') return { cls: 'loss', mark: '✗', title: 'Missed' }
  if (p.outcome === 'push') return { cls: 'push', mark: '=', title: `Push: +${num(p.earned)}` }
  if (p.live === 'win') return { cls: 'live-win', mark: '', title: 'Covering right now' }
  if (p.live === 'loss') return { cls: 'live-loss', mark: '', title: 'Not covering right now' }
  if (p.live === 'push') return { cls: 'push', mark: '', title: 'On the number right now' }
  return { cls: '', mark: '', title: '' }
}

const panel = ref(null)
const onKey = e => { if (e.key === 'Escape') emit('close') }
onMounted(() => {
  document.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
  panel.value?.focus()
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div class="scrim" @click.self="emit('close')">
      <section ref="panel" class="sheet" role="dialog" aria-modal="true" :aria-label="`Pool picks: ${sides[0].name} at ${sides[1].name}`" tabindex="-1">
        <button class="x" aria-label="Close" @click="emit('close')">×</button>

        <!-- mini scoreboard -->
        <header class="board">
          <div v-for="(s, i) in sides" :key="s.key" :class="['team', i ? 'home' : 'away', { trail: leader !== null && leader !== i }]">
            <img v-if="s.logo" :src="s.logo" alt="" @error="$event.target.style.visibility = 'hidden'" />
            <span class="tn"><b>{{ s.abbr }}</b><small>{{ s.spread }}</small></span>
            <span v-if="scores?.[s.key] != null" class="sc">{{ scores[s.key] }}</span>
          </div>
          <span class="st">{{ status || '@' }}</span>
        </header>

        <!-- the split -->
        <div class="split">
          <div class="ln">
            <span class="lbl">Pool</span>
            <b :style="{ color: ink(0) }">{{ poolPct[0] }}%</b>
            <span class="pbar"><i :style="{ flexGrow: picked ? poolPct[0] : 1, background: colors[0] }"></i><i :style="{ flexGrow: picked ? poolPct[1] : 1, background: colors[1] }"></i></span>
            <b class="r" :style="{ color: ink(1) }">{{ poolPct[1] }}%</b>
          </div>
          <div v-if="pub" class="ln" :title="`% of money: ${sides[0].abbr} ${pub[0].handle}%, ${sides[1].abbr} ${pub[1].handle}%`">
            <span class="lbl">Public</span>
            <b :style="{ color: ink(0) }">{{ pub[0].bets }}%</b>
            <span class="pbar"><i :style="{ flexGrow: pub[0].bets, background: colors[0] }"></i><i :style="{ flexGrow: pub[1].bets, background: colors[1] }"></i></span>
            <b class="r" :style="{ color: ink(1) }">{{ pub[1].bets }}%</b>
          </div>
        </div>

        <!-- everyone, by side -->
        <div class="list">
          <section v-for="g in groups" :key="g.key" class="grp">
            <h4 :style="{ '--c': g.color }">
              <img v-if="g.logo" :src="g.logo" alt="" @error="$event.target.style.visibility = 'hidden'" />
              {{ g.name }}
              <small>{{ g.count }} {{ g.count === 1 ? 'player' : 'players' }}<template v-if="g.count"> · {{ g.points }} pts</template></small>
            </h4>
            <ul v-if="g.picks.length">
              <li v-for="p in g.picks" :key="p.id" :class="{ me: p.me }">
                <span class="nm">{{ p.name }}<em v-if="p.me">you</em></span>
                <span :class="['pt', pill(p).cls, { loy: p.points === 50 }]" :title="pill(p).title">
                  {{ p.points === 50 ? '★ 50' : p.points }}<i v-if="pill(p).mark">{{ pill(p).mark }}</i>
                </span>
              </li>
            </ul>
            <p v-else class="nobody">Nobody</p>
          </section>
          <section v-if="none.length" class="grp">
            <h4>No pick <small>{{ none.length }} · −20 each</small></h4>
            <ul>
              <li v-for="p in none" :key="p.id" :class="{ me: p.me }">
                <span class="nm">{{ p.name }}<em v-if="p.me">you</em></span>
              </li>
            </ul>
          </section>
          <p v-if="anyLive" class="legend">
            <span><i class="pt live-win"></i>covering now</span>
            <span><i class="pt live-loss"></i>not covering now</span>
          </p>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; z-index: 60; background: #0f172a66; display: grid; place-items: center; padding: 16px; }
.sheet {
  position: relative; width: min(440px, 100%); max-height: min(86vh, 720px); overflow: auto; background: var(--card);
  border-radius: 20px; box-shadow: 0 20px 50px #0f172a40; outline: none;
}
.x {
  position: absolute; top: 10px; right: 10px; z-index: 1; width: 32px; height: 32px; border: 0; border-radius: 50%;
  background: var(--soft); color: var(--text-2); font-size: 1.2rem; line-height: 1; cursor: pointer;
}
.x:hover { background: var(--chip); }

/* mini scoreboard */
.board { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 8px; padding: 18px 52px 14px; }
.team { display: flex; align-items: center; gap: 8px; min-width: 0; }
.team.home { grid-column: 3; flex-direction: row-reverse; }
.team.away { grid-column: 1; grid-row: 1; }
.team img { width: 34px; height: 34px; object-fit: contain; flex: none; }
.tn { display: flex; flex-direction: column; line-height: 1.1; }
.home .tn { align-items: flex-end; }
.tn b { font-size: .95rem; font-weight: 800; }
.tn small { font-size: .72rem; font-weight: 700; color: var(--faint); font-variant-numeric: tabular-nums; }
.sc { margin: 0 2px; font-size: 1.6rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.away .sc { margin-left: auto; } .home .sc { margin-right: auto; }
.trail .sc { color: var(--faint); }
.st { grid-column: 2; grid-row: 1; font-size: .68rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); white-space: nowrap; }

/* split bars (same look as the game card) */
.split { padding: 10px 18px 12px; border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); background: var(--card-2); display: flex; flex-direction: column; gap: 4px; }
.ln { display: grid; grid-template-columns: 48px 40px minmax(0, 1fr) 40px; align-items: center; gap: 8px; min-height: 22px; }
.ln .lbl { font-size: .6rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--faint); }
.ln b { font-size: .8rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.ln b.r { text-align: right; }
.pbar { display: flex; gap: 2px; height: 6px; border-radius: 99px; overflow: hidden; }
.pbar i { flex: 1 1 0; min-width: 0; }

/* list */
.list { padding: 6px 18px 18px; }
.grp + .grp { margin-top: 6px; }
h4 {
  display: flex; align-items: center; gap: 8px; margin: 10px 0 2px; padding-left: 10px;
  border-left: 3px solid var(--c, var(--line-strong)); font-size: .86rem; font-weight: 800; color: var(--text);
}
h4 img { width: 20px; height: 20px; object-fit: contain; }
h4 small { margin-left: auto; font-size: .72rem; font-weight: 600; color: var(--faint); }
ul { list-style: none; margin: 0; padding: 0; }
li { display: flex; align-items: center; gap: 10px; padding: 7px 10px 7px 13px; border-radius: 10px; font-size: .9rem; }
li.me { background: var(--blue-tint); }
.nm { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.nm em { font-style: normal; font-size: .58rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; background: #2563eb; color: #fff; padding: 1px 6px; border-radius: 99px; margin-left: 6px; vertical-align: 2px; }
.nobody { margin: 0; padding: 6px 13px; font-size: .8rem; color: var(--faintest); }

.pt {
  display: inline-flex; align-items: center; gap: 4px; min-width: 44px; justify-content: center;
  padding: 2px 10px; border-radius: 99px; background: var(--soft); color: var(--text);
  font-size: .8rem; font-weight: 800; font-variant-numeric: tabular-nums;
}
.pt i { font-style: normal; font-size: .72rem; }
.pt.win { background: var(--green-tint); color: var(--pos); }
.pt.loss { background: var(--red-tint); color: var(--neg); }
.pt.push { background: var(--amber-tint); color: var(--amber-ink); }
.pt.live-win { background: var(--green-tint); color: var(--pos); box-shadow: inset 0 0 0 1px #86efac; }
.pt.live-loss { background: var(--red-tint); color: var(--neg); box-shadow: inset 0 0 0 1px #fca5a5; }
.legend { display: flex; gap: 14px; margin: 12px 0 0; padding-left: 13px; font-size: .72rem; color: var(--faint); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend .pt { min-width: 0; width: 18px; height: 10px; padding: 0; }
.pt.loy { box-shadow: inset 0 0 0 2px #eab308; }

@media (max-width: 560px) {
  .scrim { place-items: end stretch; padding: 0; }
  .sheet { width: 100%; max-height: 88vh; border-radius: 20px 20px 0 0; padding-bottom: env(safe-area-inset-bottom); }
  .board { padding: 16px 44px 12px; }
  .split { padding: 10px 16px 12px; }
  .list { padding: 4px 16px 18px; }
}
</style>
