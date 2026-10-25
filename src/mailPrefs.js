import { reactive } from 'vue'
import { getMailPrefs, setMailPrefs } from './api.js'

// The player's email settings (stored on their account): how Send picks opens their email, their Gmail
// address for desktop Gmail, and their pool team name. Shared by the picks page and the account menu.
export const mailPrefs = reactive({ app: '', sender: '', teamName: '', loaded: false })

let loading
export function loadMailPrefs() {
  loading ??= getMailPrefs().then(p => {
    // the team name used to live only in this browser: bring it over the first time
    let local = ''
    try { local = localStorage.getItem('teamName') || '' } catch {}
    Object.assign(mailPrefs, p, { teamName: p.teamName || local, loaded: true })
  }).catch(() => { loading = null })
  return loading
}

export async function saveMailPrefs(prefs) {
  Object.assign(mailPrefs, prefs)
  const saved = await setMailPrefs({ app: mailPrefs.app, sender: mailPrefs.sender, teamName: mailPrefs.teamName })
  Object.assign(mailPrefs, saved)
  try { localStorage.removeItem('teamName') } catch {}
}
