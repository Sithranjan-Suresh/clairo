from unittest.mock import MagicMock, patch

from app.services.analytics_service import get_denials_by_cpt


@patch("app.services.analytics_service.SessionLocal")
def test_denials_by_cpt_counts_individual_codes(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    # Two claims share CPT 29881 but have different secondary codes —
    # each individual code should be counted separately, not per combination.
    mock_db.query.return_value.filter.return_value.all.return_value = [
        ("29881, 29880",),
        ("29881",),
        (None,),
    ]

    result = get_denials_by_cpt()
    result_map = {r["cpt_code"]: r["denial_count"] for r in result}

    assert result_map["29881"] == 2
    assert result_map["29880"] == 1
