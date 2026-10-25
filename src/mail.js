// "Send picks": open the player's own email, already addressed to that week's league address with the picks
// filled in. It has to go out from their own mailbox: the league goes by when it was sent, and a disputed pick
// is settled by forwarding the original from Sent.

export const MAIL_APPS = [
  { id: 'gmail', label: 'Gmail' },
  { id: 'outlook', label: 'Outlook', note: 'outlook.com, Hotmail, Live' },
  { id: 'default', label: 'Mail app', note: 'Whatever this device opens email links with' },
]

export function platform(nav = globalThis.navigator) {
  const ua = nav?.userAgent || ''
  if (/android/i.test(ua)) return 'android'
  // iPadOS reports itself as a Mac: tell them apart by touch
  if (/iphone|ipad|ipod/i.test(ua) || (/macintosh/i.test(ua) && nav.maxTouchPoints > 1)) return 'ios'
  return 'desktop'
}

const q = params => Object.entries(params).filter(([, v]) => v)
  .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')
const crlf = s => s.replace(/\r?\n/g, '\r\n')  // mailto bodies want CRLF line breaks (RFC 6068)

export function mailtoUrl({ to, subject, body }) {
  return `mailto:${encodeURIComponent(to || '')}?${q({ subject, body: crlf(body) })}`
}

// Web compose pages: the desktop links, and where a phone falls back to when the app isn't installed.
export function webUrl(app, msg) {
  const { to, subject, body, sender } = msg
  // tf=cm: the full Gmail site (inbox, which account) with a filled-in compose window on top. view=cm and the
  // extsrc=mailto handler only give a bare compose page. /u/<address>/ opens that account, /u/0/ the first one.
  if (app === 'gmail') return `https://mail.google.com/mail/u/${encodeURIComponent(sender || '0')}/?${q({ to, su: subject, body, tf: 'cm' })}`
  if (app === 'outlook') return `https://outlook.live.com/mail/0/deeplink/compose?${q({ to, subject, body })}`
  return null
}

// Phone app links.
export function appUrl(app, os, msg) {
  const { to, subject, body } = msg
  if (app === 'gmail' && os === 'ios') return `googlegmail://co?${q({ to, subject, body })}`
  if (app === 'gmail' && os === 'android') {
    // Chrome opens a mailto in the Gmail app specifically, or the fallback page if Gmail isn't installed
    const data = mailtoUrl(msg).slice('mailto:'.length)
    return `intent:${data}#Intent;scheme=mailto;package=com.google.android.gm;` +
      `S.browser_fallback_url=${encodeURIComponent(webUrl('gmail', msg))};end`
  }
  if (app === 'outlook') return `ms-outlook://compose?${q({ to, subject, body })}`
  return null
}

// What one tap does: { url, newTab } to go to, plus a web page to fall back to if a phone app doesn't open.
export function sendPlan(app, os, msg) {
  if (app === 'default') return { url: mailtoUrl(msg) }
  if (os === 'desktop') return { url: webUrl(app, msg), newTab: true }
  const url = appUrl(app, os, msg)
  // Android's intent link carries its own fallback; iOS just doesn't open anything for an app that's missing
  return { url, fallback: os === 'ios' ? webUrl(app, msg) : null }
}

export function openMail(app, msg, os = platform()) {
  const plan = sendPlan(app, os, msg)
  if (plan.newTab) {
    // opened straight from the tap, so popup blockers allow it. Not the 'noopener' feature: with it, window.open
    // always returns null, so there'd be no telling whether the tab opened. This page never navigates away.
    const tab = window.open(plan.url, '_blank')
    if (tab) tab.opener = null
    return !!tab
  }
  if (plan.fallback) {
    // the page goes to the background when the app opens; if it's still showing, the app isn't there
    const timer = setTimeout(() => { if (document.visibilityState === 'visible') location.href = plan.fallback }, 1500)
    document.addEventListener('visibilitychange', () => clearTimeout(timer), { once: true })
  }
  location.href = plan.url
  return true
}
