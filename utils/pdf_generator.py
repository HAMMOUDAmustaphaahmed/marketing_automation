from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import json
from datetime import datetime

C_NAVY=colors.HexColor('#0f172a'); C_BLUE=colors.HexColor('#1a56db')
C_BLUE2=colors.HexColor('#1e40af'); C_BLUE_LT=colors.HexColor('#dbeafe')
C_BLUE_XL=colors.HexColor('#eff6ff'); C_TEAL=colors.HexColor('#0891b2')
C_TEAL_LT=colors.HexColor('#e0f7fa'); C_GREEN=colors.HexColor('#059669')
C_RED=colors.HexColor('#dc2626'); C_ORANGE=colors.HexColor('#d97706')
C_GRAY=colors.HexColor('#6b7280'); C_GRAY_LT=colors.HexColor('#f1f5f9')
C_GRAY_XL=colors.HexColor('#f8fafc'); C_WHITE=colors.white
W=A4[0]-3*cm

def _s():
    b=getSampleStyleSheet()
    return {
        'DocTitle':ParagraphStyle('DocTitle',parent=b['Normal'],fontSize=19,textColor=C_WHITE,fontName='Helvetica-Bold',alignment=TA_LEFT,spaceAfter=2),
        'DocSub':ParagraphStyle('DocSub',parent=b['Normal'],fontSize=10,textColor=colors.HexColor('#bfdbfe'),fontName='Helvetica'),
        'DocRef':ParagraphStyle('DocRef',parent=b['Normal'],fontSize=11,textColor=C_WHITE,fontName='Helvetica-Bold',alignment=TA_RIGHT),
        'H1':ParagraphStyle('H1',parent=b['Normal'],fontSize=11,textColor=C_BLUE2,fontName='Helvetica-Bold',spaceBefore=8,spaceAfter=4),
        'Body':ParagraphStyle('Body',parent=b['Normal'],fontSize=9,textColor=C_NAVY,fontName='Helvetica',leading=13,spaceAfter=3),
        'BodyG':ParagraphStyle('BodyG',parent=b['Normal'],fontSize=8.5,textColor=C_GRAY,fontName='Helvetica',leading=12),
        'Lbl':ParagraphStyle('Lbl',parent=b['Normal'],fontSize=7.5,textColor=C_GRAY,fontName='Helvetica-Bold'),
        'Val':ParagraphStyle('Val',parent=b['Normal'],fontSize=9,textColor=C_NAVY,fontName='Helvetica'),
        'Badge':ParagraphStyle('Badge',parent=b['Normal'],fontSize=9,textColor=C_WHITE,fontName='Helvetica-Bold',alignment=TA_CENTER),
        'TH':ParagraphStyle('TH',parent=b['Normal'],fontSize=9,textColor=C_WHITE,fontName='Helvetica-Bold',alignment=TA_CENTER),
        'TD':ParagraphStyle('TD',parent=b['Normal'],fontSize=8.5,textColor=C_NAVY,fontName='Helvetica',leading=12),
        'TDR':ParagraphStyle('TDR',parent=b['Normal'],fontSize=8.5,textColor=C_NAVY,fontName='Helvetica',alignment=TA_RIGHT),
        'TDC':ParagraphStyle('TDC',parent=b['Normal'],fontSize=8.5,textColor=C_NAVY,fontName='Helvetica',alignment=TA_CENTER),
        'TDTot':ParagraphStyle('TDTot',parent=b['Normal'],fontSize=10,textColor=C_WHITE,fontName='Helvetica-Bold',alignment=TA_RIGHT),
        'Footer':ParagraphStyle('Footer',parent=b['Normal'],fontSize=7.5,textColor=C_GRAY,alignment=TA_CENTER),
    }

def _banner(title,sub,ref='',color=None):
    if color is None: color=C_BLUE
    s=_s()
    t=Table([[Paragraph(title,s['DocTitle']),Paragraph(sub,s['DocSub']),Paragraph(ref,s['DocRef'])]],colWidths=[W*.44,W*.36,W*.2])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),color),('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),('TOPPADDING',(0,0),(-1,-1),18),('BOTTOMPADDING',(0,0),(-1,-1),18),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return t

def _pill(label,score,el):
    s=_s(); c=C_GREEN if score>=70 else C_BLUE if score>=40 else C_GRAY
    t=Table([[Paragraph(f'<b>{label} : {score}%</b>',s['Badge'])]],colWidths=[5*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),c),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),10)]))
    el.append(t); el.append(Spacer(1,4*mm))

def _sec(title,el):
    s=_s(); t=Table([[Paragraph(title,s['H1'])]],colWidths=[W])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_BLUE_XL),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBEFORE',(0,0),(0,-1),3,C_BLUE)]))
    el.append(Spacer(1,3*mm)); el.append(t); el.append(Spacer(1,2*mm))

def _kv(lbl,val,el,w1=4.5*cm):
    s=_s(); t=Table([[Paragraph(lbl.upper(),s['Lbl']),Paragraph(str(val or '—'),s['Val'])]],colWidths=[w1,W-w1])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),C_GRAY_XL),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#e2e8f0'))]))
    el.append(t)

def _foot(el,co=''):
    el.append(Spacer(1,6*mm)); el.append(HRFlowable(width=W,thickness=.5,color=C_BLUE_LT))
    el.append(Spacer(1,2*mm)); el.append(Paragraph(f'{co} · Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} · SMarketing Platform',_s()['Footer']))

def _doc(buf):
    return SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.5*cm,rightMargin=1.5*cm,topMargin=1.2*cm,bottomMargin=1.5*cm)


def generate_competitor_pdf(competitor):
    buf=BytesIO(); doc=_doc(buf); s=_s(); el=[]
    el.append(_banner('Fiche Concurrentielle',competitor.name,f'Score: {competitor.similarity_score or 0}%'))
    el.append(Spacer(1,4*mm)); _pill('Similarité',competitor.similarity_score or 0,el)
    _sec('📋 Informations Générales',el)
    _kv('Site Web',competitor.website,el); _kv('Pays/Ville',f"{competitor.country or ''} · {competitor.city or ''}",el)
    _kv('Secteur',competitor.sector,el); _kv('Fondé en',competitor.founded_year,el)
    _kv('Effectif',competitor.employees_count,el); _kv('CA estimé',competitor.revenue_estimate,el)
    _sec('🏭 Activités & Offre',el)
    _kv('Activités',competitor.activities,el); _kv('Produits',competitor.products,el); _kv('Services',competitor.services,el)
    _sec('🌐 Présence Digitale',el)
    _kv('LinkedIn',competitor.linkedin_url,el); _kv('Note Google',f"{competitor.google_rating}/5" if competitor.google_rating else '—',el); _kv('Technologies',competitor.technologies,el)
    if competitor.swot_analysis:
        _sec('🎯 Analyse SWOT (IA)',el)
        try:
            raw=competitor.swot_analysis; swot=json.loads(raw) if isinstance(raw,str) else raw
            for key,lbl,c in [('strengths','✅ Forces',C_GREEN),('weaknesses','⚠️ Faiblesses',C_ORANGE),('opportunities','🚀 Opportunités',C_BLUE),('threats','🔴 Menaces',C_RED)]:
                if key in swot:
                    items=swot[key]; text=' • '.join(items) if isinstance(items,list) else str(items)
                    row=[[Paragraph(f'<b>{lbl}</b>',ParagraphStyle('sw',parent=s['Lbl'],textColor=C_WHITE,fontName='Helvetica-Bold',fontSize=8)),Paragraph(text,s['BodyG'])]]
                    t=Table(row,colWidths=[3.2*cm,W-3.2*cm])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),c),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,C_BLUE_LT)]))
                    el.append(t); el.append(Spacer(1,1*mm))
        except: el.append(Paragraph(str(competitor.swot_analysis),s['Body']))
    if competitor.notes: _sec('📝 Notes',el); el.append(Paragraph(competitor.notes,s['Body']))
    _foot(el); doc.build(el); buf.seek(0); return buf


def generate_prospect_pdf(prospect):
    buf=BytesIO(); doc=_doc(buf); s=_s(); el=[]
    el.append(_banner('Fiche Prospect',prospect.company_name,f'Score: {prospect.relevance_score or 0}%',C_TEAL))
    el.append(Spacer(1,4*mm)); _pill('Pertinence',prospect.relevance_score or 0,el)
    _sec('🏢 Informations Entreprise',el)
    _kv('Secteur',f"{prospect.sector or ''}{' / '+prospect.sub_sector if prospect.sub_sector else ''}",el)
    _kv('Pays/Ville',f"{prospect.country or ''} · {prospect.city or ''}",el)
    _kv('Taille',prospect.size,el); _kv('Effectif',prospect.employees_count,el)
    _kv('Site Web',prospect.website,el); _kv('LinkedIn',prospect.linkedin_url,el)
    _sec('👤 Contact Principal',el)
    _kv('Nom',prospect.contact_name,el); _kv('Fonction',prospect.contact_title,el)
    _kv('Email',prospect.email,el); _kv('Téléphone',prospect.phone,el)
    if prospect.why_relevant:
        _sec('💡 Pertinence IA',el)
        t=Table([[Paragraph(prospect.why_relevant,s['Body'])]],colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_TEAL_LT),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBEFORE',(0,0),(0,-1),3,C_TEAL)]))
        el.append(t)
    if prospect.notes: _sec('📝 Notes',el); el.append(Paragraph(prospect.notes,s['Body']))
    _foot(el); doc.build(el); buf.seek(0); return buf


def generate_quote_pdf(quote, company):
    buf=BytesIO(); doc=_doc(buf); s=_s(); el=[]
    prospect=quote.opportunity.prospect if quote.opportunity else None
    el.append(_banner('DEVIS COMMERCIAL',company.name,quote.quote_number))
    el.append(Spacer(1,5*mm))

    def info_col(title,lines,color):
        rows=[[Paragraph(title,ParagraphStyle('BT',parent=s['Lbl'],textColor=C_WHITE,fontName='Helvetica-Bold'))]]
        for l in lines: rows.append([Paragraph(l or '—',s['Body'])])
        t=Table(rows,colWidths=[W/2-5*mm])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),color),('BACKGROUND',(0,1),(-1,-1),C_GRAY_XL),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,1),(-1,-1),.3,C_BLUE_LT)]))
        return t

    cl = [f'<b>{prospect.company_name}</b>',prospect.contact_name or '',prospect.email or '',prospect.phone or ''] if prospect else ['—']
    hdr=Table([[info_col('ÉMETTEUR',[f'<b>{company.name}</b>',company.sector or '',company.country or ''],C_BLUE2),Spacer(10*mm,1),info_col('CLIENT',cl,C_TEAL)]],colWidths=[W/2-5*mm,10*mm,W/2-5*mm])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    el.append(hdr); el.append(Spacer(1,5*mm))

    meta=[['Date d\'émission','Valable jusqu\'au','Statut','N° Devis'],
          [quote.sent_at.strftime('%d/%m/%Y') if quote.sent_at else datetime.now().strftime('%d/%m/%Y'),
           quote.valid_until.strftime('%d/%m/%Y') if quote.valid_until else '—',
           quote.status.upper(),quote.quote_number]]
    mt=Table(meta,colWidths=[W/4]*4)
    mt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C_BLUE2),('TEXTCOLOR',(0,0),(-1,0),C_WHITE),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8.5),('BACKGROUND',(0,1),(-1,-1),C_BLUE_XL),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('GRID',(0,0),(-1,-1),.4,C_BLUE_LT)]))
    el.append(mt); el.append(Spacer(1,5*mm))

    _sec('📦 Détail des Prestations',el)
    cw=[W*.43,W*.08,W*.17,W*.10,W*.18]
    rows=[[Paragraph(h,s['TH']) for h in ['Description','Qté','P.U. HT','Remise','Total HT']]]
    for item in quote.items:
        rows.append([Paragraph(item.description or '',s['TD']),Paragraph(str(item.quantity),s['TDC']),Paragraph(f"{item.unit_price:.2f} TND",s['TDR']),Paragraph(f"{item.discount:.0f}%",s['TDC']),Paragraph(f"{item.total:.2f} TND",s['TDR'])])
    it=Table(rows,colWidths=cw)
    it.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C_BLUE),('ROWBACKGROUNDS',(0,1),(-1,-1),[C_WHITE,C_GRAY_XL]),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(0,-1),10),('RIGHTPADDING',(-1,0),(-1,-1),10),('GRID',(0,0),(-1,-1),.3,C_BLUE_LT),('FONTSIZE',(0,0),(-1,-1),8.5)]))
    el.append(it); el.append(Spacer(1,3*mm))

    tva_amt=(quote.total_ht or 0)*(quote.tva or 19)/100
    tots=[['',Paragraph('Total HT',s['TDR']),Paragraph(f"{quote.total_ht:.2f} TND",s['TDR'])],
          ['',Paragraph(f"TVA ({quote.tva:.0f}%)",s['TDR']),Paragraph(f"{tva_amt:.2f} TND",s['TDR'])],
          ['',Paragraph('<b>TOTAL TTC</b>',s['TDTot']),Paragraph(f"<b>{quote.total_ttc:.2f} TND</b>",s['TDTot'])]]
    tt=Table(tots,colWidths=[W*.52,W*.25,W*.23])
    tt.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(1,0),(-1,-1),10),('GRID',(1,0),(-1,-1),.3,C_BLUE_LT),('BACKGROUND',(1,2),(-1,2),C_BLUE),('FONTNAME',(1,2),(-1,2),'Helvetica-Bold'),('TEXTCOLOR',(1,2),(-1,2),C_WHITE)]))
    el.append(tt)

    if quote.notes:
        _sec('📝 Notes & Conditions',el)
        t=Table([[Paragraph(quote.notes,s['Body'])]],colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_GRAY_XL),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        el.append(t)

    el.append(Spacer(1,8*mm))
    sig=[['Fait à ____________________','Le ____________________',''],['','',''],['Signature & Cachet Client','Signature & Cachet Vendeur','']]
    st=Table(sig,colWidths=[W/3,W/3,W/3])
    st.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),8),('FONTNAME',(0,0),(-1,-1),'Helvetica'),('TEXTCOLOR',(0,0),(-1,-1),C_GRAY),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,1),(-1,1),20),('LINEABOVE',(0,2),(1,2),.5,C_GRAY)]))
    el.append(st)
    _foot(el,company.name); doc.build(el); buf.seek(0); return buf