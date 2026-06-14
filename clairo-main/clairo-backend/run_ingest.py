from app.rag.ingest import ingest_policy

# UHC
ingest_policy("UHC", "app/data/policies/uhc_knee_arthroscopy.pdf")

# BCBS TX
ingest_policy("BCBS_TX", "app/data/policies/bcbs_orthopedic_policy.pdf")

# AETNA
ingest_policy("AETNA", "app/data/policies/aetna_msk_policy.pdf")

# Community Health Plan of Washington (CHPW) - Knee Arthroscopy & Arthroplasty
ingest_policy("CHPW", "app/data/policies/Knee_Arthroscopy_and_Arthroplasty_Clinical_Coverage_Criteria_-_MM202.pdf")

# Centene Corporation / Health Net - Articular Cartilage Defect Repairs
ingest_policy("CENTENE", "app/data/policies/ArticularCartilageDefectRepairs.pdf")

# Arkansas Blue Cross Blue Shield - Meniscal Transplantation Policy
ingest_policy("ARKANSAS_BCBS", "app/data/policies/Coverage Policy Manual - Arkansas Blue Cross and Blue Shield.pdf")

# Excellus BlueCross BlueShield - Autologous Chondrocyte Implantation (ACI)
ingest_policy("EXCELLUS_BCBS", "app/data/policies/EXC-PRV-Autologous Chrondrocyte Implantation.pdf")

# Cigna / American Specialty Health (ASH) - Clinical Therapy Services 
ingest_policy("CIGNA", "app/data/policies/cpg272_electric_stim_clinic.pdf")

ingest_policy("MEDICARE", "app/data/policies/medicare_lcd_knee_arthroscopy.pdf")

ingest_policy("CIGNA", "app/data/policies/cigna_cardiac_imaging.pdf")

ingest_policy("AETNA", "app/data/policies/aetna_medical_necessity.pdf")

ingest_policy("Humana", "app/data/policies/Injections_for_Chronic_Pain_Conditionspdf.pdf")

ingest_policy("Cigna", "app/data/policies/Musculoskeletal_Imaging_Guidelines_v1.1_2025.pdf")

ingest_policy("eviCore", "app/data/policies/eviCore_Guidelines-MSK_Services_Procedures.pdf")

ingest_policy("Molina", "app/data/policies/prior_auth_pre-service_review_guide_eff_7_1_13.pdf")

ingest_policy("Molina", "app/data/policies/Medically_Necessary_R.pdf")

ingest_policy("Molina", "app/data/policies/MCP-700-Foot-Surgery-Bunionectomy.pdf")

ingest_policy("Kaiser Permanente", "app/data/policies/mri_cspine.pdf")

ingest_policy("Carelon", "app/data/policies/MSK-Spine-Surgery-redline-2024-10-20.pdf")

ingest_policy("Aetna", "app/data/policies/MSK_Imaging_Clinical_Guidelines_2025.pdf")

ingest_policy("Florida Medicaid", "app/data/policies/59G-4.085_EIS_Coverage_Policy_09282018.pdf")

ingest_policy("Kaiser Permanente", "app/data/policies/lumbar-spinal-fusion-policy-nw-en-forms.pdf")
print("Ingestion complete")