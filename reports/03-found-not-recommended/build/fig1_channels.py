import json,math,datetime,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent)); import figstyle as S
import matplotlib.pyplot as plt, numpy as np
R=Path(__file__).resolve().parent.parent; res=json.load(open(R/"data/results.json"))
T0=datetime.date.fromisoformat(res["meta"]["T0"]); lg=res["logistic_direct"]
def series(ch):
    xs,ys,ns=[],[],[]
    for d,v in res["daily"].items():
        if v[ch] is None: continue
        xs.append((datetime.date.fromisoformat(d)-T0).days); ys.append(v[ch]); ns.append(res["daily_n"][d][ch])
    return np.array(xs),np.array(ys),np.array(ns)
def roll(xs,ys,w=7):
    out=[]
    for i in range(len(xs)):
        m=(xs>=xs[i]-w+1)&(xs<=xs[i]); out.append(ys[m].mean())
    return np.array(out)
for lang in ("de","en"):
    fig,ax=S.base(11,6.6)
    L={"de":dict(t="Drei Frage-Kanäle über 99 Tage",s="16 feste Fragen · OpenAI Search (Bing), Gemini (Google-Websuche), Claude (claude.ai-Websuche) · 7-Tage-Mittel, Punkte = Tageswerte",
                 direct='Direkt · „Wer ist Marin T. Kael?“',longtail='Saga-Wissen · „Welche Saga spielt in Varin?“',disc='Empfehlung · „Empfiehl mir Fantasy wie …“',
                 fit="Logistik-Fit  Decke %.0f %%  ·  Wendepunkt T+%d (%s)  ·  R² %.2f",hallu="Halluzinations-Episode nach Wikidata-Löschung (Score −3)",y="Zitationsrate (Score / Maximum)",x="Tage seit Domain-Start (T+0 = 11. Mai 2026)",
                 foot="Quelle: marin-research-pipeline, D1-Snapshot 2026-08-19 · %d Antworten · Fehlerzeilen ausgeschlossen · Kanal = Summe Score ÷ (3 × n) über alle drei Anbieter"),
       "en":dict(t="Three question channels across 99 days",s="16 fixed questions · OpenAI Search (Bing), Gemini (Google web search), Claude (claude.ai web search) · 7-day mean, dots = daily values",
                 direct="Direct · “Who is Marin T. Kael?”",longtail="Saga knowledge · “Which saga is set in Varin?”",disc="Recommendation · “Recommend fantasy like …”",
                 fit="Logistic fit  ceiling %.0f %%  ·  inflection T+%d (%s)  ·  R² %.2f",hallu="hallucination episode after Wikidata deletion (score −3)",y="Citation rate (score / maximum)",x="Days since domain launch (T+0 = 11 May 2026)",
                 foot="Source: marin-research-pipeline, D1 snapshot 2026-08-19 · %d answers · error rows excluded · channel = Σ score ÷ (3 × n) across all three providers")}[lang]
    for ch,col,lab in (("direct",S.WAX,L["direct"]),("longtail",S.BLUE,L["longtail"]),("discovery",S.COOL,L["disc"])):
        xs,ys,ns=series(ch)
        ax.scatter(xs,ys,s=np.clip(ns/2,4,26),color=col,alpha=0.22,linewidths=0)
        ax.plot(xs,roll(xs,ys),color=col,lw=2.2)
        ax.text(xs[-1]+1.5,roll(xs,ys)[-1],lab,color=col,fontsize=10,va="center",fontweight="bold")
    # Logistik
    xs,ys,ns=series("direct"); xx=np.linspace(0,xs.max(),300)
    ax.plot(xx,lg["L"]/(1+np.exp(-lg["k"]*(xx-lg["t0_days"]))),color=S.WAX,lw=1,ls=(0,(2,2)),alpha=0.8)
    ax.axhline(lg["L"],color=S.WAX,lw=0.5,ls=":",alpha=0.6)
    ax.text(1.5,lg["L"]+2.2,L["fit"]%(lg["L"],lg["t0_days"],lg["inflection_date"],lg["r2"]),fontsize=8.8,color=S.WAX,alpha=0.95,zorder=5)
    # Halluzinations-Episode (Wikidata-Loeschung 19.05., RfD) — negative Scores T+18..T+26
    ax.annotate(L["hallu"],xy=(22,-7),xytext=(33,-7.5),fontsize=8.2,color=S.WAX,va="center",arrowprops=dict(arrowstyle="-",color=S.WAX,lw=0.6))
    # Datenluecken schattieren
    for g in res["data_gaps"]:
        if g["channel"] not in ("openai_search","claude_web"): continue
        a=(datetime.date.fromisoformat(g["gap_start"])-T0).days; b=(datetime.date.fromisoformat(g["gap_end"])-T0).days
        ax.fill_betweenx([-14,86],a,b,color="#000",alpha=0.035,lw=0,zorder=0)   # nur Plotbereich, nicht in den Titel
        ax.text((a+b)/2,-12.2,("Lücke " if lang=="de" else "gap ")+g["channel"].split("_")[0],fontsize=7.5,color=S.MUTE,ha="center")
    ax.set_xlim(-2,xs.max()+3); ax.set_ylim(-15,92); ax.set_yticks([0,20,40,60,80]); ax.set_yticklabels([f"{v} %" for v in [0,20,40,60,80]])
    ax.set_xlabel(L["x"]); ax.set_ylabel(L["y"]); ax.grid(axis="y",color=S.RULE,lw=0.4)
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y",length=0)
    S.title(fig,ax,L["t"],L["s"]); S.footer(fig,L["foot"]%res["meta"]["n_rows_used"])
    fig.subplots_adjust(top=0.80,bottom=0.13,left=0.07,right=0.80)
    S.save(fig,f"fig1_channels_{lang}",R)
