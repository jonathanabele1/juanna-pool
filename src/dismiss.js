// One tap-to-dismiss popover at a time (the team stats card). The next tap anywhere closes it, and that tap
// doesn't also press whatever was under it (so dismissing over a team doesn't pick it).
let current = null

export function openOne(close) {
  closeOpen()
  current = close
  // after the event that opened it, so that event doesn't close it right away
  setTimeout(() => {
    if (current !== close) return
    document.addEventListener('pointerdown', onDown, true)
    document.addEventListener('keydown', onKey)
  })
}

export function closeOpen(only) {
  if (!current || (only && current !== only)) return
  const close = current
  current = null
  document.removeEventListener('pointerdown', onDown, true)
  document.removeEventListener('keydown', onKey)
  close()
}

function onDown() { closeOpen(); eatNextClick() }
function onKey(e) { if (e.key === 'Escape') closeOpen() }

function eatNextClick() {
  const eat = e => { e.stopPropagation(); e.preventDefault(); done() }
  const done = () => {
    document.removeEventListener('click', eat, true)
    document.removeEventListener('pointerdown', done, true)
  }
  document.addEventListener('click', eat, true)
  setTimeout(() => document.addEventListener('pointerdown', done, true))  // a scroll has no click: stop at the next tap
}
