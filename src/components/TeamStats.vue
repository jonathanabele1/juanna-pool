<script setup>
import { computed, ref } from 'vue'

const props = defineProps({ teams: Array, mine: { type: Boolean, default: true } })

const query = ref('')
const onlyBacked = ref(false)
const sortKey = ref('name')
const sortDir = ref(1)
const open = ref(new Set())

const total = o => o.w + o.l + (o.p || 0)
const pct = o => (o.w + o.l ? o.w / (o.w + o.l) : null)
const rec = o => `${o.w}–${o.l}${o.p ? `–${o.p}` : ''}`
const sgn = n => (n > 0 ? `+${n}` : `${n}`)
const tone = p => (p == null ? '' : p > 0.5 ? 'up' : p < 0.5 ? 'down' : 'even')
const pctText = p => (p == null ? '' : `${Math.round(p * 100)}%`)

const SORTS = {
  name: t => t.name,
  ats: t => pct(t.ats) ?? -1,
  backing: t => pct(t.backing) ?? -1,
  backingN: t => t.backing.n,
  net: t => t.backing.net,
  fading: t => pct(t.fading) ?? -1,
}
function sortBy(k) {
  if (sortKey.value === k) sortDir.value *= -1
  else { sortKey.value = k; sortDir.value = k === 'name' ? 1 : -1 }
}
const arrow = k => (sortKey.value === k ? (sortDir.value > 0 ? '▲' : '▼') : '')

const rows = computed(() => {
  const q = query.value.trim().toLowerCase()
  const f = SORTS[sortKey.value]
  return props.teams
    .filter(t => (!q || t.name.toLowerCase().includes(q) || t.abbr.toLowerCase() === q) && (!onlyBacked.value || t.backing.n))
    .sort((a, b) => {
      const x = f(a), y = f(b)
      const c = typeof x === 'string' ? x.localeCompare(y) : x - y
      return (c || a.name.localeCompare(b.name)) * sortDir.value
    })
})

// Highlights, only for teams with enough games to mean something
const callouts = computed(() => {
  const t = props.teams
  const best = (list, key, dir = -1) => [...list].sort((a, b) => (key(a) - key(b)) * dir)[0]
  const backed = t.filter(x => x.backing.n >= 2)
  const covered = t.filter(x => x.games >= 3)
  const out = []
  const add = (label, team, value, kind) => team && out.push({ label, team, value, kind })
  const bb = best(backed, x => (pct(x.backing) ?? 0) * 1000 + x.backing.net / 100)
  add(props.mine ? 'You read best' : 'Reads best', bb, `${rec(bb?.backing || {})} · ${sgn(bb?.backing.net)} pts`, 'good')
  const wb = best(backed, x => (pct(x.backing) ?? 0) * 1000 + x.backing.net / 100, 1)
  if (wb && wb !== bb) add(props.mine ? 'Burns you most' : 'Burns them most', wb, `${rec(wb.backing)} · ${sgn(wb.backing.net)} pts`, 'bad')
  const mb = best(t.filter(x => x.backing.n >= 2), x => x.backing.n)
  if (mb) add('Most backed', mb, `${mb.backing.n} picks · avg ${mb.backing.avgPts} pts`, 'neutral')
  const bc = best(covered, x => (pct(x.ats) ?? 0) * 1000 + x.games)
  add('Best at covering', bc, `${rec(bc?.ats || {})} ATS`, 'good')
  const wc = best(covered, x => (pct(x.ats) ?? 0) * 1000 - x.games, 1)
  if (wc && wc !== bc) add('Worst at covering', wc, `${rec(wc.ats)} ATS`, 'bad')
  return out
})

function toggle(abbr) {
  const s = new Set(open.value)
  s.has(abbr) ? s.delete(abbr) : s.add(abbr)
  open.value = s
}
</script>

<template>
  <section class="card teams">
    <div class="head">
      <div>
        <h3>By team</h3>
        <p class="note">
          <template v-if="mine">
            <b>Covers</b> = how each team has done against <em>your sheet lines</em> (every game on the weeks you’ve saved).
            <b>Backing</b> = your picks on that team to cover; <b>Fading</b> = your picks on their opponent.
          </template>
          <template v-else>
            <b>Covers</b> = how each team has done against the sheet lines (weeks this player saved).
            <b>Backing</b> = their picks on that team to cover; <b>Fading</b> = their picks on the opponent.
          </template>
        </p>
      </div>
    </div>

    <div v-if="callouts.length" class="callouts">
      <div v-for="c in callouts" :key="c.label" :class="['co', c.kind]">
        <img :src="c.team.logo" :alt="c.team.abbr" @error="$event.target.style.visibility = 'hidden'" />
        <div>
          <span class="cl">{{ c.label }}</span>
          <b>{{ c.team.short }}</b>
          <span class="cv">{{ c.value }}</span>
        </div>
      </div>
    </div>

    <div class="controls">
      <input v-model="query" type="search" placeholder="Find a team…" aria-label="Find a team" />
      <label class="chk"><input type="checkbox" v-model="onlyBacked" /> Only teams {{ mine ? 'I’ve' : 'they’ve' }} backed</label>
      <span class="count">{{ rows.length }} team{{ rows.length === 1 ? '' : 's' }}</span>
    </div>

    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th class="tcol"><button @click="sortBy('name')">Team {{ arrow('name') }}</button></th>
            <th><button @click="sortBy('ats')" title="Team's record covering your sheet lines">Covers {{ arrow('ats') }}</button></th>
            <th><button @click="sortBy('backing')" title="Your record when you picked this team to cover">Backing {{ arrow('backing') }}</button></th>
            <th><button @click="sortBy('net')" title="Points won minus points lost on picks backing this team">Net pts {{ arrow('net') }}</button></th>
            <th><button @click="sortBy('fading')" title="Your record when you picked their opponent">Fading {{ arrow('fading') }}</button></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="t in rows" :key="t.abbr">
            <tr :class="{ opened: open.has(t.abbr) }" @click="toggle(t.abbr)" tabindex="0" @keydown.enter="toggle(t.abbr)">
              <td class="tcol">
                <span class="tn">
                  <img :src="t.logo" :alt="t.abbr" @error="$event.target.style.visibility = 'hidden'" />
                  <span><b>{{ t.short }}</b><small>{{ t.games }} game{{ t.games === 1 ? '' : 's' }}</small></span>
                </span>
              </td>
              <td>
                <span :class="['rec', tone(pct(t.ats))]">{{ rec(t.ats) }}</span>
                <span class="mini"><span :style="{ width: (pct(t.ats) ?? 0) * 100 + '%' }"></span></span>
              </td>
              <td>
                <template v-if="t.backing.n">
                  <span :class="['rec', tone(pct(t.backing))]">{{ rec(t.backing) }}</span>
                  <small class="pc">{{ pctText(pct(t.backing)) }}</small>
                </template>
                <span v-else class="none">—</span>
              </td>
              <td>
                <b v-if="t.backing.n" :class="['net', t.backing.net > 0 ? 'up' : t.backing.net < 0 ? 'down' : '']">{{ sgn(t.backing.net) }}</b>
                <span v-else class="none">—</span>
              </td>
              <td>
                <template v-if="t.fading.n">
                  <span :class="['rec', tone(pct(t.fading))]">{{ rec(t.fading) }}</span>
                  <small class="pc">{{ sgn(t.fading.net) }} pts</small>
                </template>
                <span v-else class="none">—</span>
              </td>
            </tr>
            <tr v-if="open.has(t.abbr)" class="detail">
              <td colspan="5">
                <div class="dgrid">
                  <span>Straight up <b>{{ t.su.w }}–{{ t.su.l }}{{ t.su.t ? `–${t.su.t}` : '' }}</b></span>
                  <span>Covers as favorite <b>{{ total(t.asFav) ? rec(t.asFav) : '—' }}</b></span>
                  <span>Covers as underdog <b>{{ total(t.asDog) ? rec(t.asDog) : '—' }}</b></span>
                  <span>Avg confidence backing <b>{{ t.backing.avgPts ?? '—' }}</b></span>
                  <span>Picks on them / against <b>{{ t.backing.n }} / {{ t.fading.n }}</b></span>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!rows.length"><td colspan="5" class="none empty">No teams match.</td></tr>
        </tbody>
      </table>
    </div>
    <p class="note">Tap a team for more. Pushes don’t count toward percentages.</p>
  </section>
</template>

<style scoped>
.card { background: var(--card); border-radius: 16px; padding: 14px 16px; box-shadow: 0 1px 2px #0000000d; }
h3 { margin: 0 0 4px; font-size: .95rem; }
.note { font-size: .75rem; color: var(--faint); margin: 4px 0 0; line-height: 1.4; }
.note b { color: var(--muted); }

.callouts { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; margin: 12px 0; }
.co { display: flex; align-items: center; gap: 10px; padding: 9px 11px; border-radius: 12px; background: var(--card-2); border: 1px solid var(--line); }
.co.good { background: var(--green-tint); border-color: var(--green-line); }
.co.bad { background: var(--red-tint); border-color: var(--red-line); }
.co img { width: 34px; height: 34px; object-fit: contain; flex: none; }
.co div { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
.cl { font-size: .62rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 700; }
.co b { font-size: .95rem; }
.cv { font-size: .75rem; color: var(--text-2); }

.controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 6px 0 8px; }
.controls input[type=search] { flex: 1 1 180px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 10px; font: inherit; }
.chk { display: flex; gap: 6px; align-items: center; font-size: .82rem; color: var(--text-2); cursor: pointer; }
.count { font-size: .78rem; color: var(--faint); margin-left: auto; }

.scroll { overflow-x: auto; border: 1px solid var(--line-soft); border-radius: 12px; max-height: 70vh; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; min-width: 520px; font-size: .85rem; }
th { position: sticky; top: 0; z-index: 2; background: var(--card-2); text-align: left; padding: 0; border-bottom: 1px solid var(--line); }
th button { width: 100%; text-align: left; border: 0; background: none; font: inherit; font-size: .7rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); padding: 9px 10px; cursor: pointer; white-space: nowrap; }
th button:hover { color: var(--text); }
td { padding: 8px 10px; border-top: 1px solid var(--line-soft); vertical-align: middle; white-space: nowrap; }
tbody tr:not(.detail) { cursor: pointer; }
tbody tr:not(.detail):hover, tr.opened { background: var(--card-2); }
.tcol { position: sticky; left: 0; background: inherit; z-index: 1; }
th.tcol { z-index: 3; background: var(--card-2); }
td.tcol { background: var(--card); }
tr:hover td.tcol, tr.opened td.tcol { background: var(--card-2); }
.tn { display: flex; align-items: center; gap: 9px; }
.tn img { width: 30px; height: 30px; object-fit: contain; flex: none; }
.tn span { display: flex; flex-direction: column; line-height: 1.15; }
.tn small { font-size: .68rem; color: var(--faint); }

.rec { font-weight: 800; font-variant-numeric: tabular-nums; }
.rec.up, .net.up { color: var(--pos); } .rec.down, .net.down { color: var(--neg); } .rec.even { color: var(--text-2); }
.pc { margin-left: 6px; color: var(--faint); font-size: .72rem; }
.mini { display: inline-block; vertical-align: middle; width: 38px; height: 5px; background: var(--soft); border-radius: 9px; margin-left: 8px; overflow: hidden; }
.mini span { display: block; height: 100%; background: #16a34a; }
.none { color: var(--faintest); }
.empty { text-align: center; padding: 22px; }
.detail td { background: var(--card-2); border-top: 0; white-space: normal; }
.dgrid { display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: .8rem; color: var(--muted); }
.dgrid b { color: var(--text); margin-left: 4px; }
</style>
