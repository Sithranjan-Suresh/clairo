import { Badge, ConfidenceMeter } from "../ui";
import ClaimReviewPanel from "../saas/ClaimReviewPanel";
import {
  formatLabel,
  formatCurrency,
  formatCptCodes,
  displayValue,
  DOCUMENTATION_ITEMS,
  deriveDocumentationStrength,
} from "./claimIntakeUtils";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "extracted", label: "Extracted Data" },
  { id: "documentation", label: "Documentation" },
];

function FieldCard({ label, value }) {
  return (
    <div className="claim-field-card">
      <span className="claim-field-card__label">{label}</span>
      <div className="claim-field-card__value">{value}</div>
    </div>
  );
}

function SectionBlock({ title, children }) {
  return (
    <div className="claim-ws-section">
      <h3 className="claim-ws-section__title">{title}</h3>
      <div className="claim-ws-section__body">{children}</div>
    </div>
  );
}

function OverviewTab({ uploadResult }) {
  const claim = uploadResult.structured_claim ?? {};
  const policyCount = uploadResult.policy_matches_count ?? 0;
  const policyRetrieved = uploadResult.policy_retrieved || policyCount > 0;

  return (
    <div className="claim-ws-overview">
      <div className="claim-ws-overview__col">
        <SectionBlock title="Claim Information">
          <div className="claim-ws-fields">
            <FieldCard label="Payer" value={displayValue(claim.payer)} />
            <FieldCard label="Patient ID" value={displayValue(claim.patient_id)} />
            <FieldCard label="CPT Code" value={formatCptCodes(claim.cpt_codes)} />
            <FieldCard label="Service Date" value={displayValue(claim.service_date)} />
          </div>
        </SectionBlock>

        <SectionBlock title="Financial Summary">
          <div className="claim-ws-fields">
            <FieldCard label="Billed Amount" value={formatCurrency(claim.billed_amount)} />
            <FieldCard label="Denied Amount" value={formatCurrency(claim.denied_amount)} />
            <FieldCard
              label="Estimated Recoverable"
              value={formatCurrency(claim.denied_amount ?? claim.billed_amount)}
            />
          </div>
        </SectionBlock>
      </div>

      <div className="claim-ws-overview__col">
        <SectionBlock title="Denial Summary">
          <div className="claim-ws-fields">
            <FieldCard label="Category" value={formatLabel(uploadResult.classification)} />
            <FieldCard
              label="Risk Level"
              value={<Badge level={uploadResult.risk_level} />}
            />
            <FieldCard
              label="Risk Score"
              value={
                uploadResult.risk_score != null ? (
                  <ConfidenceMeter score={uploadResult.risk_score} />
                ) : (
                  "Not available"
                )
              }
            />
            <FieldCard
              label="Denial Reason"
              value={displayValue(claim.denial_reason)}
            />
          </div>
        </SectionBlock>

        <SectionBlock title="Current AI Assessment">
          <p className="claim-ws-assessment">
            {policyRetrieved
              ? `${policyCount} policy source${policyCount !== 1 ? "s" : ""} retrieved. Review documentation before generating appeal.`
              : "Policy evidence not yet retrieved. Appeal generation pending until documentation and policy evidence are ready."}
          </p>
        </SectionBlock>
      </div>
    </div>
  );
}

function ExtractedDataTab({
  uploadResult,
  onUpdateClaim,
  isEditingExtractedFields,
  setIsEditingExtractedFields,
}) {
  const claim = uploadResult.structured_claim ?? {};

  const groups = [
    {
      title: "Document Details",
      fields: [{ label: "File Name", value: displayValue(uploadResult.filename) }],
    },
    {
      title: "Patient & Claim",
      fields: [
        { label: "Payer", value: displayValue(claim.payer) },
        { label: "Patient ID", value: displayValue(claim.patient_id) },
        { label: "CPT Code", value: formatCptCodes(claim.cpt_codes) },
        { label: "Service Date", value: displayValue(claim.service_date) },
      ],
    },
    {
      title: "Denial Details",
      fields: [
        { label: "Denial Reason", value: displayValue(claim.denial_reason) },
        { label: "Denial Category", value: formatLabel(uploadResult.classification) },
        { label: "Risk Level", value: formatLabel(uploadResult.risk_level) },
        {
          label: "Risk Score",
          value:
            uploadResult.risk_score != null
              ? `${Math.round(uploadResult.risk_score)}%`
              : "Not available",
        },
      ],
    },
    {
      title: "Financial Details",
      fields: [
        { label: "Billed Amount", value: formatCurrency(claim.billed_amount) },
        { label: "Denied Amount", value: formatCurrency(claim.denied_amount) },
      ],
    },
    {
      title: "Classification",
      fields: [
        { label: "Category", value: formatLabel(uploadResult.classification) },
        {
          label: "Risk assessment",
          value: uploadResult.risk_score != null ? (
            <ConfidenceMeter score={uploadResult.risk_score} />
          ) : (
            "Not available"
          ),
        },
        {
          label: "Explanation",
          value: `Classified as ${formatLabel(uploadResult.classification)} with ${formatLabel(uploadResult.risk_level)} denial risk.`,
        },
      ],
    },
  ];

  return (
    <div className="claim-ws-extracted">
      <div className="claim-ws-extracted__toolbar">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setIsEditingExtractedFields(!isEditingExtractedFields)}
        >
          {isEditingExtractedFields ? "Hide Editor" : "Edit Extracted Fields"}
        </button>
      </div>

      {isEditingExtractedFields && (
        <ClaimReviewPanel
          uploadResult={uploadResult}
          onUpdateClaim={(data) => {
            onUpdateClaim?.(data);
          }}
        />
      )}

      <div className="claim-ws-extracted__groups">
        {groups.map((group) => (
          <div key={group.title} className="claim-ws-group glass-panel">
            <h4 className="claim-ws-group__title">{group.title}</h4>
            <div className="claim-ws-group__fields">
              {group.fields.map((field) => (
                <FieldCard
                  key={field.label}
                  label={field.label}
                  value={field.value}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DocumentationTab({ uploadResult }) {
  const strength = deriveDocumentationStrength(uploadResult);

  return (
    <div className="claim-ws-docs">
      <div className="claim-ws-docs__strength glass-panel">
        <span className="claim-ws-docs__strength-label">Documentation Strength</span>
        <span className="claim-ws-docs__strength-value">{strength.level}</span>
        <span className="claim-ws-docs__strength-note">{strength.note}</span>
      </div>

      <h4 className="claim-ws-docs__heading">Required Documentation</h4>
      <ul className="claim-doc-checklist">
        {DOCUMENTATION_ITEMS.map((item) => (
          <li key={item.id} className="claim-doc-checklist__item">
            <span className="claim-doc-checklist__label">{item.label}</span>
            <span className={`claim-doc-checklist__status claim-doc-checklist__status--${item.defaultStatus.toLowerCase().replace(/\s+/g, "-")}`}>
              {item.defaultStatus}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ClaimWorkspace({
  uploadResult,
  onUpdateClaim,
  activeWorkspaceTab,
  setActiveWorkspaceTab,
  isEditingExtractedFields,
  setIsEditingExtractedFields,
}) {
  if (!uploadResult) return null;

  return (
    <section className="claim-workspace glass-panel" aria-label="Claim workspace">
      <div className="claim-workspace__tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === tab.id}
            className={`claim-workspace__tab ${activeWorkspaceTab === tab.id ? "claim-workspace__tab--active" : ""}`}
            onClick={() => setActiveWorkspaceTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="claim-workspace__panel" role="tabpanel">
        {activeWorkspaceTab === "overview" && (
          <OverviewTab uploadResult={uploadResult} />
        )}
        {activeWorkspaceTab === "extracted" && (
          <ExtractedDataTab
            uploadResult={uploadResult}
            onUpdateClaim={onUpdateClaim}
            isEditingExtractedFields={isEditingExtractedFields}
            setIsEditingExtractedFields={setIsEditingExtractedFields}
          />
        )}
        {activeWorkspaceTab === "documentation" && (
          <DocumentationTab uploadResult={uploadResult} />
        )}
      </div>
    </section>
  );
}
