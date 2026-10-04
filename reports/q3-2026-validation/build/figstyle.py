"""Marin-Report-Figstyle (übernommen aus Bericht 03): Newsreader (Serif, Titel) + Helvetica Neue (Sans).
Änderung gegenüber Bericht 03: nur PNG + SVG, Metadaten ohne Werkzeug-Spuren, Autor = Marin T. Kael."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
F = Path(__file__).resolve().parent.parent/"figures"/"_fonts"
SERIF = (fm.FontProperties(fname=str(F/"newsreader-latin.ttf")) if (F/"newsreader-latin.ttf").exists()
         else fm.FontProperties(family="serif"))   # Newsreader optional; falls back to a serif
for p in ["/System/Library/Fonts/HelveticaNeue.ttc"]:
    try: fm.fontManager.addfont(p)
    except Exception: pass
WAX="#6E1010"; SAND="#c9a35e"; BLUE="#2b5d8a"; COOL="#4a6b85"; INK="#1c1c1c"; MUTE="#8a8a8a"; PAPER="#ffffff"; RULE="#d8d8d8"
PROV_COLOR={"OpenAI":WAX,"Gemini":"#b0763a","Claude-Web":BLUE}
plt.rcParams["svg.hashsalt"] = "marin-q3-2026"
def base(w=10.5,h=6.2,rows=1,cols=1,**kw):
    plt.rcParams.update({"font.family":"Helvetica Neue","font.size":10.5,"axes.edgecolor":RULE,"axes.linewidth":0.6,
        "xtick.color":"#555","ytick.color":"#555","xtick.labelsize":9.5,"ytick.labelsize":9.5,"axes.labelcolor":"#444",
        "figure.facecolor":PAPER,"axes.facecolor":PAPER,"savefig.facecolor":PAPER,"axes.spines.top":False,"axes.spines.right":False})
    return plt.subplots(rows,cols,figsize=(w,h),dpi=200,**kw)
def title(fig,t,sub=None,x=0.06,y=0.965):
    fig.text(x,y,t,fontproperties=SERIF,fontsize=22,color=INK,ha="left",va="top")
    if sub: fig.text(x,y-0.075,sub,fontsize=10.5,color="#666",ha="left",va="top")
def footer(fig,t,x=0.06,y=0.02):
    fig.text(x,y,t,fontsize=8.3,color=MUTE,ha="left",va="bottom")
def save(fig,name,R):
    out=Path(R)/"figures"
    fig.savefig(out/f"{name}.png",bbox_inches="tight",pad_inches=0.25,metadata={"Software":None,"Author":"Marin T. Kael"})
    fig.savefig(out/f"{name}.svg",bbox_inches="tight",pad_inches=0.25,metadata={"Creator":"Marin T. Kael","Date":None,"Format":None,"Type":None})
    sv=out/f"{name}.svg"; sv.write_text(sv.read_text(encoding="utf-8").replace('id="matplotlib.','id="'),encoding="utf-8")   # keine Werkzeug-Spuren
    plt.close(fig); print("  fig:",name)
