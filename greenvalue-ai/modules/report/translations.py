"""
GreenValue AI — Report Translations (Phase 2B.4)

Provides EN / TR / DE translations for all body text, labels, table headers,
and narrative templates used in IVS-2025 report sections.

Section TITLES are already translated in IVSTemplate.SECTION_TITLES.
This module translates everything INSIDE the sections: field labels, table
column headers, glossary terms, narrative paragraphs, and disclaimers.

Usage:
    from modules.report.translations import t, t_glossary

    label = t("energy_label", lang="tr")          # → "Enerji Etiketi"
    glossary = t_glossary(lang="de")               # → [("Marktwert", "IVS 104: ..."), ...]
"""

from typing import Dict, List, Tuple

# ──────────────────────────────────────────────
# Field Labels & Short Strings
# ──────────────────────────────────────────────

LABELS: Dict[str, Dict[str, str]] = {
    # Cover
    "report_number": {"en": "Report Number", "tr": "Rapor Numarası", "de": "Berichtsnummer"},
    "report_date": {"en": "Report Date", "tr": "Rapor Tarihi", "de": "Berichtsdatum"},
    "valuation_date": {"en": "Valuation Date", "tr": "Değerleme Tarihi", "de": "Bewertungsstichtag"},
    "prepared_by": {"en": "Prepared by", "tr": "Hazırlayan", "de": "Erstellt von"},
    "client": {"en": "Client", "tr": "Müşteri", "de": "Auftraggeber"},
    "intended_use": {"en": "Intended Use", "tr": "Kullanım Amacı", "de": "Verwendungszweck"},

    # Scope of Work
    "purpose_of_valuation": {"en": "Purpose of Valuation", "tr": "Değerleme Amacı", "de": "Bewertungszweck"},
    "type_of_value": {"en": "Type of Value", "tr": "Değer Türü", "de": "Wertart"},
    "inspection_date": {"en": "Inspection Date", "tr": "İnceleme Tarihi", "de": "Besichtigungsdatum"},
    "inspection_type": {"en": "Inspection Type", "tr": "İnceleme Türü", "de": "Besichtigungsart"},
    "assumptions_ivs": {"en": "Assumptions (IVS 101.20)", "tr": "Varsayımlar (IVS 101.20)", "de": "Annahmen (IVS 101.20)"},
    "special_assumptions": {"en": "Special Assumptions", "tr": "Özel Varsayımlar", "de": "Besondere Annahmen"},
    "departures_from_ivs": {"en": "Departures from IVS", "tr": "IVS'den Sapmalar", "de": "Abweichungen von IVS"},

    # Property Description
    "property_id": {"en": "Property ID", "tr": "Gayrimenkul ID", "de": "Objekt-ID"},
    "address": {"en": "Address", "tr": "Adres", "de": "Adresse"},
    "property_type": {"en": "Property Type", "tr": "Gayrimenkul Türü", "de": "Objekttyp"},
    "year_built": {"en": "Year Built", "tr": "İnşaat Yılı", "de": "Baujahr"},
    "gross_floor_area": {"en": "Gross Floor Area", "tr": "Brüt Alan", "de": "Bruttogeschossfläche"},
    "number_of_floors": {"en": "Number of Floors", "tr": "Kat Sayısı", "de": "Anzahl Geschosse"},
    "zoning": {"en": "Zoning", "tr": "İmar Durumu", "de": "Baugebiet"},
    "detected_components": {
        "en": "Detected Building Components (AI Vision)",
        "tr": "Tespit Edilen Yapı Bileşenleri (AI Görüntü)",
        "de": "Erkannte Gebäudekomponenten (KI-Vision)",
    },

    # Table headers — Property Description
    "component": {"en": "Component", "tr": "Bileşen", "de": "Komponente"},
    "condition": {"en": "Condition", "tr": "Durum", "de": "Zustand"},
    "u_value_header": {"en": "U-Value (W/m²K)", "tr": "U-Değeri (W/m²K)", "de": "U-Wert (W/m²K)"},
    "area_header": {"en": "Area (m²)", "tr": "Alan (m²)", "de": "Fläche (m²)"},
    "ai_confidence": {"en": "AI Confidence", "tr": "AI Güven Skoru", "de": "KI-Konfidenz"},

    # Market Analysis
    "market_overview": {"en": "Market Overview", "tr": "Piyasa Genel Bakış", "de": "Marktüberblick"},
    "market_analysis_note": {
        "en": (
            "Market analysis is based on the RAG knowledge base and comparable "
            "property data. Key factors considered:"
        ),
        "tr": (
            "Piyasa analizi, RAG bilgi tabanı ve karşılaştırılabilir gayrimenkul "
            "verilerine dayanmaktadır. Değerlendirilen temel faktörler:"
        ),
        "de": (
            "Die Marktanalyse basiert auf der RAG-Wissensdatenbank und vergleichbaren "
            "Immobiliendaten. Berücksichtigte Schlüsselfaktoren:"
        ),
    },
    "market_factor_location": {
        "en": "Location and neighbourhood characteristics",
        "tr": "Konum ve çevre özellikleri",
        "de": "Lage- und Nachbarschaftsmerkmale",
    },
    "market_factor_supply": {
        "en": "Supply and demand dynamics",
        "tr": "Arz ve talep dinamikleri",
        "de": "Angebots- und Nachfragedynamik",
    },
    "market_factor_energy": {
        "en": "Energy performance premium/discount trends",
        "tr": "Enerji performansı prim/iskonto eğilimleri",
        "de": "Energieeffizienz-Prämien-/Abschlagstrends",
    },
    "market_factor_comparable": {
        "en": "Recent comparable transactions",
        "tr": "Güncel karşılaştırılabilir işlemler",
        "de": "Aktuelle vergleichbare Transaktionen",
    },
    "market_note_disclaimer": {
        "en": (
            "*Note: Market data is derived from the AI knowledge base. "
            "For institutional-grade valuations, supplement with local MLS/cadastral data.*"
        ),
        "tr": (
            "*Not: Piyasa verileri AI bilgi tabanından elde edilmiştir. "
            "Kurumsal düzeyde değerlemeler için yerel MLS/kadastro verileriyle destekleyin.*"
        ),
        "de": (
            "*Hinweis: Die Marktdaten stammen aus der KI-Wissensdatenbank. "
            "Für institutionelle Bewertungen ergänzen Sie diese mit lokalen MLS/Katasterdaten.*"
        ),
    },

    # Market Analysis — extended
    "market_area": {"en": "Market Area", "tr": "Piyasa Alanı", "de": "Marktgebiet"},
    "analysis_date": {"en": "Analysis Date", "tr": "Analiz Tarihi", "de": "Analysedatum"},
    "median_price_sqm": {"en": "Median Price (€/m²)", "tr": "Medyan Fiyat (€/m²)", "de": "Medianpreis (€/m²)"},
    "yoy_price_change": {"en": "Year-over-Year Price Change", "tr": "Yıllık Fiyat Değişimi", "de": "Jahrespreisänderung"},
    "days_on_market": {"en": "Avg. Days on Market", "tr": "Ort. Satış Süresi (gün)", "de": "Durchschn. Vermarktungsdauer"},
    "inventory_level": {"en": "Inventory Level", "tr": "Envanter Düzeyi", "de": "Bestandsniveau"},
    "energy_premium": {"en": "Energy Label Premium (A/B vs E/F/G)", "tr": "Enerji Etiketi Primi (A/B vs E/F/G)", "de": "Energielabel-Aufschlag (A/B vs E/F/G)"},
    "comparable_properties": {"en": "Comparable Properties", "tr": "Karşılaştırılabilir Gayrimenkuller", "de": "Vergleichsimmobilien"},
    "comp_address": {"en": "Address", "tr": "Adres", "de": "Adresse"},
    "comp_sale_date": {"en": "Sale Date", "tr": "Satış Tarihi", "de": "Verkaufsdatum"},
    "comp_sale_price": {"en": "Sale Price", "tr": "Satış Fiyatı", "de": "Verkaufspreis"},
    "comp_area_sqm": {"en": "Area (m²)", "tr": "Alan (m²)", "de": "Fläche (m²)"},
    "comp_price_sqm": {"en": "€/m²", "tr": "€/m²", "de": "€/m²"},
    "comp_energy_label": {"en": "EN Label", "tr": "EN Etiketi", "de": "EN Label"},
    "comp_adj_price": {"en": "Adj. Price", "tr": "Düz. Fiyat", "de": "Ber. Preis"},
    "comp_similarity": {"en": "Similarity", "tr": "Benzerlik", "de": "Ähnlichkeit"},
    "market_conditions_heading": {"en": "Market Conditions", "tr": "Piyasa Koşulları", "de": "Marktbedingungen"},
    "data_source_notes_heading": {"en": "Data Source Notes", "tr": "Veri Kaynağı Notları", "de": "Datenquellennotizen"},

    # Valuation Approaches
    "applicable": {"en": "Applicable", "tr": "Uygulanabilir", "de": "Anwendbar"},
    "yes": {"en": "Yes", "tr": "Evet", "de": "Ja"},
    "no": {"en": "No", "tr": "Hayır", "de": "Nein"},
    "indicated_value": {"en": "Indicated Value", "tr": "Belirlenen Değer", "de": "Ermittelter Wert"},
    "methodology": {"en": "Methodology", "tr": "Yöntem", "de": "Methodik"},
    "data_sources": {"en": "Data Sources", "tr": "Veri Kaynakları", "de": "Datenquellen"},
    "adjustments": {"en": "Adjustments", "tr": "Düzeltmeler", "de": "Anpassungen"},
    "weight_in_reconciliation": {"en": "Weight in Reconciliation", "tr": "Uzlaştırma Ağırlığı", "de": "Gewicht bei Abstimmung"},
    "book_reference": {"en": "Book Reference", "tr": "Kitap Referansı", "de": "Buchreferenz"},

    # Adjustment table headers
    "adj_type": {"en": "Type", "tr": "Tür", "de": "Art"},
    "adj_amount": {"en": "Amount", "tr": "Tutar", "de": "Betrag"},
    "adj_source": {"en": "Source", "tr": "Kaynak", "de": "Quelle"},

    # Energy Assessment
    "current_energy_performance": {"en": "Current Energy Performance", "tr": "Mevcut Enerji Performansı", "de": "Aktuelle Energieleistung"},
    "energy_label_current": {"en": "Current Energy Label", "tr": "Mevcut Enerji Etiketi", "de": "Aktuelles Energielabel"},
    "energy_label_projected": {"en": "Projected Label (Post-Upgrade)", "tr": "Öngörülen Etiket (Yükseltme Sonrası)", "de": "Prognostiziertes Label (nach Sanierung)"},
    "annual_heat_loss": {"en": "Annual Heat Loss", "tr": "Yıllık Isı Kaybı", "de": "Jährlicher Wärmeverlust"},
    "carbon_footprint": {"en": "Carbon Footprint", "tr": "Karbon Ayak İzi", "de": "CO₂-Fußabdruck"},
    "component_thermal": {"en": "Component Thermal Performance", "tr": "Bileşen Termal Performansı", "de": "Thermische Komponentenleistung"},

    # Energy table headers
    "current_u_value": {"en": "Current U-Value", "tr": "Mevcut U-Değeri", "de": "Aktueller U-Wert"},
    "target_u_value": {"en": "Target U-Value", "tr": "Hedef U-Değeri", "de": "Ziel-U-Wert"},

    # Renovation Impact
    "upgrade_summary": {"en": "Upgrade Summary", "tr": "Yükseltme Özeti", "de": "Sanierungsübersicht"},
    "total_estimated_cost": {"en": "Total Estimated Cost", "tr": "Toplam Tahmini Maliyet", "de": "Geschätzte Gesamtkosten"},
    "total_value_add": {"en": "Total Value Add", "tr": "Toplam Değer Artışı", "de": "Gesamtwertsteigerung"},
    "aggregate_roi": {"en": "Aggregate ROI", "tr": "Toplam Yatırım Getirisi", "de": "Gesamt-ROI"},
    "aggregate_payback": {"en": "Aggregate Payback", "tr": "Toplam Geri Ödeme", "de": "Gesamtamortisationsdauer"},
    "energy_label_impact": {"en": "Energy Label Impact", "tr": "Enerji Etiketi Etkisi", "de": "Auswirkung auf Energielabel"},
    "individual_upgrades": {"en": "Individual Upgrade Recommendations", "tr": "Bireysel Yükseltme Önerileri", "de": "Einzelne Sanierungsempfehlungen"},
    "no_upgrades": {"en": "No renovation upgrades recommended.", "tr": "Renovasyon yükseltmesi önerilmiyor.", "de": "Keine Sanierungsmaßnahmen empfohlen."},

    # Renovation table headers
    "description": {"en": "Description", "tr": "Açıklama", "de": "Beschreibung"},
    "cost": {"en": "Cost", "tr": "Maliyet", "de": "Kosten"},
    "value_add": {"en": "Value Add", "tr": "Değer Artışı", "de": "Wertsteigerung"},
    "roi": {"en": "ROI", "tr": "Yatırım Getirisi", "de": "Rentabilität"},
    "payback": {"en": "Payback", "tr": "Geri Ödeme", "de": "Amortisation"},
    "energy_saving": {"en": "Energy Saving", "tr": "Enerji Tasarrufu", "de": "Energieeinsparung"},
    "label_impact": {"en": "Label Impact", "tr": "Etiket Etkisi", "de": "Labelwirkung"},

    # Reconciliation
    "final_value_opinion": {"en": "Final Value Opinion", "tr": "Nihai Değer Görüşü", "de": "Endgültige Wertermittlung"},
    "reconciled_value": {"en": "Reconciled Market Value (IVS 104)", "tr": "Uzlaştırılmış Piyasa Değeri (IVS 104)", "de": "Abgestimmter Marktwert (IVS 104)"},
    "confidence_level": {"en": "Confidence Level", "tr": "Güven Düzeyi", "de": "Konfidenzniveau"},
    "approach": {"en": "Approach", "tr": "Yaklaşım", "de": "Verfahren"},
    "green_premium": {"en": "Green Premium", "tr": "Yeşil Prim", "de": "Grüne Prämie"},
    "green_premium_basis": {"en": "Green Premium Basis", "tr": "Yeşil Prim Temeli", "de": "Grundlage der Grünen Prämie"},
    "reconciliation_narrative": {"en": "Reconciliation Narrative", "tr": "Uzlaştırma Açıklaması", "de": "Abstimmungsbegründung"},

    # Approach names
    "cost_approach": {"en": "Cost Approach", "tr": "Maliyet Yaklaşımı", "de": "Sachwertverfahren"},
    "sales_comparison": {"en": "Sales Comparison", "tr": "Satış Karşılaştırması", "de": "Vergleichswertverfahren"},
    "income_approach": {"en": "Income Approach", "tr": "Gelir Yaklaşımı", "de": "Ertragswertverfahren"},

    # Assumptions
    "general_assumptions": {"en": "General Assumptions (IVS 101.20)", "tr": "Genel Varsayımlar (IVS 101.20)", "de": "Allgemeine Annahmen (IVS 101.20)"},
    "limiting_conditions": {"en": "Limiting Conditions", "tr": "Sınırlayıcı Koşullar", "de": "Einschränkende Bedingungen"},
    "limit_ai_disclaimer": {
        "en": "This valuation relies on AI-assisted building component detection and automated thermal performance analysis.",
        "tr": "Bu değerleme, AI destekli yapı bileşeni tespiti ve otomatik termal performans analizine dayanmaktadır.",
        "de": "Diese Bewertung stützt sich auf KI-gestützte Gebäudekomponentenerkennung und automatisierte Wärmeleistungsanalyse.",
    },
    "limit_no_interior": {
        "en": "The appraiser has not conducted a physical interior inspection.",
        "tr": "Değerleme uzmanı fiziksel iç mekan incelemesi yapmamıştır.",
        "de": "Der Gutachter hat keine physische Innenbesichtigung durchgeführt.",
    },
    "limit_rag_data": {
        "en": "Market data is sourced from the RAG knowledge base and may not reflect the most current local market conditions.",
        "tr": "Piyasa verileri RAG bilgi tabanından alınmıştır ve en güncel yerel piyasa koşullarını yansıtmayabilir.",
        "de": "Marktdaten stammen aus der RAG-Wissensdatenbank und spiegeln möglicherweise nicht die aktuellsten lokalen Marktbedingungen wider.",
    },
    "limit_cost_benchmarks": {
        "en": "Renovation cost estimates are based on published benchmarks and should be verified with local contractor quotations before execution.",
        "tr": "Renovasyon maliyet tahminleri yayınlanmış referans değerlere dayanmaktadır ve uygulama öncesinde yerel müteahhit teklifleriyle doğrulanmalıdır.",
        "de": "Sanierungskostenschätzungen basieren auf veröffentlichten Richtwerten und sollten vor Ausführung mit lokalen Handwerkerangeboten überprüft werden.",
    },
    "limit_green_premium": {
        "en": "The green premium estimate is based on energy label differential analysis and may vary by local market.",
        "tr": "Yeşil prim tahmini, enerji etiketi fark analizine dayanmaktadır ve yerel pazara göre değişebilir.",
        "de": "Die Schätzung der Grünen Prämie basiert auf der Energielabel-Differenzanalyse und kann je nach lokalem Markt variieren.",
    },

    # Appendices
    "yolo_results": {
        "en": "YOLO11 AI Detection Results",
        "tr": "YOLO11 AI Tespit Sonuçları",
        "de": "YOLO11-KI-Erkennungsergebnisse",
    },
    "yolo_description": {
        "en": "The following building components were detected via YOLO11 instance segmentation model:",
        "tr": "Aşağıdaki yapı bileşenleri YOLO11 örnek segmentasyon modeli ile tespit edilmiştir:",
        "de": "Die folgenden Gebäudekomponenten wurden mit dem YOLO11-Instanzsegmentierungsmodell erkannt:",
    },
    "no_detections": {"en": "No AI detections available.", "tr": "AI tespiti mevcut değil.", "de": "Keine KI-Erkennungen verfügbar."},
    "detailed_financials": {"en": "Detailed Financial Calculations", "tr": "Detaylı Finansal Hesaplamalar", "de": "Detaillierte Finanzberechnungen"},
    "no_financials": {"en": "No financial calculations available.", "tr": "Finansal hesaplama mevcut değil.", "de": "Keine Finanzberechnungen verfügbar."},
    "glossary_of_terms": {"en": "Glossary of Terms", "tr": "Terimler Sözlüğü", "de": "Glossar"},
    "data_sources_citations": {"en": "Data Sources & Book Citations", "tr": "Veri Kaynakları ve Kitap Referansları", "de": "Datenquellen und Buchzitate"},
    "additional_sources": {"en": "Additional Sources Cited", "tr": "Ek Kaynak Referansları", "de": "Weitere zitierte Quellen"},
    "total": {"en": "TOTAL", "tr": "TOPLAM", "de": "GESAMT"},
    "not_assessed": {"en": "Not assessed", "tr": "Değerlendirilmedi", "de": "Nicht bewertet"},
    "na": {"en": "N/A", "tr": "YOK", "de": "K.A."},
    "unknown": {"en": "Unknown", "tr": "Bilinmiyor", "de": "Unbekannt"},
    "none": {"en": "None", "tr": "Yok", "de": "Keine"},

    # Table headers for financials appendix
    "kwh_saved": {"en": "kWh Saved", "tr": "kWh Tasarruf", "de": "kWh eingespart"},
    "co2_reduced": {"en": "CO₂ Reduced", "tr": "CO₂ Azaltma", "de": "CO₂ reduziert"},

    # Table headers for sources
    "source_id": {"en": "ID", "tr": "ID", "de": "ID"},
    "author_publisher": {"en": "Author / Publisher", "tr": "Yazar / Yayıncı", "de": "Autor / Verlag"},
    "full_title": {"en": "Full Title", "tr": "Tam Başlık", "de": "Vollständiger Titel"},

    # Table header for glossary
    "term": {"en": "Term", "tr": "Terim", "de": "Begriff"},
    "definition": {"en": "Definition", "tr": "Tanım", "de": "Definition"},
}


def t(key: str, lang: str = "en") -> str:
    """Translate a label key to the target language."""
    entry = LABELS.get(key, {})
    return entry.get(lang, entry.get("en", key))


# ──────────────────────────────────────────────
# Glossary (fully translated)
# ──────────────────────────────────────────────

GLOSSARY: Dict[str, List[Tuple[str, str]]] = {
    "en": [
        ("Market Value", "IVS 104: The estimated amount for which an asset should exchange on the valuation date."),
        ("U-Value", "Thermal transmittance of a building element in W/m²K. Lower = better insulation."),
        ("Energy Label", "Rating from A (best) to G (worst) indicating building energy performance."),
        ("Cap Rate", "Capitalisation rate: Net Operating Income ÷ Property Value."),
        ("NOI", "Net Operating Income: Gross income less operating expenses."),
        ("ROI", "Return on Investment: (Gain - Cost) ÷ Cost × 100%."),
        ("NPV", "Net Present Value: Sum of discounted future cash flows minus initial investment."),
        ("IRR", "Internal Rate of Return: Discount rate at which NPV equals zero."),
        ("DCF", "Discounted Cash Flow: Valuation method using projected future cash flows."),
        ("Cost Approach", "IVS 105: Value based on replacement cost new less depreciation plus land value."),
        ("Sales Comparison", "IVS 105: Value derived from comparable property transactions with adjustments."),
        ("Income Approach", "IVS 105: Value derived from capitalisation of income the property can produce."),
        ("Green Premium", "Additional property value attributable to superior energy/sustainability performance."),
        ("Heat Loss", "Rate of thermal energy transfer from inside to outside through building fabric (kWh/year)."),
        ("EPC", "Energy Performance Certificate: Official document rating building energy efficiency."),
        ("YOLO", "You Only Look Once: Real-time object detection neural network used for building component identification."),
    ],
    "tr": [
        ("Piyasa Değeri", "IVS 104: Bir varlığın değerleme tarihinde el değiştirmesi gereken tahmini tutar."),
        ("U-Değeri", "Bir yapı elemanının termal geçirgenliği (W/m²K). Düşük = daha iyi yalıtım."),
        ("Enerji Etiketi", "Bina enerji performansını A (en iyi) ile G (en kötü) arasında gösteren derecelendirme."),
        ("Kapitalizasyon Oranı", "Net İşletme Geliri ÷ Gayrimenkul Değeri."),
        ("Net İşletme Geliri", "Brüt gelir eksi işletme giderleri."),
        ("Yatırım Getirisi (ROI)", "(Kazanç - Maliyet) ÷ Maliyet × %100."),
        ("Net Bugünkü Değer (NPV)", "İskonto edilmiş gelecekteki nakit akışları toplamı eksi başlangıç yatırımı."),
        ("İç Verim Oranı (IRR)", "NPV'nin sıfıra eşit olduğu iskonto oranı."),
        ("İndirgenmiş Nakit Akışı (DCF)", "Öngörülen gelecekteki nakit akışlarını kullanan değerleme yöntemi."),
        ("Maliyet Yaklaşımı", "IVS 105: Yeniden yapım maliyetinden amortisman düşülerek arsa değeri eklenen değer."),
        ("Satış Karşılaştırması", "IVS 105: Düzeltmelerle karşılaştırılabilir gayrimenkul işlemlerinden elde edilen değer."),
        ("Gelir Yaklaşımı", "IVS 105: Gayrimenkulün üretebileceği gelirin kapitalizasyonundan elde edilen değer."),
        ("Yeşil Prim", "Üstün enerji/sürdürülebilirlik performansına atfedilen ek gayrimenkul değeri."),
        ("Isı Kaybı", "Bina kabuğu aracılığıyla iç mekândan dış mekâna termal enerji transfer hızı (kWh/yıl)."),
        ("EPC", "Enerji Performans Sertifikası: Bina enerji verimliliğini derecelendiren resmi belge."),
        ("YOLO", "You Only Look Once: Yapı bileşeni tanımlama için kullanılan gerçek zamanlı nesne algılama sinir ağı."),
    ],
    "de": [
        ("Marktwert", "IVS 104: Der geschätzte Betrag, zu dem ein Vermögenswert am Bewertungsstichtag getauscht werden sollte."),
        ("U-Wert", "Wärmedurchgangskoeffizient eines Bauelements in W/m²K. Niedriger = bessere Dämmung."),
        ("Energielabel", "Bewertung von A (am besten) bis G (am schlechtesten) für die Energieeffizienz des Gebäudes."),
        ("Kapitalisierungszinssatz", "Nettobetriebseinkommen ÷ Immobilienwert."),
        ("Nettobetriebseinkommen", "Bruttoeinkommen abzüglich Betriebskosten."),
        ("Kapitalrendite (ROI)", "(Gewinn - Kosten) ÷ Kosten × 100%."),
        ("Kapitalwert (NPV)", "Summe der abgezinsten zukünftigen Cashflows minus Anfangsinvestition."),
        ("Interner Zinsfuß (IRR)", "Abzinsungssatz, bei dem der NPV gleich Null ist."),
        ("Discounted Cashflow (DCF)", "Bewertungsmethode unter Verwendung prognostizierter zukünftiger Cashflows."),
        ("Sachwertverfahren", "IVS 105: Wert basierend auf Herstellungskosten abzüglich Abschreibung plus Bodenwert."),
        ("Vergleichswertverfahren", "IVS 105: Wert abgeleitet aus vergleichbaren Immobilientransaktionen mit Anpassungen."),
        ("Ertragswertverfahren", "IVS 105: Wert abgeleitet aus der Kapitalisierung des Einkommens, das die Immobilie erzielen kann."),
        ("Grüne Prämie", "Zusätzlicher Immobilienwert, der auf überlegene Energie-/Nachhaltigkeitsleistung zurückzuführen ist."),
        ("Wärmeverlust", "Rate des Wärmetransfers von innen nach außen durch die Gebäudehülle (kWh/Jahr)."),
        ("EPC", "Energieausweis: Offizielles Dokument zur Bewertung der Energieeffizienz eines Gebäudes."),
        ("YOLO", "You Only Look Once: Echtzeit-Objekterkennungsnetzwerk zur Identifizierung von Gebäudekomponenten."),
    ],
}


def t_glossary(lang: str = "en") -> List[Tuple[str, str]]:
    """Return the glossary terms for the given language."""
    return GLOSSARY.get(lang, GLOSSARY["en"])
