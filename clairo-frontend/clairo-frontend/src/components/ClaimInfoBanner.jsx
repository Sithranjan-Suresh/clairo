export default function ClaimInfoBanner({ onGoToIntake }) {
  return (
    <div className="claim-info-banner" role="status">
      <span className="claim-info-banner__icon" aria-hidden="true">
        ○
      </span>
      <div className="claim-info-banner__text">
        <strong>No claim loaded</strong>
        <span>Upload a denial on Claim Intake to prefill fields, or enter details manually below.</span>
      </div>
      {onGoToIntake && (
        <button type="button" className="btn-copy claim-info-banner__link" onClick={onGoToIntake}>
          Claim Intake
        </button>
      )}
    </div>
  );
}
