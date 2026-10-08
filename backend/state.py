from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class QualificationState:
    customer_verified: bool = False
    property_type: Optional[str] = None
    ownership_status: Optional[str] = None
    documents_available: Optional[bool] = None
    loan_amount: Optional[int] = None
    occupation: Optional[str] = None
    income_mode: Optional[str] = None
    market_value: Optional[int] = None
    tenure: Optional[int] = None
    existing_property_loan: bool = False
    emi_reduction_request: bool = False
    disqualified: bool = False
    transfer_required: bool = False
    callback_time: Optional[str] = None
    completed: bool = False
    status: str = "IN_PROGRESS"
    disqualification_reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    def answered_items(self):
        return {
            "property_type": self.property_type is not None,
            "ownership_status": self.ownership_status is not None,
            "documents_available": self.documents_available is not None,
            "loan_amount": self.loan_amount is not None,
            "occupation_income": self.occupation is not None and self.income_mode is not None,
            "market_value": self.market_value is not None,
            "tenure": self.tenure is not None,
        }
