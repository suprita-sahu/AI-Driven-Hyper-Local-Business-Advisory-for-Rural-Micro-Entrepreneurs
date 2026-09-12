import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from html import escape
import re
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_price_rows(value):
    items = [item.strip(" -") for item in re.split(r"[,;\n]+", str(value)) if item.strip(" -")]
    if not items:
        items = ["No price guidance returned"]
    return "".join(
        f"<div class='price-row'><span class='price-index'>{index:02d}</span>"
        f"<span>{escape(item)}</span></div>"
        for index, item in enumerate(items, start=1)
    )


def effectiveness_metrics(fin, study):
    """Create transparent, reportable effectiveness indicators from the advisory output."""
    swot = study.get("swot_analysis", {})
    strengths = len(swot.get("strengths", []))
    opportunities = len(swot.get("opportunities", []))
    threats = len(swot.get("threats", [])) + len(study.get("localized_threats", []))
    channels = len(study.get("market_reach", {}).get("primary_distribution_channels", []))
    density = str(study.get("competitor_mapping", {}).get("estimated_density_in_block", "Moderate")).lower()
    density_score = {"low": 90, "moderate": 70, "high": 45}.get(density, 65)
    demand_score = min(100, 45 + opportunities * 10 + channels * 5)
    resilience_score = max(35, min(100, 55 + strengths * 8 - threats * 5))
    financial_score = 75 if fin.get("sanctioned_loan_amount", 0) > 0 else 20
    overall = round((demand_score + resilience_score + density_score + financial_score) / 4)
    rating = "Strong" if overall >= 80 else "Promising" if overall >= 65 else "Needs Review"
    return {
        "overall": overall,
        "rating": rating,
        "Demand Opportunity": demand_score,
        "Operational Resilience": resilience_score,
        "Competitive Position": density_score,
        "Financial Readiness": financial_score,
        "strengths": strengths,
        "opportunities": opportunities,
        "threats": threats,
        "channels": channels,
    }


def build_effectiveness_pdf(data, location, category, language):
    """Build a PDF advisory report with ratings, charts, and the financial snapshot."""
    fin = data.get("financial_roadmap", {})
    study = data.get("feasibility_study", {})
    scheme = fin.get("scheme_details", {})
    metrics = effectiveness_metrics(fin, study)
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#0f172a"), fontSize=22, leading=27, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#475569"), fontSize=9, leading=13, spaceAfter=16))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#1d4ed8"), fontSize=13, leading=16, spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], textColor=colors.HexColor("#334155"), fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="Rating", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.HexColor("#059669"), fontSize=26, leading=30))

    def money(value):
        return f"INR {float(value or 0):,.2f}"

    story = [
        Paragraph("Rural Enterprise Effectiveness Report", styles["ReportTitle"]),
        Paragraph(f"{escape(category)} | {escape(location)} | Language: {escape(language)}", styles["ReportSubtitle"]),
        Paragraph(f"Overall Effectiveness Rating: {metrics['overall']}/100", styles["Rating"]),
        Paragraph(metrics["rating"], styles["ReportSubtitle"]),
    ]

    summary_data = [
        ["Project Cost", "Sanctioned Loan", "Quarterly Service", "Scheme"],
        [money(fin.get("total_project_cost")), money(fin.get("sanctioned_loan_amount")), money(fin.get("quarterly_emi")), str(scheme.get("name", "N/A"))],
    ]
    summary = Table(summary_data, colWidths=[43 * mm] * 4)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([summary, Spacer(1, 8), Paragraph("Effectiveness Indicators", styles["Section"])])

    labels = ["Demand Opportunity", "Operational Resilience", "Competitive Position", "Financial Readiness"]
    values = [metrics[label] for label in labels]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.1), dpi=150)
    fig.patch.set_facecolor("white")
    axes[0].barh(labels[::-1], values[::-1], color=["#059669", "#0284c7", "#6366f1", "#1d4ed8"])
    axes[0].set_xlim(0, 100)
    axes[0].set_title("Effectiveness Scores", fontsize=11, color="#0f172a", pad=10)
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{int(value)}"))
    axes[0].grid(axis="x", alpha=0.2)
    axes[0].set_axisbelow(True)
    axes[1].pie([metrics["strengths"], metrics["opportunities"], metrics["threats"]], labels=["Strengths", "Opportunities", "Threats"], colors=["#059669", "#0284c7", "#f43f5e"], autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8})
    axes[1].set_title("Advisory Signal Mix", fontsize=11, color="#0f172a", pad=10)
    fig.tight_layout()
    chart_buffer = BytesIO()
    fig.savefig(chart_buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    chart_buffer.seek(0)
    story.append(Image(chart_buffer, width=175 * mm, height=55 * mm))

    story.append(Paragraph("Business Evidence", styles["Section"]))
    evidence = [
        ["Indicator", "Value"],
        ["Market catchment", str(study.get("market_reach", {}).get("catchment_radius_km", "N/A"))],
        ["Distribution channels", str(metrics["channels"])],
        ["Local opportunities identified", str(metrics["opportunities"])],
        ["Threat signals", str(metrics["threats"])],
        ["Competitor density", str(study.get("competitor_mapping", {}).get("estimated_density_in_block", "N/A"))],
    ]
    evidence_table = Table(evidence, colWidths=[75 * mm, 100 * mm])
    evidence_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#334155")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(evidence_table)
    story.append(Paragraph("This report is an analytical projection based on the submitted business profile and generated feasibility signals. Validate assumptions before making lending or investment decisions.", styles["BodySmall"]))
    doc.build(story)
    return pdf_buffer.getvalue()


def render_pdf_download(pdf_data, file_name, key):
    st.download_button(
        label="Download Business Effectiveness Report (PDF)",
        data=pdf_data,
        file_name=file_name,
        mime="application/pdf",
        key=key,
        use_container_width=True
    )


UI_TEXT = {
    "English": {
        "vector": "BENEFICIARY DOSSIER / INPUT VECTOR", "state": "State", "district": "District",
        "block": "Block / Mandal", "village": "Panchayat / Village", "category": "Business Category",
        "capital": "Available Margin Capital (INR) [10%]", "language": "Language",
        "generate": "Generate Enterprise Dossier", "title": "MoSJE Rural Advisor AI",
        "badge": "COMMAND CENTER", "status": "Groq LPU Active", "market": "Market Catchment",
        "swot": "Strategic SWOT", "risks": "Saturation & Risks", "pricing": "Pricing Architecture",
        "amortization": "Amortization Table", "project_cost": "Total Project Cost",
        "debt": "Sanctioned Debt (90%)", "service": "Quarterly Debt Service", "scheme": "Routed Scheme",
        "catchment": "Catchment Radius", "consumer": "Consumer Base", "channels": "Distribution Channels",
        "niches": "Identified Local Niches", "density": "Estimated Density", "threats": "Operational Threats",
        "strategy": "Pricing Strategy", "price_points": "Suggested Price Points", "purchasing": "Purchasing Power Alignment",
        "strengths": "Strengths", "opportunities": "Opportunities", "weaknesses": "Weaknesses", "localized_threats": "Threats",
        "offline": "Enter venture parameters in the sidebar and click Generate Enterprise Dossier to start."
    },
    "Hindi": {
        "vector": "लाभार्थी विवरण / इनपुट वेक्टर", "state": "राज्य", "district": "जिला", "block": "ब्लॉक / मंडल", "village": "पंचायत / गांव", "category": "व्यवसाय श्रेणी", "capital": "उपलब्ध मार्जिन पूंजी (INR) [10%]", "language": "भाषा", "generate": "उद्यम विवरण बनाएं", "title": "MoSJE ग्रामीण सलाहकार AI", "badge": "कमांड सेंटर", "status": "Groq LPU सक्रिय", "market": "बाजार क्षेत्र", "swot": "रणनीतिक SWOT", "risks": "जोखिम और प्रतिस्पर्धा", "pricing": "मूल्य निर्धारण", "amortization": "किस्त तालिका", "project_cost": "कुल परियोजना लागत", "debt": "स्वीकृत ऋण (90%)", "service": "त्रैमासिक ऋण सेवा", "scheme": "चयनित योजना", "catchment": "बाजार क्षेत्र की दूरी", "consumer": "उपभोक्ता आधार", "channels": "वितरण माध्यम", "niches": "स्थानीय अवसर", "density": "अनुमानित घनत्व", "threats": "परिचालन जोखिम", "strategy": "मूल्य रणनीति", "price_points": "सुझाए गए मूल्य", "purchasing": "क्रय शक्ति अनुकूलता", "strengths": "मजबूतियां", "opportunities": "अवसर", "weaknesses": "कमजोरियां", "localized_threats": "खतरे", "offline": "साइडबार में जानकारी भरें और उद्यम विवरण बनाएं पर क्लिक करें।"
    },
    "Telugu": {
        "vector": "లబ్ధిదారు వివరాలు / ఇన్‌పుట్ వెక్టర్", "state": "రాష్ట్రం", "district": "జిల్లా", "block": "బ్లాక్ / మండలం", "village": "పంచాయతీ / గ్రామం", "category": "వ్యాపార వర్గం", "capital": "అందుబాటులో ఉన్న మార్జిన్ మూలధనం (INR) [10%]", "language": "భాష", "generate": "ఎంటర్‌ప్రైజ్ వివరాలు రూపొందించండి", "title": "MoSJE గ్రామీణ సలహాదారు AI", "badge": "కమాండ్ సెంటర్", "status": "Groq LPU యాక్టివ్", "market": "మార్కెట్ పరిధి", "swot": "వ్యూహాత్మక SWOT", "risks": "ప్రమాదాలు మరియు పోటీ", "pricing": "ధరల నిర్మాణం", "amortization": "వాయిదాల పట్టిక", "project_cost": "మొత్తం ప్రాజెక్ట్ ఖర్చు", "debt": "మంజూరైన రుణం (90%)", "service": "త్రైమాసిక రుణ చెల్లింపు", "scheme": "ఎంపిక చేసిన పథకం", "catchment": "మార్కెట్ పరిధి", "consumer": "వినియోగదారుల ఆధారం", "channels": "పంపిణీ మార్గాలు", "niches": "స్థానిక అవకాశాలు", "density": "అంచనా సాంద్రత", "threats": "నిర్వహణా ప్రమాదాలు", "strategy": "ధరల వ్యూహం", "price_points": "సూచించిన ధరలు", "purchasing": "కొనుగోలు శక్తి అనుసరణ", "strengths": "బలాలు", "opportunities": "అవకాశాలు", "weaknesses": "బలహీనతలు", "localized_threats": "ముప్పులు", "offline": "సైడ్‌బార్‌లో వివరాలు నమోదు చేసి ఎంటర్‌ప్రైజ్ వివరాలు రూపొందించండి నొక్కండి."
    },
    "Tamil": {"vector": "பயனாளி விவரம் / உள்ளீட்டு திசையன்", "state": "மாநிலம்", "district": "மாவட்டம்", "block": "வட்டம்", "village": "ஊராட்சி / கிராமம்", "category": "வணிக வகை", "capital": "கிடைக்கும் விளிம்பு மூலதனம் (INR) [10%]", "language": "மொழி", "generate": "நிறுவன விவரத்தை உருவாக்கு", "title": "MoSJE கிராமப்புற ஆலோசகர் AI", "badge": "கட்டுப்பாட்டு மையம்", "status": "Groq LPU செயலில்", "market": "சந்தை பரப்பு", "swot": "மூலோபாய SWOT", "risks": "அபாயங்கள் மற்றும் போட்டி", "pricing": "விலை அமைப்பு", "amortization": "தவணை அட்டவணை", "project_cost": "மொத்த திட்டச் செலவு", "debt": "அனுமதிக்கப்பட்ட கடன் (90%)", "service": "காலாண்டு கடன் சேவை", "scheme": "தேர்ந்தெடுக்கப்பட்ட திட்டம்", "catchment": "சந்தை சுற்றளவு", "consumer": "நுகர்வோர் தளம்", "channels": "விநியோக வழிகள்", "niches": "உள்ளூர் வாய்ப்புகள்", "density": "மதிப்பிடப்பட்ட அடர்த்தி", "threats": "செயல்பாட்டு அபாயங்கள்", "strategy": "விலை உத்தி", "price_points": "பரிந்துரைக்கப்பட்ட விலைகள்", "purchasing": "வாங்கும் திறன் பொருத்தம்", "strengths": "பலங்கள்", "opportunities": "வாய்ப்புகள்", "weaknesses": "பலவீனங்கள்", "localized_threats": "அச்சுறுத்தல்கள்", "offline": "பக்கப்பட்டியில் விவரங்களை உள்ளிட்டு நிறுவன விவரத்தை உருவாக்கு என்பதை அழுத்தவும்."},
    "Marathi": {"vector": "लाभार्थी तपशील / इनपुट वेक्टर", "state": "राज्य", "district": "जिल्हा", "block": "ब्लॉक / मंडळ", "village": "ग्रामपंचायत / गाव", "category": "व्यवसाय श्रेणी", "capital": "उपलब्ध मार्जिन भांडवल (INR) [10%]", "language": "भाषा", "generate": "उद्यम तपशील तयार करा", "title": "MoSJE ग्रामीण सल्लागार AI", "badge": "कमांड सेंटर", "status": "Groq LPU सक्रिय", "market": "बाजार क्षेत्र", "swot": "धोरणात्मक SWOT", "risks": "जोखीम आणि स्पर्धा", "pricing": "किंमत रचना", "amortization": "हप्ता तक्ता", "project_cost": "एकूण प्रकल्प खर्च", "debt": "मंजूर कर्ज (90%)", "service": "त्रैमासिक कर्ज सेवा", "scheme": "निवडलेली योजना", "catchment": "बाजार क्षेत्र", "consumer": "ग्राहक आधार", "channels": "वितरण मार्ग", "niches": "स्थानिक संधी", "density": "अंदाजे घनता", "threats": "कार्यकारी धोके", "strategy": "किंमत धोरण", "price_points": "सुचवलेल्या किंमती", "purchasing": "खरेदी शक्ती सुसंगती", "strengths": "बलस्थाने", "opportunities": "संधी", "weaknesses": "कमकुवत बाजू", "localized_threats": "धोके", "offline": "साइडबारमध्ये माहिती भरून उद्यम तपशील तयार करा वर क्लिक करा."},
    "Bengali": {"vector": "উপকারভোগীর বিবরণ / ইনপুট ভেক্টর", "state": "রাজ্য", "district": "জেলা", "block": "ব্লক / মণ্ডল", "village": "পঞ্চায়েত / গ্রাম", "category": "ব্যবসার বিভাগ", "capital": "উপলব্ধ মার্জিন মূলধন (INR) [10%]", "language": "ভাষা", "generate": "এন্টারপ্রাইজ বিবরণ তৈরি করুন", "title": "MoSJE গ্রামীণ পরামর্শদাতা AI", "badge": "কমান্ড সেন্টার", "status": "Groq LPU সক্রিয়", "market": "বাজার পরিধি", "swot": "কৌশলগত SWOT", "risks": "ঝুঁকি ও প্রতিযোগিতা", "pricing": "মূল্য কাঠামো", "amortization": "কিস্তি সারণি", "project_cost": "মোট প্রকল্প ব্যয়", "debt": "অনুমোদিত ঋণ (90%)", "service": "ত্রৈমাসিক ঋণ পরিষেবা", "scheme": "নির্বাচিত প্রকল্প", "catchment": "বাজার পরিধি", "consumer": "ভোক্তা ভিত্তি", "channels": "বিতরণ মাধ্যম", "niches": "স্থানীয় সুযোগ", "density": "আনুমানিক ঘনত্ব", "threats": "পরিচালনাগত ঝুঁকি", "strategy": "মূল্য নির্ধারণ কৌশল", "price_points": "প্রস্তাবিত মূল্য", "purchasing": "ক্রয় ক্ষমতার সামঞ্জস্য", "strengths": "শক্তি", "opportunities": "সুযোগ", "weaknesses": "দুর্বলতা", "localized_threats": "হুমকি", "offline": "সাইডবারে তথ্য পূরণ করে এন্টারপ্রাইজ বিবরণ তৈরি করুন-এ ক্লিক করুন।"}
}

TABLE_HEADERS = {
    "English": {"quarter": "Quarter", "phase": "Phase", "principal_repayment": "Principal", "interest_payment": "Interest", "total_installment": "Installment", "remaining_balance": "Balance"},
    "Hindi": {"quarter": "तिमाही", "phase": "चरण", "principal_repayment": "मूलधन", "interest_payment": "ब्याज", "total_installment": "किस्त", "remaining_balance": "शेष राशि"},
    "Telugu": {"quarter": "త్రైమాసికం", "phase": "దశ", "principal_repayment": "అసలు", "interest_payment": "వడ్డీ", "total_installment": "వాయిదా", "remaining_balance": "మిగిలిన బాకీ"},
    "Tamil": {"quarter": "காலாண்டு", "phase": "நிலை", "principal_repayment": "அசல்", "interest_payment": "வட்டி", "total_installment": "தவணை", "remaining_balance": "மீதம்"},
    "Marathi": {"quarter": "त्रैमासिक", "phase": "टप्पा", "principal_repayment": "मुद्दल", "interest_payment": "व्याज", "total_installment": "हप्ता", "remaining_balance": "शिल्लक"},
    "Bengali": {"quarter": "ত্রৈমাসিক", "phase": "পর্যায়", "principal_repayment": "মূলধন", "interest_payment": "সুদ", "total_installment": "কিস্তি", "remaining_balance": "বকেয়া"}
}

st.set_page_config(
    page_title="MoSJE Enterprise Intelligence Terminal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- Inject Live Background Canvas into Parent Window -----------------
components.html(
    """
    <script>
    (function() {
        const parentDoc = window.parent.document;
        
        // Prevent duplicate canvas elements across Streamlit reruns
        if (parentDoc.getElementById("ocr-canvas-container")) {
            return;
        }

        const container = parentDoc.createElement("div");
        container.id = "ocr-canvas-container";
        container.style.position = "fixed";
        container.style.top = "0";
        container.style.left = "0";
        container.style.width = "100vw";
        container.style.height = "100vh";
        container.style.pointerEvents = "none";
        container.style.zIndex = "-1";
        container.style.overflow = "hidden";

        const canvas = parentDoc.createElement("canvas");
        canvas.id = "ocr-stream-canvas";
        canvas.style.width = "100%";
        canvas.style.height = "100%";
        canvas.style.display = "block";
        container.appendChild(canvas);
        parentDoc.body.prepend(container);

        const ctx = canvas.getContext("2d");
        let width = 0, height = 0, dpr = window.parent.devicePixelRatio || 1;
        const mouse = { x: -1000, y: -1000, active: false };

        window.parent.addEventListener("mousemove", (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
            mouse.active = true;
        });
        window.parent.addEventListener("mouseleave", () => {
            mouse.active = false;
        });

        function resize() {
            width = window.parent.innerWidth;
            height = window.parent.innerHeight;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            canvas.style.width = width + "px";
            canvas.style.height = height + "px";
            ctx.scale(dpr, dpr);
        }
        window.parent.addEventListener("resize", resize);
        resize();

        const LABEL_TOKENS = [
            "NET QTY 500g", "MRP ₹280.00", "RULE 6(1)(a) PASS", "PKD: 08/2026",
            "MFS 6.5% P.A.", "TLS 8.0% P.A.", "10% MARGIN", "90% DEBT",
            "QUARTERLY AMORT", "HAAT FOOTFALL: HIGH", "WORKING CAPITAL PASS",
            "MANDI DIST: 7.4KM", "SCA/CA VERIFIED"
        ];

        class LabelScanNode {
            constructor() { this.init(true); }
            init(randomY = false) {
                this.x = Math.random() * width;
                this.y = randomY ? Math.random() * height : height + Math.random() * 40;
                this.text = LABEL_TOKENS[Math.floor(Math.random() * LABEL_TOKENS.length)];
                this.type = Math.random() > 0.45 ? "TOKEN" : "RETICLE";
                this.alpha = Math.random() * 0.5 + 0.2;
                this.fadeSpeed = (Math.random() * 0.008 + 0.003) * (Math.random() > 0.5 ? 1 : -1);
                this.vx = (Math.random() - 0.5) * 0.35;
                this.vy = -(Math.random() * 0.45 + 0.2);
                this.boxSize = Math.random() * 14 + 16;
                this.fontSize = Math.floor(Math.random() * 2) + 11;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                this.alpha += this.fadeSpeed;
                if (this.alpha >= 0.85) { this.alpha = 0.85; this.fadeSpeed = -Math.abs(this.fadeSpeed); }
                else if (this.alpha <= 0.1) { this.fadeSpeed = Math.abs(this.fadeSpeed); }
                if (this.y < -40 || this.x < -40 || this.x > width + 40) { this.init(false); }
            }
            draw() {
                const dx = this.x - mouse.x, dy = this.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const isHovered = mouse.active && dist < 140;
                const currentAlpha = isHovered ? Math.min(1, this.alpha + 0.4) : this.alpha;
                const strokeRgb = "29, 78, 216";
                const dotRgb = "4, 120, 87";

                ctx.save();
                ctx.translate(this.x, this.y);
                if (this.type === "TOKEN") {
                    ctx.font = `600 ${this.fontSize}px monospace`;
                    ctx.fillStyle = `rgba(${strokeRgb}, ${currentAlpha * 0.95})`;
                    ctx.fillText(this.text, 0, 0);
                    ctx.beginPath();
                    ctx.arc(-6, -3, 2, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(${dotRgb}, ${currentAlpha})`;
                    ctx.fill();
                } else {
                    const s = this.boxSize, arm = 5;
                    ctx.strokeStyle = `rgba(${strokeRgb}, ${currentAlpha * 0.85})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(-s, -s + arm); ctx.lineTo(-s, -s); ctx.lineTo(-s + arm, -s);
                    ctx.moveTo(s - arm, -s); ctx.lineTo(s, -s); ctx.lineTo(s, -s + arm);
                    ctx.moveTo(-s, s - arm); ctx.lineTo(-s, s); ctx.lineTo(-s + arm, s);
                    ctx.moveTo(s - arm, s); ctx.lineTo(s, s); ctx.lineTo(s, s - arm);
                    ctx.stroke();
                }
                ctx.restore();
            }
        }

        const nodes = Array.from({ length: 45 }, () => new LabelScanNode());
        function animate() {
            ctx.clearRect(0, 0, width, height);
            for (let i = 0; i < nodes.length; i++) {
                nodes[i].update();
                nodes[i].draw();
            }
            requestAnimationFrame(animate);
        }
        animate();
    })();
    </script>
    """,
    height=0,
    width=0
)

# ----------------- Field Intelligence Styling -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

    :root {
        --bg-color: #cbdcf7;
        --card-bg: rgba(255, 255, 255, 0.94);
        --card-border: rgba(96, 165, 250, 0.45);
        --card-shadow: 0 24px 45px -15px rgba(29, 78, 216, 0.16), 0 0 35px -5px rgba(37, 99, 235, 0.12), inset 0 1px 0 rgba(255, 255, 255, 1);
        --cyan-glow: #0284c7;
        --emerald-accent: #059669;
        --text-main: #0f172a;
        --text-muted: #334155;
    }

    html, body, [class*="css"], .stApp {
        font-family: 'DM Sans', sans-serif !important;
        background: #cbdcf7 !important;
        color: var(--text-main) !important;
    }

    .main .block-container {
        max-width: 1440px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #cbdcf7 !important;
        background-image: linear-gradient(to right, rgba(30, 64, 175, 0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(30, 64, 175, 0.06) 1px, transparent 1px) !important;
        background-size: 44px 44px;
        mask-image: none !important;
        -webkit-mask-image: none !important;
    }
    h1, h2, h3, h4, p { letter-spacing: 0 !important; }
    h1, h2, h3, h4,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    .kpi-title,
    .glass-box span,
    .glass-box strong {
        color: #000000 !important;
    }
    [style*="text-transform:uppercase"],
    [style*="text-transform: uppercase"] {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    .stTabs [role="tabpanel"] {
        background: #ffffff !important;
        border: 1px solid rgba(96, 165, 250, 0.35);
        border-radius: 18px;
        padding: 18px 16px 10px;
        box-shadow: 0 14px 30px -22px rgba(29, 78, 216, 0.42);
    }
    .stTabs [role="tabpanel"] p,
    .stTabs [role="tabpanel"] li {
        color: #0f172a;
    }

    /* Seamless Sidebar Integration */
    section[data-testid="stSidebar"] {
        background: rgba(241, 245, 254, 0.82) !important;
        backdrop-filter: blur(18px);
        border-right: 1px solid var(--card-border) !important;
    }
    header[data-testid="stHeader"] {
        background: rgba(203, 220, 247, 0.92) !important;
        height: 3rem !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label*="sidebar" i],
    button[title*="sidebar" i] {
        visibility: visible !important;
        opacity: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid rgba(96, 165, 250, 0.65) !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 14px rgba(29, 78, 216, 0.18) !important;
        z-index: 100 !important;
    }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] svg,
    header[data-testid="stHeader"] button svg,
    button[aria-label*="sidebar" i] svg,
    button[title*="sidebar" i] svg {
        color: #000000 !important;
        fill: none !important;
        stroke: #000000 !important;
        filter: brightness(0) !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarCollapseButton"] svg *,
    [data-testid="stSidebarCollapsedControl"] svg *,
    [data-testid="collapsedControl"] svg *,
    header[data-testid="stHeader"] button svg * {
        color: #000000 !important;
        fill: none !important;
        stroke: #000000 !important;
    }
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] label {
        color: #000000 !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        font-family: 'Space Mono', monospace !important;
        text-transform: uppercase !important;
    }
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label {
        color: #000000 !important;
        font-weight: 700 !important;
    }

    /* Fixed Input Text & Dropdown Visibility */
    section[data-testid="stSidebar"] div[data-baseweb="input"],
    section[data-testid="stSidebar"] div[data-baseweb="select"],
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #000000 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div {
        background: #ffffff !important;
        border: 0 !important;
        border-radius: 9px !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1px solid #000000 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="input"]:focus-within,
    section[data-testid="stSidebar"] div[data-baseweb="select"]:focus-within,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
        border-color: #000000 !important;
        outline: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
        background: #ffffff !important;
        color: #1d4ed8 !important;
        border: 0 !important;
        border-left: 1px solid #dbeafe !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="input"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 0.85rem !important;
    }

    /* Top Command Header */
    .command-header {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid var(--card-border);
        box-shadow: var(--card-shadow);
        backdrop-filter: blur(28px);
        border-radius: 24px;
        padding: 18px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    .command-header::after {
        content: "FIELD INTELLIGENCE / 2026";
        position: absolute;
        right: 20px;
        bottom: 7px;
        color: rgba(37, 99, 235, 0.48);
        font: 700 9px 'Space Mono', monospace;
        letter-spacing: 1.5px;
    }
    .badge-command {
        background: rgba(56, 189, 248, 0.1);
        color: var(--cyan-glow);
        border: 1px solid var(--card-border);
        font-family: 'Space Mono', monospace;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
    }

    /* KPI Cards */
    .kpi-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    .kpi-card {
        background: #ffffff !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(96, 165, 250, 0.35);
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 12px 28px -18px rgba(29, 78, 216, 0.45);
        position: relative;
        overflow: hidden;
        transition: all 0.25s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: var(--cyan-glow);
        box-shadow: 0 16px 30px -10px rgba(37, 99, 235, 0.18);
    }
    .kpi-title {
        font-size: 11px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-number {
        font-family: 'DM Sans', sans-serif;
        font-weight: 800;
        font-size: 1.8rem;
        color: var(--text-main);
    }

    /* Glass Panels */
    .glass-box {
        background: #ffffff !important;
        border: 1px solid rgba(96, 165, 250, 0.35);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 12px 28px -18px rgba(29, 78, 216, 0.38);
    }
    .glass-box p {
        color: #0f172a !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid rgba(96, 165, 250, 0.35);
        padding-bottom: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 12px;
        color: var(--text-muted) !important;
        background: transparent !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(219, 234, 254, 0.9) !important;
        color: var(--cyan-glow) !important;
        border: 1px solid var(--card-border) !important;
    }

    /* Action Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        border-radius: 7px !important;
        border: none !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 20px -2px rgba(37, 99, 235, 0.5) !important;
    }
    div.stButton > button:hover {
        background: #0284c7 !important;
        color: #ffffff !important;
        transform: translateY(-1px);
    }
    div[data-testid="stDownloadButton"] button {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        font-weight: 700 !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: #eff6ff !important;
        color: #000000 !important;
        border-color: #000000 !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        min-height: 46px;
        letter-spacing: 0.2px;
    }
    .pricing-list {
        margin-top: 10px;
        border-top: 1px solid rgba(96, 165, 250, 0.35);
    }
    .price-row {
        display: grid;
        grid-template-columns: 34px 1fr;
        gap: 12px;
        align-items: start;
        padding: 11px 0;
        border-bottom: 1px solid rgba(96, 165, 250, 0.25);
        color: #334155;
        font-size: 13px;
        line-height: 1.45;
    }
    .price-index {
        color: #1d4ed8;
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        padding-top: 2px;
    }
    @media (max-width: 700px) {
        .main .block-container { padding: 1.25rem 1rem 3rem; }
        .command-header { padding: 14px; }
        .command-header::after { display: none; }
        .command-header > div:last-child { display: none !important; }
        .kpi-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .kpi-card { padding: 14px; }
        .kpi-number { font-size: 1.35rem; }
        .stTabs [data-baseweb="tab-list"] { overflow-x: auto; }
    }
</style>
""", unsafe_allow_html=True)

ui = UI_TEXT.get(st.session_state.get("language", "English"), UI_TEXT["English"])

# ----------------- Top Header Component -----------------
st.markdown(f"""
<div class="command-header">
    <div style="display:flex; align-items:center; gap:12px;">
        <div style="width:38px; height:38px; border-radius:16px; background:linear-gradient(135deg, #0284c7, #2563eb); display:flex; align-items:center; justify-content:center; box-shadow:0 8px 20px rgba(37,99,235,.22);">
            <span style="font-family:'Space Mono'; font-weight:700; color:#ffffff; font-size:16px;">₹</span>
        </div>
        <div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-weight:800; font-size:15px; color:#0f172a;">{ui["title"]}</span>
                <span class="badge-command">{ui["badge"]}</span>
            </div>
            <p style="font-size:11px; color:#334155; margin-top:2px;">Ministry of Social Justice & Empowerment • Concessional Lending Grid</p>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px; font-family:'Space Mono'; font-size:11px; color:#334155;">
        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#059669; box-shadow:0 0 8px #059669;"></span>
        <span>{ui["status"]}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Sidebar Inputs -----------------
with st.sidebar:
    st.markdown(f"<p style='font-family:Space Mono; font-size:12px; font-weight:800; color:#000000; margin-bottom:8px; letter-spacing:.4px;'>{UI_TEXT.get(st.session_state.get('language', 'English'), UI_TEXT['English'])['vector']}</p>", unsafe_allow_html=True)
    state = st.text_input(ui["state"], value="Telangana")
    district = st.text_input(ui["district"], value="Warangal")
    block = st.text_input(ui["block"], value="Geesugonda")
    village = st.text_input(ui["village"], value="Dharmaram")
    
    category = st.selectbox(
        ui["category"],
        ["Poultry Farming", "Dairy Milk Chilling & Collection", "Handloom & Rural Textiles", "Kirana & General Retail", "Food Processing & Flour Mill", "Custom Hiring Center (Farm Machinery)"]
    )
    margin_capital = st.number_input(ui["capital"], min_value=5000.0, max_value=500000.0, value=80000.0, step=5000.0)
    language = st.selectbox(ui["language"], ["English", "Hindi", "Telugu", "Tamil", "Marathi", "Bengali"], key="language")
    
    submit_btn = st.button(ui["generate"], type="primary", use_container_width=True)

ui = UI_TEXT.get(language, UI_TEXT["English"])

# ----------------- Main Execution & Tab Layout -----------------
if submit_btn:
    payload = {
        "state": state, "district": district, "block_or_mandal": block,
        "village_or_panchayat": village, "business_category": category,
        "available_margin_capital": margin_capital, "preferred_language": language
    }

    with st.spinner("Synthesizing telemetry via Groq LPU engine..."):
        try:
            res = requests.post("http://localhost:8000/api/v1/generate-advisory", json=payload, timeout=60)
            if res.status_code != 200:
                st.error(f"Backend Exception: {res.text}")
            else:
                data = res.json()
                fin = data.get("financial_roadmap", {})
                study = data.get("feasibility_study", {})
                scheme = fin.get("scheme_details", {})
                report_pdf = build_effectiveness_pdf(
                    data,
                    f"{village}, {district}, {state}",
                    category,
                    language
                )
                report_filename = f"effectiveness_report_{village}_{category}.pdf".replace(" ", "_")

                # Executive Analytics KPI Row
                st.markdown(f"""
                <div class="kpi-row">
                    <div class="kpi-card">
                        <div class="kpi-title">{ui["project_cost"]}</div>
                        <div class="kpi-number">₹{fin.get('total_project_cost', 0):,.2f}</div>
                        <p style="font-size:11px; color:#64748b; margin-top:4px;">100% Calculated Base</p>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">{ui["debt"]}</div>
                        <div class="kpi-number" style="color:#34d399;">₹{fin.get('sanctioned_loan_amount', 0):,.2f}</div>
                        <p style="font-size:11px; color:#64748b; margin-top:4px;">Concessional Facility</p>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">{ui["service"]}</div>
                        <div class="kpi-number" style="color:#f43f5e;">₹{fin.get('quarterly_emi', 0):,.2f}</div>
                        <p style="font-size:11px; color:#64748b; margin-top:4px;">Factoring Moratorium</p>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">{ui["scheme"]}</div>
                        <div class="kpi-number" style="font-size:1.15rem; color:#38bdf8; line-height:2.2;">{scheme.get('name', 'N/A')}</div>
                        <p style="font-size:11px; color:#64748b; margin-top:4px;">{scheme.get('interest_rate_percent', 0)}% p.a. • {scheme.get('tenure_years', 0)} Yrs</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Tabs
                t_market, t_swot, t_comp, t_pricing, t_amort = st.tabs([
                    ui["market"], ui["swot"], ui["risks"], ui["pricing"], ui["amortization"]
                ])

                with t_market:
                    render_pdf_download(report_pdf, report_filename, "pdf_market")
                    mr = study.get("market_reach", {})
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"""
                        <div class="glass-box">
                            <span style="font-size:10px; font-family:'Space Mono'; color:#0284c7; text-transform:uppercase;">{ui["catchment"]}</span>
                            <h4 style="font-weight:700; margin-top:4px; font-size:16px; color:#0f172a;">{mr.get('catchment_radius_km', '5-10 km')}</h4>
                            <span style="font-size:10px; font-family:'Space Mono'; color:#64748b; text-transform:uppercase; display:block; margin-top:12px;">{ui["consumer"]}</span>
                            <p style="font-size:12px; color:#334155; margin-top:4px;">{mr.get('estimated_consumer_base', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f"<div class='glass-box'><span style='font-size:10px; font-family:Space Mono; color:#0284c7; text-transform:uppercase;'>{ui['channels']}</span>", unsafe_allow_html=True)
                        for ch in mr.get("primary_distribution_channels", []):
                            st.markdown(f"<p style='font-size:12px; color:#334155; margin:6px 0;'>- {ch}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown(f"<div class='glass-box'><span style='font-size:10px; font-family:Space Mono; color:#059669; text-transform:uppercase;'>{ui['niches']}</span>", unsafe_allow_html=True)
                    for opp in study.get("opportunity_analysis", []):
                        st.markdown(f"<p style='font-size:12px; color:#334155; margin:6px 0;'>- {opp}</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                with t_swot:
                    render_pdf_download(report_pdf, report_filename, "pdf_swot")
                    swot = study.get("swot_analysis", {})
                    s1, s2 = st.columns(2)
                    with s1:
                        st.markdown(f"<div class='glass-box' style='border-left:3px solid #34d399;'><p style='color:#34d399; font-weight:700; font-size:11px; text-transform:uppercase;'>{ui['strengths']}</p>", unsafe_allow_html=True)
                        for s in swot.get("strengths", []): st.markdown(f"<p style='font-size:12px; color:#334155; margin:4px 0;'>- {s}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                        st.markdown(f"<div class='glass-box' style='border-left:3px solid #38bdf8;'><p style='color:#38bdf8; font-weight:700; font-size:11px; text-transform:uppercase;'>{ui['opportunities']}</p>", unsafe_allow_html=True)
                        for o in swot.get("opportunities", []): st.markdown(f"<p style='font-size:12px; color:#334155; margin:4px 0;'>- {o}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    with s2:
                        st.markdown(f"<div class='glass-box' style='border-left:3px solid #fbbf24;'><p style='color:#fbbf24; font-weight:700; font-size:11px; text-transform:uppercase;'>{ui['weaknesses']}</p>", unsafe_allow_html=True)
                        for w in swot.get("weaknesses", []): st.markdown(f"<p style='font-size:12px; color:#334155; margin:4px 0;'>- {w}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                        st.markdown(f"<div class='glass-box' style='border-left:3px solid #f43f5e;'><p style='color:#f43f5e; font-weight:700; font-size:11px; text-transform:uppercase;'>{ui['localized_threats']}</p>", unsafe_allow_html=True)
                        for t in swot.get("threats", []): st.markdown(f"<p style='font-size:12px; color:#334155; margin:4px 0;'>- {t}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                with t_comp:
                    render_pdf_download(report_pdf, report_filename, "pdf_risks")
                    comp = study.get("competitor_mapping", {})
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"""
                        <div class='glass-box'>
                            <span style='font-size:10px; font-family:Space Mono; color:#0284c7; text-transform:uppercase;'>{ui["density"]}</span>
                            <h4 style='font-size:16px; font-weight:700; margin-top:4px;'>{comp.get('estimated_density_in_block', 'Moderate')}</h4>
                            <p style='font-size:12px; color:#334155; margin-top:8px;'>{comp.get('notes', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<div class='glass-box'><span style='font-size:10px; font-family:Space Mono; color:#e27d86; text-transform:uppercase;'>{ui['threats']}</span>", unsafe_allow_html=True)
                        for threat in study.get("localized_threats", []):
                            st.markdown(f"<p style='font-size:12px; color:#334155; margin:6px 0;'>- {threat}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                with t_pricing:
                    render_pdf_download(report_pdf, report_filename, "pdf_pricing")
                    pricing = study.get("product_market_value_and_pricing", {})
                    st.markdown(f"""
                    <div class='glass-box'>
                        <span style='font-size:10px; font-family:Space Mono; color:#0284c7; text-transform:uppercase;'>{ui["strategy"]}</span>
                        <p style='font-size:12px; color:#334155; margin-top:4px;'>{pricing.get('pricing_strategy', 'N/A')}</p>
                        <hr style='border-color:rgba(96,165,250,0.35); margin:12px 0;'>
                        <span style='font-size:10px; font-family:Space Mono; color:#059669; text-transform:uppercase;'>{ui["price_points"]}</span>
                        <div class='pricing-list'>{build_price_rows(pricing.get('suggested_price_points', 'N/A'))}</div>
                        <hr style='border-color:rgba(96,165,250,0.35); margin:12px 0;'>
                        <span style='font-size:10px; font-family:Space Mono; color:#059669; text-transform:uppercase;'>{ui["purchasing"]}</span>
                        <p style='font-size:12px; color:#334155; margin-top:4px;'>{pricing.get('purchasing_power_alignment', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with t_amort:
                    render_pdf_download(report_pdf, report_filename, "pdf_amortization")
                    schedule = fin.get("amortization_schedule", [])
                    if schedule:
                        df = pd.DataFrame(schedule)
                        table_headers = TABLE_HEADERS.get(language, TABLE_HEADERS["English"])
                        display_df = df.rename(columns={
                            "quarter": table_headers["quarter"],
                            "phase": table_headers["phase"],
                            "principal_repayment": table_headers["principal_repayment"],
                            "interest_payment": table_headers["interest_payment"],
                            "total_installment": table_headers["total_installment"],
                            "remaining_balance": table_headers["remaining_balance"]
                        })
                        numeric_columns = [
                            column for column in [table_headers["principal_repayment"], table_headers["interest_payment"], table_headers["total_installment"], table_headers["remaining_balance"]]
                            if column in display_df.columns
                        ]
                        styled_df = (
                            display_df.style
                            .format({column: "₹{:,.2f}" for column in numeric_columns})
                            .set_properties(**{
                                "font-family": "DM Sans, sans-serif",
                                "font-size": "12px",
                                "color": "#0f172a",
                                "background-color": "#ffffff"
                            })
                            .set_table_styles([
                                {
                                    "selector": "th",
                                    "props": [
                                        ("background-color", "#dbeafe"),
                                        ("color", "#1d4ed8"),
                                        ("font-family", "Space Mono, monospace"),
                                        ("font-size", "11px"),
                                        ("text-transform", "uppercase"),
                                        ("letter-spacing", "0.04em")
                                    ]
                                },
                                {
                                    "selector": "tbody tr:nth-child(even)",
                                    "props": [("background-color", "#eff6ff")]
                                }
                            ])
                        )
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                        st.download_button(
                            label="Export Schedule (CSV)",
                            data=df.to_csv(index=False).encode('utf-8'),
                            file_name=f"audit_{village}_{category}.csv",
                            mime="text/csv"
                        )
        except requests.exceptions.ConnectionError:
            st.error("Backend offline. Make sure `python main.py` is running on port 8000.")
else:
    st.info(ui["offline"])