import json,sys,datetime,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent)); import figstyle as S
import matplotlib.pyplot as plt, numpy as np
R=Path(__file__).resolve().parent.parent; res=json.load(open(R/"data/results.json"))
prim=json.load(open(R/"data/primary_rows.json")); cl=json.load(open(R/"data/claude_rows.json")); q=json.load(open(R/"data/questions.json"))
TIERS={"claude-haiku-4-5-20251001","claude-haiku-4-5","claude-sonnet-4-6","claude-sonnet-4.6 (web)","claude-opus-4-8","claude-opus-4-7","claude-opus-4.7 (web)"}
TX={"de":{},"en":{}}
# ---------------- FIG 2: Phasen x Kanal (Small Multiples) ----------------
for lang in ("de","en"):
    ph=res["phases"]; names=list(ph.keys())
    chans=[("direct","Direkt" if lang=="de" else "Direct",S.WAX),("longtail","Saga-Wissen" if lang=="de" else "Saga knowledge",S.BLUE),("discovery","Empfehlung" if lang=="de" else "Recommendation",S.COOL)]
    fig,axes=plt.subplots(1,3,figsize=(11,4.6),dpi=200,sharey=True)
    plt.rcParams.update({"font.family":"Helvetica Neue"})
    labels={"de":["T+0–20","T+21–48","T+49–76","T+77–99"],"en":["T+0–20","T+21–48","T+49–76","T+77–99"]}[lang]
    for ax,(ch,lab,col) in zip(axes,chans):
        vals=[ph[n][ch] for n in names]
        # Wilson-CI pooled aus weekly: Mittel der Wochen-CIs je Phase (konservativ: min/max)
        wk=res["weekly"]; phases_w={"KW20-22 (T+0..T+20)":[20,21,22],"KW23-26":[23,24,25,26],"KW27-30":[27,28,29,30],"KW31-33":[31,32,33]}
        lo,hi,ns=[],[],[]
        for n in names:
            cis=[wk[str(w)][ch]["_ci"] for w in phases_w[n] if str(w) in wk and wk[str(w)][ch]["_ci"][0] is not None]
            nn=sum(wk[str(w)][ch]["_n"] for w in phases_w[n] if str(w) in wk)
            lo.append(min(c[0] for c in cis) if cis else 0); hi.append(max(c[1] for c in cis) if cis else 0); ns.append(nn)
        x=np.arange(4)
        ax.bar(x,vals,color=col,width=0.62,alpha=0.92,zorder=3)
        for i,(v,n) in enumerate(zip(vals,ns)):
            ax.text(i,v+2.2,f"{abs(v):.0f} %",ha="center",fontsize=10.5,color=col,fontweight="bold")
            ax.text(i,-9,f"n={n}",ha="center",fontsize=7.8,color=S.MUTE)
        ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=8.8); ax.set_ylim(-12,88)
        for sp in ("top","right","left"): ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y",length=0); ax.grid(axis="y",color=S.RULE,lw=0.4,zorder=0)
        ax.set_title(lab,fontsize=11.5,color=col,loc="left",pad=8,fontweight="bold")
        ax.axhline(0,color="#999",lw=0.6)
    axes[0].set_yticks([0,20,40,60,80]); axes[0].set_yticklabels([f"{v} %" for v in [0,20,40,60,80]],fontsize=9)
    t={"de":("Vier Phasen, drei Geschwindigkeiten","Zitationsrate je Kanal und Phase, gepoolt über OpenAI · Gemini · Claude · Konfidenzbänder in Tabelle 1"),
       "en":("Four phases, three speeds","Citation rate per channel and phase, pooled across OpenAI · Gemini · Claude · confidence bands in Table 1")}[lang]
    S.title(fig,axes[0],t[0],t[1]); S.footer(fig,{"de":"Quelle: D1-Snapshot 2026-08-19 · Phasen nach Kalenderwochen 20–22 · 23–26 · 27–30 · 31–33 · n = Antworten je Phase und Kanal","en":"Source: D1 snapshot 2026-08-19 · phases by ISO weeks 20–22 · 23–26 · 27–30 · 31–33 · n = answers per phase and channel"}[lang])
    fig.subplots_adjust(top=0.72,bottom=0.16,left=0.07,right=0.98,wspace=0.18); S.save(fig,f"fig2_phases_{lang}",R)
# ---------------- FIG 3: Provider-Disagreement (Direct, Woche) ----------------
for lang in ("de","en"):
    fig,ax=S.base(11,5.6); wk=res["weekly"]; weeks=sorted(int(w) for w in wk)
    for p,col,lab in (("openai",S.WAX,"OpenAI Search"),("gemini","#b0763a","Gemini (Google-Websuche)" if lang=="de" else "Gemini (Google web grounding)"),("claude",S.BLUE,"Claude (Websuche)" if lang=="de" else "Claude (web search)")):
        xs=[w for w in weeks if p in wk[str(w)]["direct"] and wk[str(w)]["direct"][p]["pct"] is not None]
        ys=[wk[str(w)]["direct"][p]["pct"] for w in xs]
        ax.plot(xs,ys,color=col,lw=2,marker="o",ms=4.5,mfc="white",mew=1.6)
        ax.text(xs[-1]+0.25,ys[-1],lab,color=col,fontsize=10,va="center",fontweight="bold")
    # Spannweite schattieren
    dis={d["week"]:d for d in res["provider_disagreement_direct"]}
    ax.fill_between([w for w in weeks if w in dis],[dis[w]["min"] for w in weeks if w in dis],[dis[w]["max"] for w in weeks if w in dis],color="#000",alpha=0.04,lw=0)
    mx=max(dis.values(),key=lambda d:d["range"])
    ax.annotate(({"de":"Spannweite KW%d: %.0f Punkte","en":"spread wk %d: %.0f points"}[lang])%(mx["week"],mx["range"]),xy=(mx["week"],(mx["min"]+mx["max"])/2),xytext=(mx["week"]-3.2,mx["max"]+9),fontsize=8.8,color="#555",arrowprops=dict(arrowstyle="-",color="#999",lw=0.6))
    ax.set_xlim(weeks[0]-0.5,weeks[-1]+4.2); ax.set_ylim(-15,105); ax.set_yticks([0,25,50,75,100]); ax.set_yticklabels([f"{v} %" for v in [0,25,50,75,100]])
    ax.set_xticks(weeks); ax.set_xticklabels([f"KW{w}" if lang=="de" else f"wk{w}" for w in weeks],fontsize=8.5)
    ax.grid(axis="y",color=S.RULE,lw=0.4); ax.spines["left"].set_visible(False); ax.tick_params(axis="y",length=0)
    ax.set_ylabel({"de":"Direkt-Kanal · Zitationsrate","en":"Direct channel · citation rate"}[lang])
    t={"de":("Direkt-Kanal je Anbieter","Wochenmittel · OpenAI Search (Bing), Gemini (Google-Websuche), Claude (claude.ai-Websuche) · graues Band = Spannweite zwischen den Anbietern in derselben Woche"),
       "en":("Direct channel by provider","Weekly mean · OpenAI Search (Bing), Gemini (Google web search), Claude (claude.ai web search) · grey band = spread between providers in the same week")}[lang]
    S.title(fig,ax,t[0],t[1]); S.footer(fig,{"de":"Quelle: D1-Snapshot 2026-08-19 · Claude ab KW21 (claude.ai-Websuche, drei Stufen gemittelt) · Gemini mit Google-Grounding ab 20.05.","en":"Source: D1 snapshot 2026-08-19 · Claude from wk 21 (claude.ai web search, three tiers averaged) · Gemini with Google grounding from 20 May"}[lang])
    fig.subplots_adjust(top=0.79,bottom=0.12,left=0.07,right=0.84); S.save(fig,f"fig3_providers_{lang}",R)
# ---------------- FIG 4: Discovery-Anatomie ----------------
hits=[(r["d"],"openai" if "openai" in r["llm"] else "gemini",r["question_id"]) for r in prim if r["category"] in ("Genre","CompCluster","GenreRecommend") and float(r["score"])>0]
hits+=[(r["d"],"claude",r["question_id"]) for r in cl if r["model"] in TIERS and r["category"] in ("Genre","CompCluster","GenreRecommend") and r["score"] and float(r["score"])>0]
tot=collections.Counter(); 
for r in prim:
    if r["category"] in ("Genre","CompCluster","GenreRecommend"): tot[r["question_id"]]+=1
for r in cl:
    if r["model"] in TIERS and r["category"] in ("Genre","CompCluster","GenreRecommend"): tot[r["question_id"]]+=1
byq=collections.Counter(h[2] for h in hits); byqp=collections.defaultdict(collections.Counter)
for h in hits: byqp[h[2]][h[1]]+=1
qtext={x["question_id"]:x["q"] for x in q}
order=[qid for qid,_ in sorted(tot.items(),key=lambda kv:-byq.get(kv[0],0))]
for lang in ("de","en"):
    fig,ax=S.base(11,6.2)
    y=np.arange(len(order))[::-1]
    for yi,qid in zip(y,order):
        n=tot[qid]; k=byq.get(qid,0); left=0
        ax.barh(yi,n,color="#eeeeee",height=0.62,zorder=2)
        for p,col in (("openai",S.WAX),("gemini","#b0763a"),("claude",S.BLUE)):
            c=byqp[qid].get(p,0)
            if c: ax.barh(yi,c,left=left,color=col,height=0.62,zorder=3); left+=c
        txt=qtext.get(qid,qid); txt=(txt[:74]+"…") if len(txt)>76 else txt
        ax.text(-8,yi,f"{qid}  {txt}",ha="right",va="center",fontsize=8.8,color=S.INK)
        ax.text(n+6,yi,f"{k} / {n}"+("" if k==0 else f"  ({100*k/n:.1f} %)"),va="center",fontsize=8.8,color=S.INK if k else S.MUTE)
    ax.set_yticks([]); ax.set_xlim(0,max(tot.values())*1.25); ax.set_ylim(-0.7,len(order)+0.4); ax.spines["left"].set_visible(False)
    ax.set_xlabel({"de":"Blind-Antworten je Frage","en":"Blind answers per question"}[lang])
    for i,(p,col,lab) in enumerate((("openai",S.WAX,"OpenAI"),("gemini","#b0763a","Gemini"),("claude",S.BLUE,"Claude"))):
        ax.text(max(tot.values())*0.72+i*110,len(order)-0.2,"● "+lab,color=col,fontsize=9,va="center",fontweight="bold")
    ax.text(max(tot.values())*0.72-120,len(order)-0.2,{"de":"Nennungen:","en":"mentions:"}[lang],color=S.MUTE,fontsize=9,va="center")
    d=res["discovery_total"]
    t={"de":("Empfehlungen nach Frage",f"{d['positive']} Nennungen in {d['n']:,} Blind-Antworten ({d['rate_pct']} %) · {byq.get('GR6',0)} davon auf eine einzige Frage: das selbst geprägte Sub-Genre „Edikt-Fantasy“".replace(",",".")),
       "en":("Recommendations by question",f"{d['positive']} mentions in {d['n']:,} blind answers ({d['rate_pct']} %) · {byq.get('GR6',0)} of them on a single question: the self-coined sub-genre “edict fantasy”")}[lang]
    S.title(fig,ax,t[0],t[1]); S.footer(fig,{"de":"Quelle: D1-Snapshot 2026-08-19 · Blind = Frage enthält weder Autor noch Titel · Nennung = Score > 0 (genre_placement / minimal_match) · Anbieter-Farben wie Abb. 3","en":"Source: D1 snapshot 2026-08-19 · blind = question names neither author nor title · mention = score > 0 (genre_placement / minimal_match) · provider colours as Fig. 3"}[lang])
    fig.subplots_adjust(top=0.78,bottom=0.16,left=0.47,right=0.975); S.save(fig,f"fig4_discovery_{lang}",R)
# ---------------- FIG 5: Echo-Proof ----------------
nw=json.load(open(R/"data/noweb_rows.json"))
blind=[r for r in nw if r["category"] in ("Genre","CompCluster","GenreRecommend")]
bym=collections.Counter(r["llm"] for r in blind); men=collections.Counter(r["llm"] for r in blind if int(r["marin_in_answer"]))
direct=[r for r in nw if r["category"]=="Direct"]; dst=collections.defaultdict(collections.Counter)
for r in direct: dst[r["llm"]][("hallu" if r["status"]=="hallucinated" else "echo" if r["status"] in ("partial_book","minimal_match","name_only_echo") else "nf")]+=1
LAB={"claude":"Claude (ohne Web)","claude_sonnet":"Claude Sonnet (ohne Web)","claude_opus":"Claude Opus (ohne Web)","llama3":"Llama 3","llama31":"Llama 3.1","llama32":"Llama 3.2","mistral":"Mistral","phi2":"Phi-2","openai":"GPT-4o-mini (ohne Suche)","openai_gpt4o":"GPT-4o (ohne Suche)"}
LABE={k:v.replace("ohne Web","no web").replace("ohne Suche","no search") for k,v in LAB.items()}
for lang in ("de","en"):
    fig,ax=S.base(11,5.8); models=[m for m,n in bym.most_common() if n>=50]; y=np.arange(len(models))[::-1]   # n<50 (GPT-4o ohne Suche, 8 Antworten) raus
    for yi,m in zip(y,models):
        n=bym[m]; ax.barh(yi,n,color="#e9e9e9",height=0.6,zorder=2)
        ax.text(n+40,yi,f"{men.get(m,0)} / {n}",va="center",fontsize=9.2,color=S.INK,fontweight="bold")
        ax.text(-40,yi,(LAB if lang=="de" else LABE).get(m,m),ha="right",va="center",fontsize=9.2,color=S.INK)
        # Direct-Kontrolle rechts als Mini-Legende
        dd=dst.get(m,{}); tot_d=sum(dd.values())
        if tot_d: ax.text(max(bym.values())*1.18,yi,({"de":"Direkt: %d %% Nichtwissen · %d %% Echo · %d %% Halluzination","en":"direct: %d %% unknown · %d %% echo · %d %% hallucination"}[lang])%(100*dd.get("nf",0)/tot_d,100*dd.get("echo",0)/tot_d,100*dd.get("hallu",0)/tot_d),va="center",fontsize=7.6,color=S.MUTE)
    ax.set_yticks([]); ax.set_xlim(0,max(bym.values())*1.95); ax.spines["left"].set_visible(False)
    ax.set_xlabel({"de":"Blind-Antworten je Modell (grau) · Zahl = ungefragte Nennungen von Marin T. Kael / Antworten","en":"Blind answers per model (grey) · number = unprompted mentions of Marin T. Kael / answers"}[lang])
    e=res["echo_proof"]
    t={"de":("Kontrollkanal: Modelle ohne Web-Zugriff",f"{e['n_blind_answers']:,} Blind-Antworten von {e['n_models']} Modellen ohne Web-Zugriff · ungefragte Nennungen: {e['marin_mentioned_unprompted']} · Gemini fehlt hier, weil es nur mit Google-Websuche gemessen wurde".replace(",",".")),
       "en":("Control channel: models without web access",f"{e['n_blind_answers']:,} blind answers from {e['n_models']} models without web access · unprompted mentions: {e['marin_mentioned_unprompted']} · Gemini is absent here because it was only ever measured with Google web grounding")}[lang]
    S.title(fig,ax,t[0],t[1]); S.footer(fig,{"de":"Quelle: D1-Snapshot 2026-08-19 · Kontrollkanal (Cutoff-Modelle, kein Web) · rechts: Verhalten bei Direkt-Fragen mit Autor/Titel im Prompt · Echo = Titel/Name zurückgespiegelt ohne Wissen","en":"Source: D1 snapshot 2026-08-19 · control channel (cutoff models, no web) · right: behaviour on direct questions with author/title in the prompt · echo = title/name mirrored back without knowledge"}[lang])
    fig.subplots_adjust(top=0.79,bottom=0.15,left=0.22,right=0.98); S.save(fig,f"fig5_echo_{lang}",R)
