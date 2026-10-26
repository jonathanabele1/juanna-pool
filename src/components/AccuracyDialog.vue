<script setup>
// The week's accuracy, picked apart: how it's worked out, then each final pick and how much it counted.
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  week: Number,
  pct: Number,      // the week's accuracy (server)
  rows: Array,      // final picks: [{ key, abbr, logo, pts, weight, how, acc }]
  pending: Number,  // picks still to play
})
const emit = defineEmits(['close'])

const totalWeight = computed(() => props.rows.reduce((t, r) => t + r.weight, 0))
const sorted = computed(() => [...props.rows].sort((a, b) => b.weight - a.weight || b.acc - a.acc))
const share = r => Math.round((100 * r.weight) / totalWeight.value)
const tone = a => (a >= 100 ? 'win' : a >= 50 ? 'mid' : 'loss')

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
      <section ref="panel" class="sheet" role="dialog" aria-modal="true" :aria-label="`Week ${week} accuracy`" tabindex="-1">
        <button class="x" aria-label="Close" @click="emit('close')">×</button>

        <header class="hd">
          <span class="k">Week {{ week }} accuracy</span>
          <b class="v">{{ Math.round(pct) }}%</b>
          <span class="track"><i :style="{ width: pct + '%' }"></i></span>
        </header>

        <div class="how">
          <h4>How it’s scored</h4>
          <ul class="rules">
            <li><span class="chip win">100%</span>Covered or push</li>
            <li><span class="chip mid">93%</span>Missed by 1</li>
            <li><span class="chip mid">50%</span>Missed by 7</li>
            <li><span class="chip loss">0%</span>Missed by 14 or more</li>
          </ul>
          <p>Each point you miss by takes off about 7%. Picks count by their points, so a 20 counts ten times a 2. Your lock counts as 20.</p>
        </div>

        <div class="list">
          <div class="lh"><span>Pick</span><span>Result</span><span class="r">Accuracy</span></div>
          <div v-for="r in sorted" :key="r.key" class="row">
            <span class="tm">
              <img v-if="r.logo" :src="r.logo" alt="" @error="$event.target.style.visibility = 'hidden'" />
              <b>{{ r.abbr }}</b>
              <span class="pts" :title="`Counts for ${share(r)}% of the week`">{{ r.pts }}</span>
            </span>
            <span class="res">{{ r.how }}</span>
            <span class="r"><b :class="['pa', tone(r.acc)]">{{ Math.round(r.acc) }}%</b></span>
          </div>
          <p v-if="pending" class="more">{{ pending }} {{ pending === 1 ? 'pick' : 'picks' }} still to play</p>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; z-index: 60; background: #0f172a66; display: grid; place-items: center; padding: 16px; }
.sheet {
  position: relative; width: min(420px, 100%); max-height: min(86vh, 720px); overflow: auto; background: var(--card);
  border-radius: 20px; box-shadow: 0 20px 50px #0f172a40; outline: none;
}
.x {
  position: absolute; top: 10px; right: 10px; z-index: 1; width: 32px; height: 32px; border: 0; border-radius: 50%;
  background: var(--soft); color: var(--text-2); font-size: 1.2rem; line-height: 1; cursor: pointer;
}
.x:hover { background: var(--chip); }

.hd { display: flex; flex-direction: column; gap: 6px; padding: 18px 18px 16px; }
.k { font-size: .66rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--faint); }
.v { font-size: 2.2rem; font-weight: 800; line-height: 1; letter-spacing: -.03em; color: var(--text); font-variant-numeric: tabular-nums; }
.track { height: 8px; margin-top: 4px; background: var(--soft); border-radius: 99px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--blue); border-radius: 99px; }

.how { padding: 12px 18px 14px; background: var(--card-2); border-top: 1px solid var(--line-soft); border-bottom: 1px solid var(--line-soft); }
h4 { margin: 0 0 8px; font-size: .66rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--faint); }
.rules { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rules li { display: flex; align-items: center; gap: 10px; font-size: .84rem; color: var(--text-2); }
.how p { margin: 10px 0 0; font-size: .8rem; color: var(--muted); line-height: 1.4; }
.chip { flex: none; min-width: 52px; text-align: center; padding: 2px 6px; border-radius: 6px; font-size: .74rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.chip.win { background: var(--green-tint); color: var(--pos); }
.chip.mid { background: var(--amber-tint); color: var(--amber-ink); }
.chip.loss { background: var(--red-tint); color: var(--neg); }

.list { padding: 6px 18px 16px; }
.lh, .row { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) 64px; align-items: center; gap: 8px; }
.lh { padding: 8px 0 6px; font-size: .62rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--faint); }
.row { min-height: 44px; border-top: 1px solid var(--line-soft); }
.r { text-align: right; }
.tm { display: flex; align-items: center; gap: 8px; min-width: 0; }
.tm img { width: 24px; height: 24px; object-fit: contain; flex: none; }
.tm b { font-size: .9rem; font-weight: 800; }
.pts { padding: 1px 7px; border-radius: 99px; background: var(--soft); color: var(--text-2); font-size: .72rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.res { font-size: .82rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pa { font-size: .95rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.pa.win { color: var(--pos); } .pa.mid { color: var(--amber-ink); } .pa.loss { color: var(--neg); }
.more { margin: 0; padding: 10px 0 0; border-top: 1px solid var(--line-soft); font-size: .8rem; color: var(--faint); }
</style>
