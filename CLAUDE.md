# Juanna Picks — project context

## What this app is (and isn't)
- The real league is the **Juanna Football Pool** at **juanna.net**. It runs on an old, manual system:
  every player **emails their picks** to the league each week, and the receiving address changes
  week to week (it goes to whichever person is in charge that week). Jonathan knows every week's address
  for the whole season in advance, so the app can store them ahead of time. The commissioners post the lines,
  standings and point distributions on juanna.net.
- **This app is not the league.** It's an unofficial helper on top of it, built by one player (Jonathan)
  for himself and a few friends in the league. Nothing here is official, and nothing here submits picks
  to the league by itself.
- Why it exists: making picks used to mean keeping juanna.net's lines, the points distribution and other
  pages open on several screens. This app puts it all in one view.

## How it grew
1. A single picks view: lines, confidence points and validation in one place.
2. **Email tab**: builds the picks email in the league's format so the player can copy it and paste it
   into their own email to that week's league address. The player still sends it themselves.
3. Hosted on Railway (instead of running locally) so friends in the league could use it too.
4. Social features: the League tab, seeing each other's picks, pool and public splits.
5. **Send picks** replaced the Email tab: one button on the week card opens the player's own Gmail, Outlook or
   mail app with the email to that week's league address already written. The player still sends it themselves.

## Implications for changes
- League rules live in `docs/` (from the commissioner's memo). The league decides the rules; this app only
  mirrors them. Don't invent rules, and flag any ambiguity (see `docs/open-questions.md`).
- The league counts a pick as on time by **when the player's own email was sent** (`docs/submission.md`), and
  a player proves a disputed pick by forwarding the original. So a submission needs to come from the
  player's own mailbox, and a copy needs to stay in their Sent folder.
- Users are a small group of friends, mostly on phones. See `docs/` for behavior, deploy and data model.
