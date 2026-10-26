<script setup>
// The week's accuracy, picked apart: how it's worked out, then each final pick (and each one on now, as it stands)
// and how much it counted.
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  week: Number,
  pct: Number,      // the week's accuracy (server): final picks only, null until one is final
  livePct: Number,  // with the games on now counted as they stand (null while nothing's on)
  rows: Array,      // final picks: [{ key, abbr, logo, pts, weight, how, acc }]
  pending: Number,  // picks still to play
  who: String,      // another player's name, when it's their week
})
const emit = defineEmits(['close'])

const totalWeight = computed(() => props.rows.reduce((t, r) => t + r.weight, 0))
const sorted = computed(() => [...props.rows].sort((a, b) => b.weight - a.weight || b.acc - a.acc))
const share = r => Math.round((100 * r.weight) / totalWeight.value)
// the big number: final picks, or (before any is final) the live one
const shown = computed(() => props.pct ?? props.livePct)
const toPlay = computed(() => Math.max(0, (props.pending || 0) - props.rows.filter(r => r.live).length))
const tone = a => (a >= 100 ? 'win' : a >= 50 ? 'mid' : 'loss')

const panel = ref(null)
const rules = ref(false)     // the "how it's scored" key: behind the book button
const outside = ref(false)
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
    <!-- a tap anywhere outside the sheet closes it (only one that starts outside too, so a drag out of the list doesn't) -->
    <div class="scrim" @pointerdown.self="outside = true" @click.self="outside && emit('close')">
      <section ref="panel" class="sheet" role="dialog" aria-modal="true" :aria-label="`${who ? who + ', ' : ''}Week ${week} accuracy`" tabindex="-1">
        <!-- pinned: the title, the number and the close button stay put while the picks scroll -->
        <header class="hd">
          <div class="hd-top">
            <span class="k"><template v-if="who">{{ who }} · </template>Week {{ week }} accuracy</span>
            <button type="button" :class="['ib', { on: rules }]" :aria-pressed="rules" aria-label="How it's scored" title="How it's scored" @click="rules = !rules">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H15v12H5.5A1.5 1.5 0 0 0 4 16.5zM4 16.5A1.5 1.5 0 0 0 5.5 18H15v-3" /><path d="M7.5 7h4.5M7.5 10h3" /></svg>
            </button>
            <button type="button" class="ib x" aria-label="Close" @click="emit('close')">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5.5 5.5l9 9M14.5 5.5l-9 9" /></svg>
            </button>
          </div>
          <div class="vrow">
            <b :class="['v', { lv: pct == null }]">{{ Math.round(shown) }}%</b>
            <span v-if="livePct != null && pct != null" class="live-v" title="If the games on now ended as they stand"><i class="ldot"></i>{{ Math.round(livePct) }}%</span>
          </div>
          <span class="track"><i :style="{ width: shown + '%' }"></i></span>
        </header>

        <div class="body">
          <div v-if="rules" class="how">
            <h4>How it’s scored</h4>
            <ul class="rules">
              <li><span class="chip win">100%</span>Covered or push</li>
              <li><span class="chip mid">93%</span>Missed by 1</li>
              <li><span class="chip mid">50%</span>Missed by 7</li>
              <li><span class="chip loss">0%</span>Missed by 14 or more</li>
            </ul>
            <p>Each point you miss by takes off about 7%. Picks count by their points, so a 20 counts ten times a 2. The lock counts as 20.</p>
          </div>

          <div class="list">
            <div class="lh"><span>Pick</span><span>Result</span><span class="r">Accuracy</span></div>
            <div v-for="r in sorted" :key="r.key" class="row">
              <span class="tm">
                <img v-if="r.logo" :src="r.logo" alt="" @error="$event.target.style.visibility = 'hidden'" />
                <b>{{ r.abbr }}</b>
                <span class="pts" :title="`Counts for ${share(r)}% of the week`">{{ r.pts }}</span>
              </span>
              <span :class="['res', { lv: r.live }]">{{ r.how }}</span>
              <span class="r"><b :class="['pa', tone(r.acc)]">{{ Math.round(r.acc) }}%</b></span>
            </div>
            <p v-if="toPlay" class="more">{{ toPlay }} {{ toPlay === 1 ? 'pick' : 'picks' }} still to play</p>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; z-index: 60; background: #0f172a66; display: grid; place-items: center; padding: 16px; cursor: pointer; }
.sheet {
  position: relative; width: min(420px, 100%); max-height: min(86vh, 720px); display: flex; flex-direction: column; overflow: hidden;
  background: var(--card); border-radius: 20px; box-shadow: 0 20px 50px #0f172a40; outline: none; cursor: auto;
}

.hd { flex: none; display: flex; flex-direction: column; gap: 6px; padding: 12px 18px 14px; border-bottom: 1px solid var(--line-soft); background: var(--card); }
.hd-top { display: flex; align-items: center; gap: 8px; }
.k { flex: 1; min-width: 0; font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ib {
  flex: none; width: 36px; height: 36px; display: grid; place-items: center; padding: 0; border: 1px solid var(--line); border-radius: 50%;
  background: var(--soft); color: var(--text-2); cursor: pointer; transition: background .15s, color .15s, border-color .15s;
}
.ib svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.ib:hover { background: var(--chip); color: var(--text); }
.ib:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }
.ib.on { background: var(--blue-tint); border-color: var(--blue-line); color: var(--blue); }
/* close: solid, so it's the first thing you see */
.ib.x { background: var(--ink); border-color: var(--ink); color: var(--on-ink); }
.ib.x svg { stroke-width: 2.2; }
.ib.x:hover { background: var(--ink); opacity: .85; color: var(--on-ink); }
.vrow { display: flex; align-items: baseline; gap: 10px; }
.v { font-size: 2.2rem; font-weight: 800; line-height: 1; letter-spacing: -.03em; color: var(--text); font-variant-numeric: tabular-nums; }
.v.lv { color: var(--neg); }
.live-v { display: inline-flex; align-items: center; gap: 6px; font-size: 1rem; font-weight: 800; color: var(--neg); font-variant-numeric: tabular-nums; }
.track { height: 8px; margin-top: 2px; background: var(--soft); border-radius: 99px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--blue); border-radius: 99px; }

.body { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.how { padding: 12px 18px 14px; background: var(--card-2); border-bottom: 1px solid var(--line-soft); }
h4 { margin: 0 0 8px; font-size: .66rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--faint); }
.rules { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rules li { display: flex; align-items: center; gap: 10px; font-size: .84rem; color: var(--text-2); }
.how p { margin: 10px 0 0; font-size: .8rem; color: var(--muted); line-height: 1.4; }
.chip { flex: none; min-width: 52px; text-align: center; padding: 2px 6px; border-radius: 6px; font-size: .74rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.chip.win { background: var(--green-tint); color: var(--pos); }
.chip.mid { background: var(--amber-tint); color: var(--amber-ink); }
.chip.loss { background: var(--red-tint); color: var(--neg); }

.list { padding: 0 18px 16px; }
.lh, .row { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) 64px; align-items: center; gap: 8px; }
.lh { position: sticky; top: 0; z-index: 1; background: var(--card); padding: 10px 0 8px; border-bottom: 1px solid var(--line-soft); font-size: .62rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--faint); }
.row { min-height: 44px; border-top: 1px solid var(--line-soft); }
.lh + .row { border-top: 0; }
.r { text-align: right; }
.tm { display: flex; align-items: center; gap: 8px; min-width: 0; }
.tm img { width: 24px; height: 24px; object-fit: contain; flex: none; }
.tm b { font-size: .9rem; font-weight: 800; }
.pts { padding: 1px 7px; border-radius: 99px; background: var(--soft); color: var(--text-2); font-size: .72rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.res { font-size: .82rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res.lv { color: var(--neg); font-weight: 600; }
.pa { font-size: .95rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.pa.win { color: var(--pos); } .pa.mid { color: var(--amber-ink); } .pa.loss { color: var(--neg); }
.more { margin: 0; padding: 10px 0 0; border-top: 1px solid var(--line-soft); font-size: .8rem; color: var(--faint); }
</style>
