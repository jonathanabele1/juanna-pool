# Open Questions / Assumptions

Items the memo leaves unclear. Defaults below are what I'd implement unless told otherwise.

1. **Are point values unique?** "Ranking from 20 to 2" suggests a ranking, but 16 unique values from 2–20
   can't sum to 100 with 16+ games (min sum 2+…+17 = 152). So values clearly repeat or aren't a strict
   permutation. *Assume: repeats allowed, each 2–20, sum = 100.*
2. **Does the LOY's 50 count toward the 100 total?** *Assume yes* (so other picks sum to 50).
3. **Does the LOY count as a double-digit pick?** *Assume yes.*
4. **Pushes**: confirmed: a push earns half the points and counts as neither win nor loss.
5. **Missing whole weekend**: "a 10 or the lowest weekly score" — meaning unclear. *Assume the
   participant gets the week's lowest score among all participants.* Needs commissioner clarification.
6. **Missing-game penalty vs. over-100 penalty interplay**: if a game is missing, is the target 80 and
   does a total over 80 get penalized as over 100? *Assume the −20 is applied per missing game and
   the cap stays 100 on submitted points.*
7. **Out-of-order picks** and "egregious" are subjective → manual adjustment entry.
8. **Tardy ladder**: 1st late = grace, 2nd = −10, 3rd = −20, 4th = −30 ("and so on"). *Assume +10 each.*
9. **Late (≥5 min) vs. grace**: does "<5 min late" count at all? *Assume under 5 min is on-time.*
10. **Entry fee remainder**: $95 − $45 − $45 = $5 unaccounted. Treated as admin.
11. **Number of weeks**: weekly pot math implies 18 weeks ($45 ÷ $2.50). Confirm.
12. **Weekly "lowest score"**: lowest score among all participants *that week* including penalties?
13. **Default pick penalty**: "different pick than the one on the list → −10" — per game or per week?
14. **Year-end tie handling** and whether last place is by total points among carp-eligible players only
    (memo implies only carp-eligible players can win the last-place prize).
15. **Who is the user in the site?** One commissioner view (data entry for everyone) vs. each member
    logging in. Not defined in the rules; *assume commissioner-run, locally.*
