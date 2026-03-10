"""
Generate sample knowledge-base PDFs for RAG ingestion testing.
Creates 8 books matching the BOOK_LIBRARY filename patterns.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "greenvalue-ai" / "infrastructure" / "qdrant" / "knowledge_base" / "books"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="BookTitle", fontSize=20, spaceAfter=20, alignment=1, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Chapter", fontSize=16, spaceAfter=14, spaceBefore=20, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Section", fontSize=13, spaceAfter=10, spaceBefore=14, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Body", fontSize=10, spaceAfter=8, leading=14))
styles.add(ParagraphStyle(name="TableNote", fontSize=8, spaceAfter=4, textColor=colors.grey))


def make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_pdf(filename, elements):
    path = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    doc.build(elements)
    print(f"  ✅ {filename} ({path.stat().st_size/1024:.0f} KB)")


# ════════════════════════════════════════════════════════════
# Book 1: IVS-Jan-2025 (International Valuation Standards)
# ════════════════════════════════════════════════════════════
def book_01_ivs():
    e = []
    e.append(Paragraph("International Valuation Standards (IVS) January 2025", styles["BookTitle"]))
    e.append(Paragraph("IVSC — International Valuation Standards Council", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: IVS Framework", styles["Chapter"]))
    e.append(Paragraph(
        "The International Valuation Standards (IVS) provide a globally recognised framework for "
        "undertaking valuation assignments. IVS 2025 consolidates all previous editions and introduces "
        "enhanced requirements for sustainability-linked valuations. The framework ensures consistency, "
        "transparency, and competence in real estate appraisal across jurisdictions.", styles["Body"]))
    e.append(Paragraph(
        "IVS 101 — Scope of Work: Every valuation engagement must begin with a clear scope of work that "
        "identifies the asset, the purpose, the basis of value, the valuation date, assumptions, and "
        "limiting conditions. The scope must be documented before the valuation commences.", styles["Body"]))
    e.append(Paragraph(
        "IVS 102 — Investigations and Compliance: Valuers must undertake sufficient investigations to "
        "produce a credible valuation. This includes physical inspection, market evidence analysis, and "
        "verification of tenancy and title information.", styles["Body"]))

    e.append(Paragraph("Chapter 2: Bases of Value", styles["Chapter"]))
    e.append(Paragraph(
        "IVS 104 — Bases of Value: Market Value is defined as the estimated amount for which an asset "
        "should exchange on the date of valuation between a willing buyer and a willing seller in an "
        "arm's-length transaction after proper marketing wherein the parties had each acted knowledgeably, "
        "prudently, and without compulsion. Market Rent is the estimated amount for which an interest in "
        "real property should be leased on the valuation date.", styles["Body"]))
    e.append(Paragraph(
        "Other bases include Investment Value (value to a specific investor), Fair Value (IFRS 13), "
        "Equitable Value, Liquidation Value, and Synergistic Value.", styles["Body"]))

    e.append(Paragraph("Chapter 3: Valuation Approaches", styles["Chapter"]))
    e.append(Paragraph(
        "IVS 105 — Valuation Approaches and Methods: Three generally accepted approaches exist:", styles["Body"]))
    e.append(Paragraph(
        "<b>Market Approach (Sales Comparison):</b> Values are derived from comparable transactions. "
        "Adjustments are applied for differences in location, size, condition, and date of sale. "
        "This is the most common approach for residential properties.", styles["Body"]))
    e.append(Paragraph(
        "<b>Income Approach:</b> Converts future income streams into a present capital value via "
        "capitalisation or discounted cash flow (DCF). Used primarily for income-producing properties.", styles["Body"]))
    e.append(Paragraph(
        "<b>Cost Approach:</b> Estimates replacement or reproduction cost minus accumulated depreciation "
        "plus land value. Suitable for specialized properties with limited market evidence.", styles["Body"]))

    # Adjustment grid table
    e.append(Paragraph("Table 3.1: Sales Comparison Adjustment Grid", styles["Section"]))
    data = [
        ["Factor", "Subject", "Comp 1", "Comp 2", "Comp 3"],
        ["Sale Price", "—", "€285,000", "€310,000", "€265,000"],
        ["Location", "City Centre", "+5%", "0%", "+10%"],
        ["Size (m²)", "95", "-3%", "+2%", "-5%"],
        ["Condition", "Good", "0%", "-4%", "+3%"],
        ["Energy Label", "C", "+2%", "+2%", "+8%"],
        ["Adjusted Value", "—", "€296,400", "€310,000", "€307,100"],
    ]
    e.append(make_table(data, col_widths=[80, 70, 70, 70, 70]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 4: Sustainability in Valuation", styles["Chapter"]))
    e.append(Paragraph(
        "IVS 2025 introduces mandatory consideration of ESG (Environmental, Social, Governance) factors. "
        "Valuers must assess the impact of energy performance certificates, carbon compliance regulations, "
        "and climate risk on property values. Properties with poor energy labels (F/G) face increasing "
        "regulatory risk including potential rental restrictions in EU member states.", styles["Body"]))
    e.append(Paragraph(
        "Research shows that energy-efficient buildings command a 'green premium' of 5–15% in sale price "
        "and 3–8% in rental value. Conversely, buildings with high carbon emissions face 'brown discounts' "
        "of up to 20%. These adjustments must be explicitly documented.", styles["Body"]))

    # Green premium table
    e.append(Paragraph("Table 4.1: Green Premium by Energy Label", styles["Section"]))
    data = [
        ["Energy Label", "Sale Premium", "Rental Premium", "Risk Level"],
        ["A+", "+12–15%", "+6–8%", "Very Low"],
        ["A", "+8–12%", "+4–6%", "Low"],
        ["B", "+5–8%", "+2–4%", "Low"],
        ["C", "+2–5%", "+1–2%", "Moderate"],
        ["D", "Baseline", "Baseline", "Moderate"],
        ["E", "-3–5%", "-1–3%", "Elevated"],
        ["F", "-8–12%", "-4–6%", "High"],
        ["G", "-15–20%", "-6–10%", "Very High"],
    ]
    e.append(make_table(data, col_widths=[80, 80, 80, 80]))

    e.append(PageBreak())
    e.append(Paragraph("Chapter 5: Reporting Requirements", styles["Chapter"]))
    e.append(Paragraph(
        "IVS 106 — Valuation Reporting: All reports must include the identity of the valuer, the date "
        "of valuation, the basis of value, the approach(es) adopted, key inputs and assumptions, "
        "the valuation figure, and any material uncertainty. Electronic delivery is acceptable "
        "provided authentication is verifiable.", styles["Body"]))

    build_pdf("IVS-Jan-2025.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 2: Appraisal of Real Estate 15th
# ════════════════════════════════════════════════════════════
def book_02_appraisal():
    e = []
    e.append(Paragraph("The Appraisal of Real Estate — 15th Edition", styles["BookTitle"]))
    e.append(Paragraph("Appraisal Institute, Chicago", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Real Property and Value", styles["Chapter"]))
    e.append(Paragraph(
        "Real property includes the physical land, improvements, and the bundle of rights associated "
        "with ownership. Value is created by utility, scarcity, desire, and effective purchasing power. "
        "The highest and best use analysis is the foundation of every appraisal — it determines the most "
        "profitable legally permissible, physically possible, financially feasible, and maximally "
        "productive use of the property.", styles["Body"]))

    e.append(Paragraph("Chapter 2: The Sales Comparison Approach", styles["Chapter"]))
    e.append(Paragraph(
        "The sales comparison approach derives market value by comparing the subject to recently sold "
        "comparable properties. Key elements of comparison include: property rights conveyed, financing "
        "terms, conditions of sale, market conditions (time), location, and physical characteristics.", styles["Body"]))
    e.append(Paragraph(
        "Adjustments may be expressed in percentage or dollar amounts. The appraiser must support all "
        "adjustments with market evidence. Paired sales analysis, statistical techniques, and qualitative "
        "analysis are the primary adjustment extraction methods.", styles["Body"]))

    e.append(Paragraph("Table 2.1: Comparable Sales Grid", styles["Section"]))
    data = [
        ["Element", "Subject", "Sale 1", "Sale 2", "Sale 3"],
        ["Sale Price", "—", "$425,000", "$398,000", "$452,000"],
        ["Date of Sale", "Current", "-3 mo", "-6 mo", "-2 mo"],
        ["Time Adj.", "—", "+1.5%", "+3%", "+1%"],
        ["GLA (sq ft)", "2,100", "2,000", "2,200", "1,950"],
        ["Size Adj.", "—", "+$5,000", "-$5,000", "+$7,500"],
        ["Condition", "Average", "Average", "Good", "Fair"],
        ["Cond. Adj.", "—", "$0", "-$12,000", "+$10,000"],
        ["Energy Eff.", "Average", "Average", "Above Avg", "Below Avg"],
        ["Energy Adj.", "—", "$0", "-$8,000", "+$12,000"],
        ["Net Adj.", "—", "+$11,375", "-$13,060", "+$34,020"],
        ["Adj. Price", "—", "$436,375", "$384,940", "$486,020"],
    ]
    e.append(make_table(data, col_widths=[70, 60, 70, 70, 70]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 3: The Cost Approach", styles["Chapter"]))
    e.append(Paragraph(
        "The cost approach estimates value by calculating the cost to reproduce or replace the existing "
        "improvements, less depreciation (physical, functional, external), plus the value of land. "
        "Physical depreciation is caused by wear and tear; functional obsolescence arises from design "
        "deficiencies; external obsolescence stems from factors outside the property.", styles["Body"]))

    e.append(Paragraph("Chapter 4: The Income Approach", styles["Chapter"]))
    e.append(Paragraph(
        "The income capitalization approach converts anticipated future benefits (income) into a present "
        "value. Direct capitalization divides a single year's net operating income (NOI) by a capitalization "
        "rate. Yield capitalization (DCF) discounts projected cash flows over a holding period.", styles["Body"]))

    data = [
        ["Income Parameter", "Value"],
        ["Potential Gross Income (PGI)", "$180,000/yr"],
        ["Vacancy & Collection Loss (5%)", "-$9,000"],
        ["Effective Gross Income (EGI)", "$171,000"],
        ["Operating Expenses", "-$51,300"],
        ["Net Operating Income (NOI)", "$119,700"],
        ["Cap Rate", "6.5%"],
        ["Indicated Value (NOI/Cap Rate)", "$1,841,538"],
    ]
    e.append(Paragraph("Table 4.1: Direct Capitalization", styles["Section"]))
    e.append(make_table(data, col_widths=[200, 120]))

    e.append(Paragraph("Chapter 5: Reconciliation and Final Value", styles["Chapter"]))
    e.append(Paragraph(
        "The appraiser reconciles the value indications from multiple approaches. The approach given "
        "greatest weight depends on the property type, data quality, and purpose. For typical residential "
        "properties, the sales comparison approach usually provides the most reliable indication.", styles["Body"]))

    build_pdf("Appraisal-of-Real-Estate-15th.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 3: Sustainable Home Refurbishment (Thermal Physics)
# ════════════════════════════════════════════════════════════
def book_03_thermal():
    e = []
    e.append(Paragraph("Sustainable Home Refurbishment", styles["BookTitle"]))
    e.append(Paragraph("A Practical Guide to Energy-Efficient Renovation", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Building Fabric and Heat Loss", styles["Chapter"]))
    e.append(Paragraph(
        "Heat loss through the building fabric accounts for 60–80% of total energy consumption in "
        "residential buildings. The three mechanisms of heat transfer are: conduction (through solid "
        "materials), convection (through air movement), and radiation (electromagnetic energy). "
        "The U-value (thermal transmittance) measured in W/m²K quantifies the rate of heat loss "
        "through a building element — lower values indicate better insulation.", styles["Body"]))
    e.append(Paragraph(
        "Heat loss calculation: Q = U × A × ΔT, where Q is heat loss in watts, U is the U-value, "
        "A is the area in m², and ΔT is the temperature difference across the element.", styles["Body"]))

    e.append(Paragraph("Table 1.1: Typical U-Values for Building Elements", styles["Section"]))
    data = [
        ["Building Element", "Uninsulated (W/m²K)", "Insulated (W/m²K)", "Best Practice"],
        ["Solid Brick Wall (225mm)", "2.10", "0.35", "0.18"],
        ["Cavity Wall (unfilled)", "1.60", "0.30", "0.18"],
        ["Timber Frame Wall", "1.90", "0.25", "0.15"],
        ["Concrete Flat Roof", "1.50", "0.20", "0.13"],
        ["Pitched Roof (loft)", "2.30", "0.16", "0.11"],
        ["Suspended Timber Floor", "0.70", "0.22", "0.15"],
        ["Solid Concrete Floor", "0.80", "0.22", "0.13"],
        ["Single Glazing", "5.60", "—", "—"],
        ["Double Glazing (air)", "2.80", "—", "1.40"],
        ["Double Glazing (argon)", "—", "1.20", "1.00"],
        ["Triple Glazing", "—", "0.80", "0.60"],
    ]
    e.append(make_table(data, col_widths=[120, 90, 90, 80]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 2: Insulation Materials", styles["Chapter"]))
    e.append(Paragraph(
        "A building material's effectiveness as an insulator is described by its thermal conductivity "
        "(λ, lambda), measured in W/mK. Lower λ values mean better insulation performance:", styles["Body"]))

    data = [
        ["Material", "λ (W/mK)", "Typical Thickness (mm)", "R-value (m²K/W)"],
        ["EPS (Expanded Polystyrene)", "0.035", "100", "2.86"],
        ["XPS (Extruded Polystyrene)", "0.030", "100", "3.33"],
        ["Glass Wool (mineral)", "0.040", "100", "2.50"],
        ["Rock Wool (stone)", "0.038", "100", "2.63"],
        ["Polyurethane Foam (PUR)", "0.025", "80", "3.20"],
        ["Phenolic Foam", "0.021", "60", "2.86"],
        ["Cellulose Fibre", "0.040", "120", "3.00"],
        ["Aerogel Blanket", "0.015", "40", "2.67"],
        ["Vacuum Insulation Panel", "0.007", "25", "3.57"],
    ]
    e.append(Paragraph("Table 2.1: Insulation Material Thermal Conductivity", styles["Section"]))
    e.append(make_table(data, col_widths=[130, 65, 100, 90]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 3: Energy Performance Certificates", styles["Chapter"]))
    e.append(Paragraph(
        "The Energy Performance Certificate (EPC) rates a building from A (most efficient) to G "
        "(least efficient). The rating is primarily based on the building's overall U-value, "
        "heating system efficiency, and lighting. EU regulations require all buildings to have an "
        "EPC when sold, rented, or newly constructed.", styles["Body"]))

    data = [
        ["Energy Label", "kWh/m²/year", "Avg U-Value (W/m²K)", "Description"],
        ["A++", "< 30", "< 0.15", "Nearly zero energy (nZEB)"],
        ["A+", "30–50", "0.15–0.20", "Passive house standard"],
        ["A", "50–75", "0.20–0.30", "Very efficient, minimal heating"],
        ["B", "75–100", "0.30–0.50", "Well insulated, modern build"],
        ["C", "100–150", "0.50–0.80", "Adequate insulation, some upgrades"],
        ["D", "150–200", "0.80–1.20", "Average older building, needs work"],
        ["E", "200–250", "1.20–1.80", "Poor insulation, high costs"],
        ["F", "250–300", "1.80–2.50", "Very poor, urgent renovation"],
        ["G", "> 300", "> 2.50", "Worst performing, energy sieve"],
    ]
    e.append(Paragraph("Table 3.1: Energy Labels and Performance Ranges", styles["Section"]))
    e.append(make_table(data, col_widths=[65, 80, 100, 150]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 4: Thermal Bridging", styles["Chapter"]))
    e.append(Paragraph(
        "Thermal bridges occur where insulation is penetrated by a material with higher thermal "
        "conductivity — typically at junctions between walls and floors, around window frames, "
        "and at balcony connections. Thermal bridges can account for 10–30% of total heat loss. "
        "The linear thermal transmittance (ψ, psi value) quantifies this effect in W/mK.", styles["Body"]))

    e.append(Paragraph("Chapter 5: Retrofit Strategies", styles["Chapter"]))
    e.append(Paragraph(
        "External wall insulation (EWI) adds 50–200mm of insulation to the exterior face of walls. "
        "Internal wall insulation (IWI) adds insulation inside but reduces floor area. "
        "Cavity wall insulation injects material into the existing cavity. Each strategy has trade-offs "
        "in cost, performance, and impact on the building's appearance.", styles["Body"]))

    data = [
        ["Retrofit Measure", "Cost (€/m²)", "U-Value Reduction", "Payback (years)"],
        ["Cavity Wall Insulation", "15–25", "1.60 → 0.30", "3–5"],
        ["External Wall Insulation", "80–150", "2.10 → 0.25", "12–18"],
        ["Internal Wall Insulation", "40–70", "2.10 → 0.35", "8–12"],
        ["Loft Insulation (300mm)", "8–15", "2.30 → 0.14", "2–3"],
        ["Floor Insulation", "30–50", "0.70 → 0.22", "8–12"],
        ["Double → Triple Glazing", "350–600/unit", "2.80 → 0.80", "15–25"],
    ]
    e.append(Paragraph("Table 5.1: Retrofit Cost-Effectiveness", styles["Section"]))
    e.append(make_table(data, col_widths=[110, 75, 95, 85]))

    build_pdf("Sustainable-Home-Refurbishment.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 4: Green Building Illustrated
# ════════════════════════════════════════════════════════════
def book_04_architecture():
    e = []
    e.append(Paragraph("Green Building Illustrated", styles["BookTitle"]))
    e.append(Paragraph("A Guide to Understanding and Applying Green Building Design", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Passive Design Principles", styles["Chapter"]))
    e.append(Paragraph(
        "Passive design minimises energy consumption by using the building's form, orientation, and "
        "materials to manage heat, light, and ventilation. Key strategies include: south-facing glazing "
        "(northern hemisphere) for solar gain, thermal mass for heat storage, cross-ventilation for "
        "natural cooling, and daylighting design to reduce artificial lighting loads.", styles["Body"]))
    e.append(Paragraph(
        "Recommended window-to-wall ratios: South facade 40–60%, East/West 15–25%, North 10–15%. "
        "Roof overhangs should be designed to block high summer sun while admitting low winter sun.", styles["Body"]))

    e.append(Paragraph("Chapter 2: Solar Energy Integration", styles["Chapter"]))
    e.append(Paragraph(
        "Solar panels (photovoltaic and thermal) should be oriented within ±15° of true south at "
        "an inclination of 30–45° for optimal annual energy yield. A typical residential PV system "
        "(4–6 kWp) generates 3,500–5,500 kWh/year depending on location and can reduce energy "
        "costs by 40–60%.", styles["Body"]))

    data = [
        ["PV System Size", "Annual Yield", "CO₂ Saved/yr", "Cost", "Payback"],
        ["3 kWp", "2,700 kWh", "1,200 kg", "€4,500", "7–9 yr"],
        ["5 kWp", "4,500 kWh", "2,000 kg", "€7,000", "6–8 yr"],
        ["8 kWp", "7,200 kWh", "3,200 kg", "€10,500", "6–7 yr"],
        ["10 kWp", "9,000 kWh", "4,000 kg", "€12,500", "5–7 yr"],
    ]
    e.append(Paragraph("Table 2.1: Residential Solar PV Performance", styles["Section"]))
    e.append(make_table(data, col_widths=[80, 80, 80, 65, 65]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 3: LEED and BREEAM Certification", styles["Chapter"]))
    e.append(Paragraph(
        "LEED (Leadership in Energy and Environmental Design) awards credits across categories: "
        "Sustainable Sites, Water Efficiency, Energy & Atmosphere, Materials & Resources, Indoor "
        "Environmental Quality, and Innovation. Certification levels: Certified (40–49 pts), "
        "Silver (50–59), Gold (60–79), Platinum (80+).", styles["Body"]))
    e.append(Paragraph(
        "BREEAM (Building Research Establishment Environmental Assessment Method) is the world's "
        "oldest green building rating system. It scores buildings across Management, Health & Wellbeing, "
        "Energy, Transport, Water, Materials, Waste, Land Use, Pollution, and Innovation. "
        "Ratings: Pass, Good, Very Good, Excellent, Outstanding.", styles["Body"]))

    e.append(Paragraph("Chapter 4: HVAC Systems", styles["Chapter"]))
    e.append(Paragraph(
        "Heating, ventilation, and air conditioning systems account for 40–60% of building energy use. "
        "High-efficiency options include heat pumps (COP 3.5–5.0), mechanical ventilation with heat "
        "recovery (MVHR, 85–95% efficiency), and radiant floor/ceiling heating. Ground-source heat pumps "
        "achieve COP of 4.0–5.0 vs. 2.5–3.5 for air-source units.", styles["Body"]))

    e.append(Paragraph("Chapter 5: Building Envelope Performance", styles["Chapter"]))
    e.append(Paragraph(
        "The building envelope separates conditioned and unconditioned spaces. Performance depends on "
        "the thermal resistance of walls, roof, floor, and glazing; air tightness measured in air changes "
        "per hour at 50 Pa (ACH50); and control of thermal bridges. A well-performing envelope achieves "
        "ACH50 < 3.0 and overall U-value below 0.30 W/m²K.", styles["Body"]))

    build_pdf("Green-Building-Illustrated.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 5: Sustainable Construction
# ════════════════════════════════════════════════════════════
def book_05_materials():
    e = []
    e.append(Paragraph("Sustainable Construction — Materials and Practice", styles["BookTitle"]))
    e.append(Paragraph("Life Cycle Analysis and Environmental Impact of Building Materials", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Life Cycle Assessment (LCA)", styles["Chapter"]))
    e.append(Paragraph(
        "Life Cycle Assessment evaluates the environmental impact of a material from 'cradle to grave': "
        "raw material extraction, manufacturing, transport, installation, use phase, and end-of-life "
        "disposal or recycling. Key metrics include embodied energy (MJ/kg), embodied carbon "
        "(kgCO₂eq/kg), and Global Warming Potential (GWP).", styles["Body"]))

    data = [
        ["Material", "Embodied Energy (MJ/kg)", "Embodied Carbon (kgCO₂/kg)", "Recyclable"],
        ["Concrete (C30)", "1.0", "0.13", "Partially"],
        ["Steel (structural)", "20.1", "1.37", "Yes (98%)"],
        ["Timber (softwood)", "8.5", "0.46 (biogenic)", "Yes"],
        ["Brick (fired clay)", "3.0", "0.22", "Partially"],
        ["Aluminium", "155", "8.24", "Yes (95%)"],
        ["Glass (float)", "15.0", "0.86", "Yes (80%)"],
        ["EPS Insulation", "88.6", "3.29", "Limited"],
        ["Rock Wool", "16.8", "1.05", "Yes"],
        ["Cellulose Insulation", "3.3", "0.16", "Yes (98%)"],
    ]
    e.append(Paragraph("Table 1.1: Embodied Energy and Carbon of Building Materials", styles["Section"]))
    e.append(make_table(data, col_widths=[110, 100, 115, 65]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 2: Insulation Material Comparison", styles["Chapter"]))
    e.append(Paragraph(
        "Choosing insulation involves balancing thermal conductivity (λ), fire resistance, moisture "
        "permeability, environmental impact, cost, and available thickness. High-performance materials "
        "like aerogel (λ = 0.015 W/mK) enable thinner profiles but at higher cost. Traditional options "
        "like rock wool (λ = 0.038 W/mK) offer good fire resistance at lower cost.", styles["Body"]))

    data = [
        ["Material", "λ (W/mK)", "Fire Class", "Moisture", "Cost (€/m²)", "CO₂ Impact"],
        ["Rock Wool", "0.038", "A1 (non-comb.)", "Breathable", "15–25", "Medium"],
        ["Glass Wool", "0.040", "A1", "Breathable", "12–20", "Medium"],
        ["EPS", "0.035", "E (flammable)", "Low perm.", "10–18", "High"],
        ["XPS", "0.030", "E", "Very low", "18–30", "High"],
        ["PUR/PIR", "0.025", "B-C", "Low", "25–40", "High"],
        ["Cellulose", "0.040", "B-C", "High perm.", "15–22", "Very Low"],
        ["Aerogel", "0.015", "A2-B", "Breathable", "120–200", "Medium"],
        ["VIP", "0.007", "A1", "Sealed", "200–400", "Medium-High"],
    ]
    e.append(Paragraph("Table 2.1: Insulation Material Comparison Matrix", styles["Section"]))
    e.append(make_table(data, col_widths=[65, 60, 75, 60, 70, 65]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 3: Carbon Footprint of Buildings", styles["Chapter"]))
    e.append(Paragraph(
        "Buildings account for approximately 39% of global CO₂ emissions: 28% from operational "
        "energy (heating, cooling, lighting) and 11% from embodied carbon in materials and construction. "
        "A typical European residential building emits 1,500–4,000 kgCO₂/year from operations. "
        "Renovating to energy label A can reduce operational emissions by 60–80%.", styles["Body"]))

    build_pdf("Sustainable-Construction.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 6: The Book on Flipping Houses (J. Scott)
# ════════════════════════════════════════════════════════════
def book_06_costs():
    e = []
    e.append(Paragraph("The Book on Flipping Houses — J. Scott", styles["BookTitle"]))
    e.append(Paragraph("Renovation Cost Estimation and Project Management", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Estimating Rehab Costs", styles["Chapter"]))
    e.append(Paragraph(
        "Accurate renovation cost estimation is the foundation of any successful property investment. "
        "The scope of work should be broken down into individual line items grouped by trade: "
        "demolition, structural, plumbing, electrical, HVAC, insulation, drywall, flooring, painting, "
        "fixtures, and exterior improvements. Always add a 10–15% contingency reserve.", styles["Body"]))

    data = [
        ["Component", "Cost per sq ft ($)", "Cost per m² (€)", "Typical Scope"],
        ["Full Kitchen Remodel", "30–75", "280–700", "Cabinets, counters, appliances"],
        ["Bathroom Remodel", "35–80", "325–750", "Fixtures, tile, vanity, plumbing"],
        ["Roof Replacement", "4–10", "40–95", "Tear off, underlayment, shingles"],
        ["Window Replacement", "—", "350–600/unit", "Double/triple glazing upgrade"],
        ["Exterior Insulation", "—", "80–150/m²", "EWI system + render"],
        ["Interior Insulation", "—", "40–70/m²", "IWI battens + board + finish"],
        ["HVAC Replacement", "8–15", "75–140", "Heat pump or furnace + ducts"],
        ["Electrical Update", "3–7", "28–65", "Panel, wiring, outlets"],
        ["Plumbing", "3–8", "28–75", "Supply lines, drain, fixtures"],
        ["Flooring", "3–12", "28–110", "Hardwood, tile, or LVP"],
        ["Painting (int+ext)", "2–5", "19–47", "Prep, prime, 2 coats"],
    ]
    e.append(Paragraph("Table 1.1: Renovation Cost Benchmarks", styles["Section"]))
    e.append(make_table(data, col_widths=[95, 80, 80, 140]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 2: The 70% Rule and ARV", styles["Chapter"]))
    e.append(Paragraph(
        "The 70% rule states that an investor should pay no more than 70% of the After-Repair Value "
        "(ARV) minus repair costs. Example: ARV = $300,000, repairs = $50,000 → max offer = "
        "($300,000 × 0.70) - $50,000 = $160,000. This builds in profit margin and holding costs.", styles["Body"]))

    e.append(Paragraph("Chapter 3: Contractor Management", styles["Chapter"]))
    e.append(Paragraph(
        "Always get at least three bids for major work. A detailed scope of work (SOW) prevents cost "
        "overruns and misunderstandings. Payment should be tied to milestones: 10% at start, 40% at "
        "rough-in, 40% at substantial completion, 10% at final inspection/punchlist.", styles["Body"]))

    e.append(Paragraph("Chapter 4: Energy Retrofit ROI", styles["Chapter"]))
    e.append(Paragraph(
        "Energy improvements often have the highest ROI in renovation because they reduce operating "
        "costs and increase property value simultaneously. Insulation upgrades typically return "
        "€2.50–4.00 for every €1 invested over 15 years, factoring in energy savings and value increase.", styles["Body"]))

    data = [
        ["Retrofit", "Cost (€)", "Annual Savings (€)", "Value Increase (€)", "ROI (15yr)"],
        ["Wall Insulation", "8,000", "600", "12,000", "275%"],
        ["Roof Insulation", "3,000", "400", "5,000", "300%"],
        ["Triple Glazing", "12,000", "350", "8,000", "110%"],
        ["Heat Pump", "10,000", "800", "15,000", "330%"],
        ["Solar PV (5kWp)", "7,000", "700", "10,000", "293%"],
    ]
    e.append(Paragraph("Table 4.1: Energy Retrofit Return on Investment", styles["Section"]))
    e.append(make_table(data, col_widths=[80, 60, 85, 85, 65]))

    build_pdf("Book-on-Flipping-Houses-J-Scott.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 7: What Every RE Investor (Cash Flow)
# ════════════════════════════════════════════════════════════
def book_07_finance():
    e = []
    e.append(Paragraph("What Every Real Estate Investor Needs to Know About Cash Flow", styles["BookTitle"]))
    e.append(Paragraph("Financial Analysis and Investment Modeling", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Capitalization Rate (Cap Rate)", styles["Chapter"]))
    e.append(Paragraph(
        "The capitalization rate is the ratio of Net Operating Income (NOI) to property value: "
        "Cap Rate = NOI / Value. It represents the expected return on a property purchased with all "
        "cash. Lower cap rates indicate lower risk and higher values. Typical residential cap rates "
        "range from 4–8% depending on market and property class.", styles["Body"]))

    e.append(Paragraph("Chapter 2: Net Operating Income (NOI)", styles["Chapter"]))
    e.append(Paragraph(
        "NOI = Effective Gross Income - Operating Expenses. Operating expenses include property taxes, "
        "insurance, maintenance, management fees, and utilities (if paid by owner). NOI excludes "
        "mortgage payments and income tax. Annual energy costs directly reduce NOI, so energy "
        "efficiency improvements directly increase property value through the income approach.", styles["Body"]))

    e.append(Paragraph("Chapter 3: Discounted Cash Flow (DCF)", styles["Chapter"]))
    e.append(Paragraph(
        "DCF analysis projects cash flows over a holding period (typically 5–10 years) and discounts "
        "them to present value using a discount rate. NPV = Σ(CF_t / (1+r)^t) + Terminal Value / (1+r)^n. "
        "The Internal Rate of Return (IRR) is the discount rate that makes NPV = 0.", styles["Body"]))

    data = [
        ["Year", "NOI (€)", "Energy Savings (€)", "Total CF (€)", "PV @ 8%"],
        ["1", "24,000", "1,200", "25,200", "23,333"],
        ["2", "24,720", "1,260", "25,980", "22,261"],
        ["3", "25,462", "1,323", "26,785", "21,260"],
        ["4", "26,226", "1,389", "27,615", "20,298"],
        ["5", "27,013", "1,459", "28,472", "19,375"],
        ["Terminal Value", "—", "—", "356,650", "242,645"],
        ["Total", "—", "—", "—", "349,172"],
    ]
    e.append(Paragraph("Table 3.1: DCF Analysis with Energy Savings", styles["Section"]))
    e.append(make_table(data, col_widths=[80, 70, 85, 70, 70]))
    e.append(Spacer(1, 10))

    e.append(Paragraph("Chapter 4: Cash-on-Cash Return", styles["Chapter"]))
    e.append(Paragraph(
        "Cash-on-Cash Return measures the pre-tax cash flow relative to the total cash invested: "
        "CoC = Annual Pre-Tax Cash Flow / Total Cash Invested. A property generating €4,800/yr "
        "pre-tax cash flow on a €60,000 down payment yields 8% cash-on-cash return.", styles["Body"]))

    e.append(Paragraph("Chapter 5: Energy Value via Income Approach", styles["Chapter"]))
    e.append(Paragraph(
        "Energy improvements increase property value through the income approach: "
        "Value Increase = Annual Energy Savings / Cap Rate. Example: €1,200/yr energy savings "
        "at a 6% cap rate adds €20,000 to property value. This is the 'green premium' quantified "
        "using standard financial methodology.", styles["Body"]))

    data = [
        ["Annual Energy Savings", "Cap Rate 5%", "Cap Rate 6%", "Cap Rate 7%", "Cap Rate 8%"],
        ["€500", "€10,000", "€8,333", "€7,143", "€6,250"],
        ["€1,000", "€20,000", "€16,667", "€14,286", "€12,500"],
        ["€1,500", "€30,000", "€25,000", "€21,429", "€18,750"],
        ["€2,000", "€40,000", "€33,333", "€28,571", "€25,000"],
        ["€3,000", "€60,000", "€50,000", "€42,857", "€37,500"],
    ]
    e.append(Paragraph("Table 5.1: Value Increase from Energy Savings (Income Approach)", styles["Section"]))
    e.append(make_table(data, col_widths=[90, 70, 70, 70, 70]))

    build_pdf("What-Every-RE-Investor-Cash-Flow.pdf", e)


# ════════════════════════════════════════════════════════════
# Book 8: REALES — Real Estate Fundamentals & Glossary
# ════════════════════════════════════════════════════════════
def book_08_glossary():
    e = []
    e.append(Paragraph("REALES — Real Estate Fundamentals", styles["BookTitle"]))
    e.append(Paragraph("A Comprehensive Glossary and Reference Guide", styles["Body"]))
    e.append(Spacer(1, 20))

    e.append(Paragraph("Chapter 1: Real Estate Terminology", styles["Chapter"]))
    terms = [
        ("Appraisal", "A professional opinion of value, typically performed by a licensed or certified appraiser following recognized standards (IVS, USPAP)."),
        ("Market Value", "The most probable price a property should bring in a competitive and open market under all conditions requisite to a fair sale."),
        ("Easement", "A non-possessory right to use another person's land for a specific purpose (e.g., utility right-of-way, shared driveway)."),
        ("Zoning", "Government regulations controlling land use, building density, height, setbacks, and permitted activities in defined geographic areas."),
        ("Lien", "A legal claim against property as security for a debt. The most common lien is a mortgage. Tax liens take priority over other liens."),
        ("Title", "Legal evidence of ownership. A clear (or 'clean') title is free of liens, encumbrances, or legal questions as to the ownership."),
        ("Deed", "A legal document that transfers ownership of real property from one party to another. Types: General Warranty, Special Warranty, Quitclaim."),
        ("Mortgage", "A loan instrument secured by real property. The borrower (mortgagor) pledges the property to the lender (mortgagee)."),
        ("Encumbrance", "Any claim, lien, charge, or liability attached to property. Includes mortgages, easements, restrictive covenants, and unpaid taxes."),
        ("Depreciation", "Loss in property value from any cause. Physical (wear/tear), functional (obsolescence), external (economic/environmental)."),
        ("Cap Rate", "Capitalization Rate = NOI / Property Value. Used to estimate return on real estate investments. Lower cap rate = higher value."),
        ("NOI", "Net Operating Income = Effective Gross Income - Operating Expenses. Excludes debt service and income tax."),
        ("GRM", "Gross Rent Multiplier = Sale Price / Gross Annual Rent. A quick screening tool for investment properties."),
        ("U-Value", "Thermal transmittance coefficient measured in W/m²K. Indicates the rate of heat transfer through a building element. Lower = better insulation."),
        ("EPC", "Energy Performance Certificate. Rates a building's energy efficiency from A (best) to G (worst). Required for sale/lease in the EU."),
        ("Payback Period", "The time required for an investment to generate enough savings or income to recover its initial cost."),
        ("ROI", "Return on Investment = (Gain from Investment - Cost of Investment) / Cost of Investment × 100%."),
        ("DCF", "Discounted Cash Flow analysis. Projects future income and discounts it to present value using a chosen discount rate."),
        ("IRR", "Internal Rate of Return. The discount rate that makes the net present value (NPV) of all cash flows equal to zero."),
        ("Green Premium", "The additional value (sale price or rent) that energy-efficient or sustainably designed buildings command over conventional equivalents."),
    ]
    for term, definition in terms:
        e.append(Paragraph(f"<b>{term}:</b> {definition}", styles["Body"]))

    e.append(Paragraph("Chapter 2: Property Types", styles["Chapter"]))
    e.append(Paragraph(
        "Real estate is broadly categorised as: <b>Residential</b> (single-family, multi-family, "
        "condo, apartment), <b>Commercial</b> (office, retail, hospitality), <b>Industrial</b> "
        "(warehouse, manufacturing, flex space), and <b>Special Purpose</b> (schools, hospitals, "
        "religious facilities). Mixed-use properties combine two or more categories.", styles["Body"]))

    build_pdf("REALES-Fundamentals.pdf", e)


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"📚 Generating knowledge base PDFs → {OUTPUT_DIR}\n")
    book_01_ivs()
    book_02_appraisal()
    book_03_thermal()
    book_04_architecture()
    book_05_materials()
    book_06_costs()
    book_07_finance()
    book_08_glossary()
    print(f"\n✅ All 8 books generated in {OUTPUT_DIR}")
