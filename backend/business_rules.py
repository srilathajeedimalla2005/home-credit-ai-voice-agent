import re
from typing import Any, Dict, Optional, Tuple

MAX_LOAN = 7_500_000
MIN_TENURE = 3
MAX_TENURE = 15

QUESTIONS = [
    ("property_type", "What type of property do you have: residential, commercial, or industrial?"),
    ("ownership_status", "Is the property solely owned by you, or is it jointly owned?"),
    ("documents_available", "Do you have the original property documents available for verification?"),
    ("loan_amount", "How much would you like to borrow?"),
    ("occupation_income", "Are you salaried or self-employed, and is your income received through your bank account or in cash?"),
    ("market_value", "Approximately what is the current market value of the property?"),
    ("tenure", "How many years would you like to take to repay the loan?"),
]


def first_missing(state) -> Optional[str]:
    answered = state.answered_items()
    for key, _ in QUESTIONS:
        if not answered[key]:
            return key
    return None


def _money_matches(text: str):
    """Return all money amounts in the text as (start, end, value)."""
    t = text.lower().replace("₹", "")
    patterns = [
        (r"([\d,]+(?:\.\d+)?)\s*(?:crore|crores|cr)\b", 10_000_000),
        (r"([\d,]+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs)\b", 100_000),
        (r"\b(\d{5,8})\b", 1),
    ]
    matches = []
    for pattern, multiplier in patterns:
        for m in re.finditer(pattern, t):
            number = m.group(1).replace(",", "")
            matches.append((m.start(), m.end(), int(float(number) * multiplier)))
    # A phrase can match more than one pattern. Keep the longest unique span.
    unique = {}
    for start, end, value in matches:
        unique[(start, end)] = value
    return sorted([(s, e, v) for (s, e), v in unique.items()], key=lambda x: x[0])


def _loan_amount_from_text(text: str) -> Optional[int]:
    """Extract the amount requested for the loan, not the property's market value."""
    t = text.lower().replace(",", "").replace("₹", "")
    matches = _money_matches(text)
    if not matches:
        return None

    # Strong loan-request phrases take priority. This prevents
    # "worth 80 lakhs and I need 40 lakhs" from selecting 80 lakhs.
    loan_patterns = [
        r"(?:need|needs|want|wants|require|requires|borrow|borrowing|looking for)\s+(?:around\s+|about\s+|approximately\s+|for\s+|of\s+)?",
        r"(?:loan amount|loan)\s*(?:of|is|for)?\s*",
        r"(?:take|taking)\s+(?:a\s+)?loan\s+(?:of|for)\s*",
    ]
    candidates = []
    for pattern in loan_patterns:
        for m in re.finditer(pattern, t):
            after = m.end()
            for start, end, value in matches:
                if start >= after and start - after <= 45:
                    candidates.append((start - after, value))
                    break
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    # If the whole utterance is clearly about a loan and has one amount,
    # accept that amount. Do not use a bare property-value statement.
    loan_words = ("loan", "borrow", "borrowing", "lakh", "lakhs", "crore", "crores", "cr")
    property_value_words = ("worth", "market value", "property value", "valued at")
    if any(word in t for word in loan_words) and not any(word in t for word in property_value_words):
        return matches[-1][2]
    return None


def _market_value_from_text(text: str) -> Optional[int]:
    """Extract a property market value from phrases such as "worth 1 crore"."""
    t = text.lower()
    matches = _money_matches(text)
    if not matches:
        return None

    property_patterns = [
        r"(?:worth|market value|property value|valued at)\s+(?:about\s+|around\s+|approximately\s+|of\s+)?",
        r"(?:worth|valued)\s+(?:about\s+|around\s+|approximately\s+)?",
    ]
    candidates = []
    for pattern in property_patterns:
        for m in re.finditer(pattern, t):
            after = m.end()
            for start, end, value in matches:
                if start >= after and start - after <= 45:
                    candidates.append((start - after, value))
                    break
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    return None


def extract_facts(text: str) -> Dict[str, Any]:
    t = text.lower()
    facts: Dict[str, Any] = {}

    if "agricultural" in t or "agriculture" in t:
        facts["property_type"] = "Agricultural"
    elif any(x in t for x in ["residential", "house", "flat", "home"]):
        facts["property_type"] = "Residential"
    elif any(x in t for x in ["commercial", "shop", "office"]):
        facts["property_type"] = "Commercial"
    elif any(x in t for x in ["industrial", "factory"]):
        facts["property_type"] = "Industrial"

    if any(x in t for x in ["joint", "jointly", "co-owned", "co owned"]):
        facts["ownership_status"] = "Joint"
    elif any(x in t for x in ["sole owner", "only owner", "my own", "owned by me"]):
        facts["ownership_status"] = "Sole"

    if any(x in t for x in ["original documents", "original property documents", "original papers", "original documents are available", "original property documents are available", "original papers are available"]):
        if not any(x in t for x in ["don't have", "do not have", "no original", "only photocopy", "photocopy only", "copies only"]):
            facts["documents_available"] = True
    if any(x in t for x in ["don't have original", "do not have original", "no original", "only photocopy", "photocopy only", "copies only", "originals unavailable"]):
        facts["documents_available"] = False

    amount = _loan_amount_from_text(text)
    if amount is not None:
        facts["loan_amount"] = amount

    if any(x in t for x in ["self-employed", "self employed", "business", "business owner"]):
        facts["occupation"] = "Self-Employed"
    elif any(x in t for x in ["salaried", "salary", "job", "employee"]):
        facts["occupation"] = "Salaried"

    if any(x in t for x in ["bank account", "bank", "credited to my bank", "comes into my bank"]):
        facts["income_mode"] = "Bank"
    elif "cash" in t:
        facts["income_mode"] = "Cash"

    market_value = _market_value_from_text(text)
    if market_value is not None:
        facts["market_value"] = market_value

    m = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?)\b", t)
    if m:
        facts["tenure"] = int(m.group(1))

    if any(x in t for x in ["already have a loan", "existing loan", "loan against this property", "loan on this property", "current loan"]):
        facts["existing_property_loan"] = True
    if any(x in t for x in ["reduce my emi", "reduce emi", "lower my emi", "emi reduction"]):
        facts["emi_reduction_request"] = True

    return facts


def apply_facts(state, facts: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    # Latest explicit answer wins.
    for key, value in facts.items():
        if hasattr(state, key):
            setattr(state, key, value)

    if state.existing_property_loan or state.emi_reduction_request:
        state.transfer_required = True
        state.status = "TRANSFER"
        return "TRANSFER", "Existing property loan / EMI reduction request"

    if state.property_type == "Agricultural":
        state.disqualified = True
        state.status = "NOT_ELIGIBLE"
        state.disqualification_reason = "Agricultural property"
        return "DISQUALIFY", state.disqualification_reason

    if state.documents_available is False:
        state.disqualified = True
        state.status = "NOT_ELIGIBLE"
        state.disqualification_reason = "Original property documents unavailable"
        return "DISQUALIFY", state.disqualification_reason

    if state.income_mode == "Cash":
        state.disqualified = True
        state.status = "NOT_ELIGIBLE"
        state.disqualification_reason = "Income received in cash"
        return "DISQUALIFY", state.disqualification_reason

    if state.tenure is not None and not (MIN_TENURE <= state.tenure <= MAX_TENURE):
        state.disqualified = True
        state.status = "NOT_ELIGIBLE"
        state.disqualification_reason = "Tenure must be between 3 and 15 years"
        return "DISQUALIFY", state.disqualification_reason

    return "CONTINUE", None


def all_eligibility_answered(state) -> bool:
    return first_missing(state) is None
