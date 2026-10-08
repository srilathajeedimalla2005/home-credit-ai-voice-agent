from backend.state import QualificationState
from backend.business_rules import extract_facts, apply_facts, first_missing, all_eligibility_answered

def test_agricultural_disqualifies():
    s = QualificationState()
    result, _ = apply_facts(s, extract_facts("My property is agricultural land."))
    assert result == "DISQUALIFY"
    assert s.disqualified is True

def test_joint_is_allowed():
    s = QualificationState()
    result, _ = apply_facts(s, extract_facts("It is jointly owned with my wife."))
    assert result == "CONTINUE"
    assert s.ownership_status == "Joint"

def test_cash_income_disqualifies():
    s = QualificationState()
    result, _ = apply_facts(s, extract_facts("I am self-employed and my income is cash."))
    assert result == "DISQUALIFY"

def test_tenure_range():
    s = QualificationState()
    result, _ = apply_facts(s, extract_facts("I want a tenure of 2 years."))
    assert result == "DISQUALIFY"

def test_out_of_order_extraction():
    s = QualificationState()
    facts = extract_facts("It is a residential house, jointly owned with my wife, worth around 80 lakhs and I need 40 lakhs.")
    apply_facts(s, facts)
    assert s.property_type == "Residential"
    assert s.ownership_status == "Joint"
    assert s.loan_amount == 4_000_000
    assert s.market_value == 8_000_000

def test_all_items():
    s = QualificationState(
        property_type="Residential",
        ownership_status="Sole",
        documents_available=True,
        loan_amount=5_000_000,
        occupation="Salaried",
        income_mode="Bank",
        market_value="₹1 crore",
        tenure=10
    )
    assert all_eligibility_answered(s)

def test_market_value_is_not_treated_as_loan_amount():
    s = QualificationState()
    facts = extract_facts("My house is worth 1 crore and I want a loan of 50 lakhs.")
    apply_facts(s, facts)
    assert s.market_value == 10_000_000
    assert s.loan_amount == 5_000_000


def test_loan_amount_prefers_requested_amount_when_two_amounts_are_present():
    s = QualificationState()
    facts = extract_facts("The property is worth around 80 lakhs and I need 40 lakhs.")
    apply_facts(s, facts)
    assert s.loan_amount == 4_000_000
