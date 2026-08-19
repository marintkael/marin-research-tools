"""Marin-Report-Figstyle — Tufte x Encyclopédie x Swiss. Newsreader (Serif, Titel) + Helvetica Neue (Sans)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
F = Path(__file__).resolve().parent.parent/"figures"/"_fonts"
SERIF = fm.FontProperties(fname=str(F/"newsreader-latin.ttf"))
for p in ["/System/Library/Fonts/HelveticaNeue.ttc"]:
    try: fm.fontManager.addfont(p)
    except Exception: pass
WAX="#6E1010"; SAND="#c9a35e"; BLUE="#2b5d8a"; COOL="#4a6b85"; INK="#1c1c1c"; MUTE="#8a8a8a"; PAPER="#ffffff"; RULE="#d8d8d8"
CH_COLOR={"direct":WAX,"longtail":BLUE,"discovery":COOL,"research":SAND}
PROV_COLOR={"openai":WAX,"gemini":"#b0763a","claude":BLUE}
def base(w=10.5,h=6.2):
    plt.rcParams.update({"font.family":"Helvetica Neue","font.size":10.5,"axes.edgecolor":RULE,"axes.linewidth":0.6,
        "xtick.color":"#555","ytick.color":"#555","xtick.labelsize":9.5,"ytick.labelsize":9.5,"axes.labelcolor":"#444",
        "figure.facecolor":PAPER,"axes.facecolor":PAPER,"savefig.facecolor":PAPER,"axes.spines.top":False,"axes.spines.right":False})
    fig,ax=plt.subplots(figsize=(w,h),dpi=200); return fig,ax
def title(fig,ax,t,sub=None,x=0.06,y=0.965):
    fig.text(x,y,t,fontproperties=SERIF,fontsize=22,color=INK,ha="left",va="top")
    if sub: fig.text(x,y-0.085,sub,fontsize=10.5,color="#666",ha="left",va="top")
def footer(fig,t,x=0.06,y=0.025):
    fig.text(x,y,t,fontsize=8.3,color=MUTE,ha="left",va="bottom")
def save(fig,name,R):
    out=Path(R)/"figures"
    for ext in ("png","svg","pdf"): fig.savefig(out/f"{name}.{ext}",bbox_inches="tight",pad_inches=0.25)
    plt.close(fig); print("  fig:",name)
