import pytest
from app.responses.compliance_scorer import calculate_compliance_scores


class TestComplianceScorer:
    def test_all_compliant(self):
        requirements = [
            {"id": "1", "type": "functional", "is_mandatory": True},
            {"id": "2", "type": "functional", "is_mandatory": True},
        ]
        responses = [
            {"requirement_id": "1", "compliance_status": "fully_compliant"},
            {"requirement_id": "2", "compliance_status": "fully_compliant"},
        ]
        scores = calculate_compliance_scores(requirements, responses)
        assert scores["overall_score"] == 100.0
        assert scores["functional_score"] == 100.0

    def test_mixed_compliance(self):
        requirements = [
            {"id": "1", "type": "functional", "is_mandatory": True},
            {"id": "2", "type": "functional", "is_mandatory": True},
        ]
        responses = [
            {"requirement_id": "1", "compliance_status": "fully_compliant"},
            {"requirement_id": "2", "compliance_status": "partially_compliant"},
        ]
        scores = calculate_compliance_scores(requirements, responses)
        assert scores["overall_score"] == 75.0  # (1.0 + 0.5) / 2 * 100

    def test_empty_responses(self):
        requirements = [{"id": "1", "type": "functional", "is_mandatory": True}]
        scores = calculate_compliance_scores(requirements, [])
        assert scores["overall_score"] == 0

    def test_status_breakdown(self):
        requirements = [
            {"id": "1", "type": "functional", "is_mandatory": True},
            {"id": "2", "type": "non_functional", "is_mandatory": False},
            {"id": "3", "type": "functional", "is_mandatory": True},
        ]
        responses = [
            {"requirement_id": "1", "compliance_status": "fully_compliant"},
            {"requirement_id": "2", "compliance_status": "configurable"},
            {"requirement_id": "3", "compliance_status": "custom_dev"},
        ]
        scores = calculate_compliance_scores(requirements, responses)
        assert scores["status_breakdown"]["fully_compliant"] == 1
        assert scores["status_breakdown"]["configurable"] == 1
        assert scores["status_breakdown"]["custom_dev"] == 1
        assert scores["total_requirements"] == 3
        assert scores["total_responses"] == 3

    def test_multiple_types(self):
        requirements = [
            {"id": "1", "type": "functional", "is_mandatory": True},
            {"id": "2", "type": "non_functional", "is_mandatory": True},
        ]
        responses = [
            {"requirement_id": "1", "compliance_status": "fully_compliant"},
            {"requirement_id": "2", "compliance_status": "partially_compliant"},
        ]
        scores = calculate_compliance_scores(requirements, responses)
        assert scores["functional_score"] == 100.0
        assert scores["non_functional_score"] == 50.0
