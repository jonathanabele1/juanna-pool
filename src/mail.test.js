import { test } from 'node:test'
import assert from 'node:assert/strict'
import { platform, mailtoUrl, sendPlan, openMail } from './mail.js'

const msg = { to: 'pool@example.com', subject: 'Week 8 picks', body: 'Week 8.\nBills 10\nJets & Co 5', sender: 'me@gmail.com' }
const params = url => new URL(url.replace(/^[a-z-]+:\/\/co\?/, 'https://x/?')).searchParams

test('platform tells phones from desktops', () => {
  assert.equal(platform({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)' }), 'ios')
  assert.equal(platform({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', maxTouchPoints: 5 }), 'ios')
  assert.equal(platform({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', maxTouchPoints: 0 }), 'desktop')
  assert.equal(platform({ userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8)' }), 'android')
})

test('mailto keeps the address and uses CRLF line breaks', () => {
  const url = mailtoUrl(msg)
  assert.ok(url.startsWith('mailto:pool%40example.com?subject=Week%208%20picks&body='))
  assert.ok(url.includes('Week%208.%0D%0ABills%2010%0D%0AJets%20%26%20Co%205'))
})

test('desktop Gmail opens the full Gmail site, on the right account, in a new tab', () => {
  const plan = sendPlan('gmail', 'desktop', msg)
  assert.equal(plan.newTab, true)
  const u = new URL(plan.url)
  assert.equal(u.origin + decodeURIComponent(u.pathname), 'https://mail.google.com/mail/u/me@gmail.com/')
  assert.equal(u.searchParams.get('tf'), 'cm')
  assert.ok(!u.searchParams.has('view') && !u.searchParams.has('fs'))  // those give the bare compose page
  assert.equal(u.searchParams.get('to'), 'pool@example.com')
  assert.equal(u.searchParams.get('su'), 'Week 8 picks')
  assert.equal(u.searchParams.get('body'), msg.body)
})

test('desktop Gmail without a saved address opens the first signed-in account', () => {
  assert.equal(new URL(sendPlan('gmail', 'desktop', { ...msg, sender: '' }).url).pathname, '/mail/u/0/')
})

test('iPhone Gmail uses the app and falls back to the web', () => {
  const plan = sendPlan('gmail', 'ios', msg)
  assert.ok(plan.url.startsWith('googlegmail://co?'))
  assert.equal(params(plan.url).get('body'), msg.body)
  assert.ok(plan.fallback.startsWith('https://mail.google.com/'))
})

test('Android Gmail targets the Gmail app with a fallback page', () => {
  const { url } = sendPlan('gmail', 'android', msg)
  assert.ok(url.startsWith('intent:pool%40example.com?subject='))
  assert.ok(url.includes('#Intent;scheme=mailto;package=com.google.android.gm;S.browser_fallback_url=https%3A%2F%2Fmail.google.com'))
  assert.ok(url.endsWith(';end'))
})

test('Outlook: app on phones, outlook.com on desktop', () => {
  assert.ok(sendPlan('outlook', 'ios', msg).url.startsWith('ms-outlook://compose?'))
  assert.ok(sendPlan('outlook', 'android', msg).url.startsWith('ms-outlook://compose?'))
  assert.ok(sendPlan('outlook', 'desktop', msg).url.startsWith('https://outlook.live.com/mail/0/deeplink/compose?'))
})

test('Mail app is a plain mailto everywhere', () => {
  for (const os of ['ios', 'android', 'desktop']) assert.ok(sendPlan('default', os, msg).url.startsWith('mailto:'))
})

test('desktop opens one new tab and never navigates this page, even if the tab is blocked', () => {
  const opened = []
  globalThis.location = { href: 'http://localhost:8000/' }
  globalThis.window = { open: (url, target) => { opened.push([url, target]); return {} } }
  assert.equal(openMail('gmail', msg, 'desktop'), true)
  assert.equal(opened.length, 1)
  assert.equal(opened[0][1], '_blank')
  globalThis.window = { open: () => null }  // popup blocked
  assert.equal(openMail('outlook', msg, 'desktop'), false)
  assert.equal(location.href, 'http://localhost:8000/')
})
