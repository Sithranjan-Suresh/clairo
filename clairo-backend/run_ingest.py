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

print("Ingestion complete")