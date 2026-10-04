import numpy as np, math
rng = np.random.default_rng(7)
G = 16
S = {
 "Flat (6-7 each)":        [7]*4+[6]*12,
 "Moderate ladder":        [12,11,10,9,8,8,7,6,6,5,4,4,3,3,2,2],
 "Your style (3x20)":      [20,20,20,6,5,4,4,3,3,3,2,2,2,2,2,2],
 "Max (20,20,20,9,9,2s)":  [20,20,20,9,9]+[2]*11,
 "Five DD (20,20,18,10,10)":[20,20,18,10,10]+[2]*11,
 "LOY week (50,20,4,2s)":  [50,20,4]+[2]*13,
}
for k,v in S.items():
    assert sum(v)==100 and len(v)==G and sum(x>=10 for x in v)!=4, k
print("## Analytic mean/sd at 50% per game")
for k,v in S.items():
    v=np.array(v); print(f"{k:28s} mean 50  sd {math.sqrt((v**2).sum()*.25):5.1f}  P(>=70)~", end="")
    # exact-ish via MC
    o=rng.random((200000,G))<.5; sc=o@v; print(f"{(sc>=70).mean():.3f}  P(>=80) {(sc>=80).mean():.3f}  P(<=30) {(sc<=30).mean():.3f}")

FIELD_STYLES=[S["Flat (6-7 each)"],S["Moderate ladder"],S["Your style (3x20)"],S["Max (20,20,20,9,9,2s)"]]
FIELD_MIX=[.25,.35,.25,.15]

def week(N, me_alloc, T, consensus=0.7, contrarian=False, my_edge=0.5, field_mix=FIELD_MIX):
    """Returns my score, and my prize share for T simulated weeks."""
    pop = rng.normal(size=(T,G))                       # how 'obvious' each game looks
    cov = rng.random((T,G)) < 0.5                       # consensus side covers?
    # field
    styles = rng.choice(len(FIELD_STYLES), size=(T,N), p=field_mix)
    A = np.array(FIELD_STYLES)[styles]                  # T,N,G sorted desc
    rank = np.argsort(-(pop[:,None,:]+rng.normal(size=(T,N,G))), axis=2)
    pts = np.zeros((T,N,G)); np.put_along_axis(pts, rank, A, axis=2)
    agree = rng.random((T,N,G)) < consensus
    hit = agree == cov[:,None,:]
    fscore = (pts*hit).sum(2); fwins = hit.sum(2)
    # me
    key = (-pop if contrarian else pop) + rng.normal(size=(T,G))
    r = np.argsort(-key, axis=1); mp = np.zeros((T,G)); np.put_along_axis(mp, r, np.array(me_alloc)[None,:].repeat(T,0), axis=1)
    if my_edge == 0.5:
        magree = rng.random((T,G)) < consensus
        mhit = magree == cov
    else:  # I independently cover with prob my_edge on my top-5 games, 0.5 elsewhere
        p = np.full((T,G), .5); top = r[:, :5]; np.put_along_axis(p, top, my_edge, axis=1)
        mhit = rng.random((T,G)) < p
    ms = (mp*mhit).sum(1); mw = mhit.sum(1)
    best = fscore.max(1)
    share = np.zeros(T)
    beat = ms > best; share[beat] = 1
    tie = ms == best
    for t in np.where(tie)[0]:
        tied = fwins[t][fscore[t]==best[t]]; bw = max(tied.max(), mw[t])
        if mw[t] == bw: share[t] = 1/(1+(tied==bw).sum())
    return ms, share

print("\n## Weekly prize: P(win the week) vs field, zero edge")
for N in (15,30,50):
    print(f"\nField of {N} others (fair share = {1/(N+1):.3f})")
    for k,v in S.items():
        ms,sh = week(N,v,20000)
        _,shc = week(N,v,20000,contrarian=True)
        print(f"  {k:28s} win-share {sh.mean():.3f} ({sh.mean()*(N+1):.2f}x fair)  contrarian-ranking {shc.mean():.3f}")

def season(N, me_alloc, T=4000, weeks=18, my_edge=0.5, loy=False):
    pay = np.array([21,17,14,11,9,7,6,5,4,3]+[0]*200)/100
    tot_me = np.zeros(T); tot_f = np.zeros((T,N)); wk_share = 0
    for w in range(weeks):
        alloc = S["LOY week (50,20,4,2s)"] if (loy and w==weeks-1) else me_alloc
        # reuse week() but also need field scores: rerun quick
        pop = rng.normal(size=(T,G)); cov = rng.random((T,G))<.5
        styles = rng.choice(len(FIELD_STYLES), size=(T,N), p=FIELD_MIX)
        A = np.array(FIELD_STYLES)[styles]
        rank = np.argsort(-(pop[:,None,:]+rng.normal(size=(T,N,G))),axis=2)
        pts=np.zeros((T,N,G)); np.put_along_axis(pts,rank,A,axis=2)
        hit=(rng.random((T,N,G))<.7)==cov[:,None,:]
        tot_f += (pts*hit).sum(2)
        r=np.argsort(-(pop+rng.normal(size=(T,G))),axis=1); mp=np.zeros((T,G)); np.put_along_axis(mp,r,np.array(alloc)[None,:].repeat(T,0),axis=1)
        if my_edge==.5: mh=(rng.random((T,G))<.7)==cov
        else:
            p=np.full((T,G),.5); np.put_along_axis(p,r[:,:5],my_edge,axis=1); mh=rng.random((T,G))<p
        tot_me += (mp*mh).sum(1)
    place = (tot_f > tot_me[:,None]).sum(1)          # 0 = first
    ties = (tot_f == tot_me[:,None]).sum(1)
    ev = np.array([pay[p:p+t+1].mean() for p,t in zip(place,ties)])
    return ev.mean(), (place==0).mean(), (place<10).mean(), tot_me.std()

print("\n## Season (18 wks) vs 30 others, year-end top-10 payout; field mix as above")
for edge in (.5,.53,.55):
    print(f"\nMy cover rate on my top-5 ranked games: {edge}")
    for k in ["Flat (6-7 each)","Moderate ladder","Your style (3x20)","Max (20,20,20,9,9,2s)"]:
        ev,p1,p10,sd = season(30,S[k],my_edge=edge)
        print(f"  {k:28s} E[share of pot] {ev*100:5.2f}%  P(1st) {p1:.3f}  P(top10) {p10:.3f}  season sd {sd:5.1f}")
