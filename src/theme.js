// Light / dark / auto (follow the device). Kept per browser; index.html applies it before the app loads so a dark
// page doesn't flash white first.
import { ref, watch } from 'vue'

const KEY = 'theme'
const read = () => { try { return localStorage.getItem(KEY) } catch { return null } }
export const THEMES = [{ id: 'light', label: 'Light' }, { id: 'dark', label: 'Dark' }, { id: 'auto', label: 'Auto' }]
export const theme = ref(['light', 'dark'].includes(read()) ? read() : 'auto')

const darkMq = window.matchMedia('(prefers-color-scheme: dark)')
// whether the page is dark right now (Dark, or Auto on a dark device): for colors worked out in code, like team colors
export const isDark = ref(false)
function apply() {
  const root = document.documentElement
  if (theme.value === 'auto') delete root.dataset.theme
  else root.dataset.theme = theme.value
  const dark = theme.value === 'dark' || (theme.value === 'auto' && darkMq.matches)
  isDark.value = dark
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0b1120' : '#f1f5f9')
}
watch(theme, v => {
  try { v === 'auto' ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, v) } catch {}
  apply()
})
darkMq.addEventListener('change', apply)
apply()
