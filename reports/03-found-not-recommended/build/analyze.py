#!/usr/bin/env python3
"""Auswertung fuer 'Found, not recommended' — alles aus dem eingefrorenen Snapshot in data/.
Ausgabe: data/results.json (einzige Quelle fuer Figuren + Text)."""
import json, math, datetime, collections, statistics as st
from pathlib import Path
R = Path(__file__).resolve().parent.parent
D = R/"data"
prim = json.load(open(D/"primary_rows.json"))
claude = json.load(open(D/"claude_rows.json"))
noweb = json.load(open(D/"noweb_rows.json"))
gaps = json.load(open(D/"data_gaps.json"))
T0 = datetime.date(2026,5,11)            # Domain-Start / T+0
CH = {"Direct":"direct","Research":"research","LongTail":"longtail",
      "Genre":"discovery","CompCluster":"discovery","GenreRecommend":"discovery"}
CLAUDE_TIERS = {"claude-haiku-4-5-20251001","claude-haiku-4-5","claude-sonnet-4-6","claude-sonnet-4.6 (web)",
                "claude-opus-4-8","claude-opus-4-7","claude-opus-4.7 (web)"}
def prov(llm):
    if llm=="openai_search": return "openai"
    if llm=="gemini": return "gemini"
    return None
# ---- Zeilen normalisieren: (date, provider, channel, score, status)
rows=[]
for r in prim:
    p=prov(r["llm"]); 
    if not p: continue
    rows.append((datetime.date.fromisoformat(r["d"]), p, CH[r["category"]], float(r["score"]), r["status"]))
for r in claude:
    if r["model"] not in CLAUDE_TIERS: continue
    if r["score"] is None: continue
    rows.append((datetime.date.fromisoformat(r["d"]), "claude", CH.get(r["category"],"discovery"), float(r["score"]), r["status"]))
def pct(sc,n): return None if not n else round(100*sc/(3*n),1)
def wilson(k,n,z=1.96):
    """Wilson-Intervall fuer Anteil; hier: Anteil 'positive Zitation' (score>0) als Binomial-Proxy"""
    if n==0: return (None,None)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (round(100*(c-h),1), round(100*(c+h),1))
# ---- Woche (ISO) x Kanal x Provider
wk=collections.defaultdict(lambda: {"sc":0.0,"n":0,"pos":0,"neg":0})
for d,p,ch,sc,stt in rows:
    k=(d.isocalendar()[1], ch, p); w=wk[k]; w["sc"]+=sc; w["n"]+=1; w["pos"]+= (sc>0); w["neg"]+= (sc<0)
weeks=sorted({k[0] for k in wk})
chans=["direct","longtail","discovery","research"]; provs=["openai","gemini","claude"]
weekly={}
for w in weeks:
    weekly[w]={}
    for ch in chans:
        e={}
        for p in provs:
            v=wk.get((w,ch,p))
            if v and v["n"]: e[p]={"pct":pct(v["sc"],v["n"]),"n":v["n"],"pos_share":round(100*v["pos"]/v["n"],1),"ci":wilson(v["pos"],v["n"]),"neg":v["neg"]}
        # Kanal gesamt = Mittel der Provider-Prozente (wie /api/latest), plus pooled
        ps=[e[p]["pct"] for p in e if e[p]["pct"] is not None]
        pooled_sc=sum(wk[(w,ch,p)]["sc"] for p in e); pooled_n=sum(wk[(w,ch,p)]["n"] for p in e)
        pooled_pos=sum(wk[(w,ch,p)]["pos"] for p in e)
        e["_mean"]= round(sum(ps)/len(ps),1) if ps else None
        e["_pooled"]= pct(pooled_sc,pooled_n); e["_n"]=pooled_n; e["_ci"]=wilson(pooled_pos,pooled_n)
        weekly[w][ch]=e
# ---- Tages-Reihe Kanal (pooled ueber Provider) fuer Kurven + Autokorrelation
day=collections.defaultdict(lambda: collections.defaultdict(lambda: {"sc":0.0,"n":0}))
for d,p,ch,sc,stt in rows: day[d][ch]["sc"]+=sc; day[d][ch]["n"]+=1
days=sorted(day)
daily={str(d):{ch:pct(day[d][ch]["sc"],day[d][ch]["n"]) for ch in chans} for d in days}
daily_n={str(d):{ch:day[d][ch]["n"] for ch in chans} for d in days}
def lag1(xs):
    xs=[x for x in xs if x is not None]
    if len(xs)<10: return None
    m=st.mean(xs); num=sum((xs[i]-m)*(xs[i+1]-m) for i in range(len(xs)-1)); den=sum((a-m)**2 for a in xs)
    return round(num/den,3) if den else None
since=datetime.date(2026,7,1)
ac={ch: lag1([daily[str(d)][ch] for d in days if d>=since]) for ch in chans}
# ---- Logistik-Fit Direct (pooled, taeglich) : y = L/(1+exp(-k(t-t0)))
import itertools
def fit_logistic(ts, ys):
    best=None
    for L in [x/2 for x in range(60,200)]:
        for k in [0.05,0.08,0.1,0.12,0.15,0.2,0.25,0.3,0.4]:
            for t0 in range(0,60):
                sse=sum((L/(1+math.exp(-k*(t-t0)))-y)**2 for t,y in zip(ts,ys))
                if best is None or sse<best[0]: best=(sse,L,k,t0)
    return best
ts=[(d-T0).days for d in days if daily[str(d)]["direct"] is not None]
ys=[daily[str(d)]["direct"] for d in days if daily[str(d)]["direct"] is not None]
sse,L,k,t0=fit_logistic(ts,ys)
ss_tot=sum((y-st.mean(ys))**2 for y in ys); r2=round(1-sse/ss_tot,3)
# ---- Discovery: Gesamtbilanz aller Blind-Antworten im Primaerkanal
disc=[(d,p,sc,stt) for d,p,ch,sc,stt in rows if ch=="discovery"]
disc_n=len(disc); disc_pos=sum(1 for x in disc if x[2]>0); disc_place=sum(1 for x in disc if x[3]=="genre_placement")
# ---- Provider-Disagreement: wöchentliche Spannweite der Direct-% ueber Provider
dis=[]
for w in weeks:
    e=weekly[w]["direct"]; ps=[e[p]["pct"] for p in provs if p in e and e[p]["pct"] is not None]
    if len(ps)>=2: dis.append({"week":w,"min":min(ps),"max":max(ps),"range":round(max(ps)-min(ps),1),"n_prov":len(ps)})
# ---- Provider-Mittelwert seit 01.07. je Kanal
since_rows=[x for x in rows if x[0]>=since]
pm={}
for p in provs:
    pm[p]={}
    for ch in chans:
        xs=[x for x in since_rows if x[1]==p and x[2]==ch]
        sc=sum(x[3] for x in xs); n=len(xs); pos=sum(1 for x in xs if x[3]>0); neg=sum(1 for x in xs if x[3]<0)
        pm[p][ch]={"pct":pct(sc,n),"n":n,"pos_share":round(100*pos/n,1) if n else None,"hallu_share":round(100*neg/n,1) if n else None,"ci":wilson(pos,n)}
# ---- Echo-Proof: No-Web-Modelle, Blind-Kategorien
blind=[r for r in noweb if r["category"] in ("Genre","CompCluster","GenreRecommend")]
echo={"n_blind_answers":len(blind),"n_models":len({r['llm'] for r in blind}),"models":sorted({r['llm'] for r in blind}),
      "marin_mentioned_unprompted":sum(int(r["marin_in_answer"]) for r in blind)}
# ---- Direct-Fragen No-Web: Anteil ehrliches Nichtwissen vs Halluzination (Kontrollkanal)
nw_direct=[r for r in noweb if r["category"]=="Direct"]
nwd={"n":len(nw_direct),"hallucinated":sum(1 for r in nw_direct if r["status"]=="hallucinated"),
     "not_found":sum(1 for r in nw_direct if str(r["status"]).startswith("not_found")),
     "echo_partial":sum(1 for r in nw_direct if r["status"] in ("partial_book","minimal_match","name_only_echo"))}
# ---- Phasen (Kanal-Mittel der Wochen)
def phase(ws,ch): 
    vals=[weekly[w][ch]["_pooled"] for w in ws if weekly[w][ch]["_pooled"] is not None]
    return round(st.mean(vals),1) if vals else None
phases={"KW20-22 (T+0..T+20)":[20,21,22],"KW23-26":[23,24,25,26],"KW27-30":[27,28,29,30],"KW31-33":[31,32,33]}
ph={name:{ch:phase(ws,ch) for ch in chans} for name,ws in phases.items()}
out={"meta":{"T0":str(T0),"first_day":str(days[0]),"last_day":str(days[-1]),"n_days":len(days),
             "n_primary_rows":len(prim),"n_claude_rows":sum(1 for r in claude if r['model'] in CLAUDE_TIERS),"n_rows_used":len(rows),
             "n_noweb_rows":len(noweb),"questions":16,"providers":provs},
     "weekly":weekly,"daily":daily,"daily_n":daily_n,"autocorr_lag1_since_0701":ac,
     "logistic_direct":{"L":L,"k":k,"t0_days":t0,"r2":r2,"n_points":len(ys),"inflection_date":str(T0+datetime.timedelta(days=t0))},
     "discovery_total":{"n":disc_n,"positive":disc_pos,"genre_placement":disc_place,"rate_pct":round(100*disc_pos/disc_n,2)},
     "provider_disagreement_direct":dis,"provider_means_since_0701":pm,"echo_proof":echo,"noweb_direct_control":nwd,
     "phases":ph,"data_gaps":gaps}
json.dump(out,open(D/"results.json","w"),ensure_ascii=False,indent=1)
print("results.json geschrieben")
print("Tage:",len(days),"| Zeilen genutzt:",len(rows))
print("Phasen (pooled %):"); [print("  ",k,v) for k,v in ph.items()]
print("Autokorr seit 01.07.:",ac)
print("Logistik Direct: L=%.1f k=%.2f t0=T+%d (=%s) R2=%.3f"%(L,k,t0,T0+datetime.timedelta(days=t0),r2))
print("Discovery gesamt:",out["discovery_total"])
print("Echo-Proof:",echo)
print("No-Web Direct Kontrolle:",nwd)
