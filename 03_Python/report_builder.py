# -*- coding: utf-8 -*-
"""
report_builder.py — LE METTEUR EN PAGE (ne calcule rien)
========================================================
Entrees : 01_Data/Output/ai_report.md   (texte ecrit par l'IA)
          01_Data/Output/_charts/*.png   (graphiques produits par generate_ai_context.py)
Sortie  : 01_Data/Output/<CLIENT>_Executive_Report.pdf
"""
import os, re, glob
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
                                PageBreak, Frame, PageTemplate, NextPageTemplate, KeepTogether)
from PIL import Image as PILImage

# ============================ REGLAGES (branding) ============================
CLIENT  = "AdventureWorks"
AUTHOR  = "Rudy Mevizou"
SUBTITLE= "Sales Performance & Profitability"
PALETTE = {"gold":"#C9B46A","char":"#262626","cream":"#F3F0E7","ink":"#3A3A36"}
# ===========================================================================

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD=os.path.join(BASE,"01_Data","Output"); CH=os.path.join(OUTD,"_charts")
MDp=os.path.join(OUTD,"ai_report.md"); OUT=os.path.join(OUTD,f"{CLIENT}_Executive_Report.pdf")
os.makedirs(OUTD,exist_ok=True)
if not os.path.exists(MDp):  # demo: fallback sur la narration livree dans 04_Report
    _FB=os.path.join(BASE,"04_Report","ai_report.md")
    if os.path.exists(_FB): MDp=_FB; print("[demo] narration LLM absente -> 04_Report/ai_report.md")
gold=colors.HexColor(PALETTE["gold"]); char=colors.HexColor(PALETTE["char"]); cream=colors.HexColor(PALETTE["cream"]); ink=colors.HexColor(PALETTE["ink"])

styles=getSampleStyleSheet()
def mk(n,**k):
    k.setdefault("fontName","Helvetica");k.setdefault("textColor",ink);k.setdefault("fontSize",10.5);k.setdefault("leading",15);k.setdefault("spaceAfter",6)
    return ParagraphStyle(n,parent=styles["Normal"],**k)
body=mk("body");cell=mk("cell",fontSize=9,leading=12,spaceAfter=0);cellh=mk("cellh",fontSize=9,leading=12,spaceAfter=0,fontName="Helvetica-Bold",textColor=colors.white)
h1=mk("h1",fontName="Helvetica-Bold",fontSize=16,textColor=char,spaceBefore=4,spaceAfter=9,leading=19)
h2=mk("h2",fontName="Helvetica-Bold",fontSize=12.5,textColor=colors.HexColor("#7a6a2f"),spaceBefore=9,spaceAfter=4,leading=16)
h3=mk("h3",fontName="Helvetica-Bold",fontSize=11,textColor=char,spaceBefore=6,spaceAfter=3,leading=14)
bullet=mk("bullet",leftIndent=12,spaceAfter=3);small=mk("small",fontSize=8.5,textColor=colors.HexColor("#7a756c"),leading=12)
note=mk("note",fontName="Helvetica-Oblique",fontSize=10,leading=14,textColor=colors.HexColor("#6b6b63"),leftIndent=10,spaceBefore=2,spaceAfter=8)
capst=mk("capst",fontSize=8.5,textColor=colors.HexColor("#7a756c"),alignment=TA_CENTER,spaceAfter=10)
def cap(t): return Paragraph(t,capst)
def inline(t):
    t=t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    t=re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",t)
    t=re.sub(r"\*(.+?)\*",r"<i>\1</i>",t)
    return t
def render_md(text):
    fl=[];L=text.split("\n");i=0;pages=0
    while i<len(L):
        ln=L[i].rstrip()
        if ln.strip().startswith("|"):
            blk=[]
            while i<len(L) and L[i].strip().startswith("|"): blk.append(L[i].strip());i+=1
            rows=[]
            for r in blk:
                cs=[c.strip() for c in r.strip("|").split("|")]
                if all(set(c)<=set("-: ") for c in cs): continue
                rows.append(cs)
            if rows:
                nc=max(len(r) for r in rows); w=(170*mm)/nc
                data=[[Paragraph(inline(c),cellh if ri==0 else cell) for c in (r+[""]*(nc-len(r)))] for ri,r in enumerate(rows)]
                t=Table(data,colWidths=[w]*nc,repeatRows=1)
                t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),char),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F2EA")]),
                    ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D6D2C8")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
                fl+=[t,Spacer(1,8)]
            continue
        if ln.strip() in ("---","***","___"): fl.append(Spacer(1,6)); i+=1; continue
        if ln.strip().startswith(">"): fl.append(Paragraph(inline(ln.strip().lstrip(">").strip()),note)); i+=1; continue
        mp=re.match(r"#\s+PAGE\s+\d+\s*[-\u2014:]\s*(.+)$", ln.strip(), re.I)
        if mp:
            if pages>0: fl.append(PageBreak())
            pages+=1
            fl.append(Paragraph(inline(mp.group(1).strip()),h1)); i+=1; continue
        if ln.startswith("# "): fl.append(Paragraph(inline(ln[2:]),h1))
        elif ln.startswith("### "): fl.append(Paragraph(inline(ln[4:]),h3))
        elif ln.startswith("## "): fl.append(Paragraph(inline(ln[3:]),h2))
        elif ln.strip().startswith(("- ","* ")): fl.append(Paragraph(inline(ln.strip()[2:]),bullet,bulletText="•"))
        elif ln.strip()=="": fl.append(Spacer(1,4))
        else: fl.append(Paragraph(inline(ln),body))
        i+=1
    return fl

PW,PH=A4
def cover(c,d):
    c.saveState();c.setFillColor(cream);c.rect(0,0,PW,PH,fill=1,stroke=0);c.setFillColor(gold);c.rect(0,PH-58*mm,PW,58*mm,fill=1,stroke=0)
    c.setFillColor(char);c.rect(0,PH-60*mm,PW,2*mm,fill=1,stroke=0);c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold",26);c.drawString(22*mm,PH-32*mm,CLIENT);c.setFont("Helvetica",15);c.drawString(22*mm,PH-42*mm,SUBTITLE)
    c.setFillColor(char);c.setFont("Helvetica-Bold",13);c.drawString(22*mm,PH-80*mm,"Executive Report")
    c.setFillColor(ink);c.setFont("Helvetica",10);c.drawString(22*mm,PH-92*mm,"Scope: full historical period - year-over-year on the latest comparable years")
    c.setFillColor(char);c.rect(0,18*mm,PW,0.4*mm,fill=1,stroke=0);c.setFont("Helvetica-Bold",10);c.drawString(22*mm,11*mm,AUTHOR.upper())
    c.setFont("Helvetica",9);c.setFillColor(colors.HexColor("#7a756c"));c.drawString(22*mm,7*mm,"Data Analyst - Power BI - SQL - Python");c.restoreState()
def page(c,d):
    c.saveState();c.setFillColor(colors.HexColor("#FBFAF6"));c.rect(0,0,PW,PH,fill=1,stroke=0);c.setFillColor(gold);c.rect(20*mm,PH-18*mm,PW-40*mm,1.2*mm,fill=1,stroke=0)
    c.setFont("Helvetica",8);c.setFillColor(colors.HexColor("#9a958c"));c.drawString(20*mm,PH-15*mm,f"{CLIENT} - Executive Report");c.drawRightString(PW-20*mm,PH-15*mm,f"{AUTHOR} - Data Analyst")
    c.drawRightString(PW-20*mm,12*mm,f"Page {d.page-1}");c.drawString(20*mm,12*mm,"Confidential - for decision-making purposes");c.restoreState()
doc=SimpleDocTemplate(OUT,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=22*mm,bottomMargin=18*mm,title=f"{CLIENT} Executive Report",author=AUTHOR)
doc.addPageTemplates([PageTemplate(id="Cover",frames=[Frame(0,0,PW,PH,id="c")],onPage=cover),
                      PageTemplate(id="Body",frames=[Frame(20*mm,18*mm,PW-40*mm,PH-38*mm,id="b")],onPage=page)])
def figimg(p,w=160*mm):
    iw,ih=PILImage.open(p).size; return Image(p,width=w,height=w*ih/iw)

story=[NextPageTemplate("Body"),PageBreak()]
if os.path.exists(MDp): story+=render_md(open(MDp,encoding="utf-8").read())
else: story+=[Paragraph("Executive narrative manquante",h1),Paragraph(f"Place le rapport de l'IA dans : {MDp}",body)]
charts=sorted(glob.glob(os.path.join(CH,"*.png")))
if charts:
    story+=[PageBreak(),Paragraph("Appendix - Charts",h1)]
    for i,p in enumerate(charts):
        name=re.sub(r"^\d+_","",os.path.basename(p)).replace(".png","")
        w=110*mm if "vs" in name else 160*mm
        story.append(KeepTogether([figimg(p,w),cap(f"Figure {i+1} - {name}"),Spacer(1,6)]))
    story+=[Spacer(1,6),Paragraph("Charts generated automatically from the source data. Orders/Customers are distinct counts (nunique).",small)]
doc.build(story); print("PDF OK:", OUT)
