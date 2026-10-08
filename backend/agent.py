import uuid
from datetime import datetime
from typing import Dict, Any

from .state import QualificationState
from .business_rules import (
    QUESTIONS, first_missing, extract_facts, apply_facts,
    all_eligibility_answered, MAX_LOAN
)
from .config import COMPANY_NAME, AGENT_NAME, AGENT_GENDER, LANGUAGE_TO_SPEAK
from .database import save_conversation
from .prompt import render_prompt

class VoiceAgent:
    def __init__(self, customer_name="Customer", language=None):
        self.call_id = str(uuid.uuid4())
        self.customer_name = customer_name
        self.language = language or LANGUAGE_TO_SPEAK
        self.state = QualificationState()
        self.transcript = []

    def _log(self, speaker, text):
        self.transcript.append({"speaker": speaker, "text": text})

    def _reply(self, text):
        self._log("AI", text)
        return text

    def start(self):
        msg = f"Hello, may I speak with {self.customer_name}?"
        self._log("AI", msg)
        return self.payload(msg)

    def payload(self, message):
        return {
            "call_id": self.call_id,
            "message": message,
            "state": self.state.to_dict(),
            "transcript": self.transcript,
            "finished": self.state.completed,
        }

    def process(self, text):
        text = text.strip()
        if not text:
            return self.payload("I'm sorry, I didn't catch that. Could you please repeat that?")

        self._log("Customer", text)
        t = text.lower()

        # Opening verification / busy state
        if not self.state.customer_verified:
            if any(x in t for x in ["busy", "in a meeting", "can't talk", "cannot talk", "not free", "call later"]):
                self.state.status = "CALLBACK"
                self.state.completed = True
                return self.payload(self._reply(
                    "Certainly, I understand. What would be a convenient time for us to call you back?"
                ))
            if any(x in t for x in ["yes", "speaking", "this is", "that's me", "correct", "sure"]):
                self.state.customer_verified = True
                return self.payload(self._reply(
                    f"Thank you. I'm calling from {COMPANY_NAME}. As one of our valued customers, "
                    "you may be eligible for a special Loan Against Property offer of up to ₹75 lakh. "
                    "I'd like to ask a few questions to check whether the offer is suitable for you."
                ))
            return self.payload(self._reply(
                f"Thank you. I'm calling from {COMPANY_NAME}. May I confirm that I am speaking with "
                f"{self.customer_name}?"
            ))

        # Explicit busy diversion after verification
        if any(x in t for x in ["busy", "in a meeting", "can't talk", "cannot talk", "not free"]):
            self.state.status = "CALLBACK"
            self.state.completed = True
            return self.payload(self._reply(
                "Certainly, I understand. What would be a convenient time for us to call you back?"
            ))

        # If the previous turn asked for confirmation of the ₹75 lakh cap,
        # handle that answer before normal fact extraction. This prevents the
        # same large amount from being interpreted as a fresh loan request.
        # If the previous turn asked for confirmation of the ₹75 lakh cap,
        # accept the confirmation and then continue normal fact extraction.
        # This is important because the confirmation turn may also contain
        # another fact, such as market value.
        if self.state.status == "AWAITING_LOAN_CAP_CONFIRMATION":
            if any(x in t for x in ["yes", "okay", "ok", "sure", "proceed"]):
                result, reason = apply_facts(self.state, {"loan_amount": MAX_LOAN})
                if result != "CONTINUE":
                    self.state.completed = True
                    return self.payload(self._reply(
                        "Thank you. Unfortunately, I cannot continue with this request right now."
                    ))
                self.state.status = "IN_PROGRESS"
            elif any(x in t for x in ["no", "not interested", "don't want", "do not want"]):
                self.state.status = "NOT_INTERESTED"
                self.state.completed = True
                return self.payload(self._reply(
                    "I understand. Thank you for your time. Have a good day."
                ))
            else:
                return self.payload(self._reply(
                    "The current offer is available for up to ₹75 lakh. "
                    "Would you like to proceed with the maximum eligible amount of ₹75 lakh?"
                ))

        # User can give natural-language facts in any order.
        facts = extract_facts(text)

        # Special handling for a requested loan above ₹75 lakh. Preserve all
        # other facts from the same sentence instead of discarding them.
        amount = facts.get("loan_amount")
        if amount is not None and amount > MAX_LOAN:
            other_facts = {k: v for k, v in facts.items() if k != "loan_amount"}
            result, reason = apply_facts(self.state, other_facts)
            if result == "TRANSFER":
                self.state.completed = True
                return self.payload(self._reply(
                    "Thank you for clarifying. Since you already have an existing loan on the property "
                    "or are looking to reduce your current EMI, this needs to be handled by our loan-transfer "
                    "specialist. A specialist will contact you shortly. Thank you for your time."
                ))
            if result == "DISQUALIFY":
                self.state.completed = True
                return self.payload(self._reply(
                    "Thank you for sharing that. Unfortunately, you do not meet the criteria for this "
                    "specific offer at this time. Thank you for your time."
                ))
            self.state.loan_amount = None
            self.state.status = "AWAITING_LOAN_CAP_CONFIRMATION"
            return self.payload(self._reply(
                "The current offer is available for up to ₹75 lakh. "
                "Would you like to proceed with the maximum eligible amount of ₹75 lakh?"
            ))

        result, reason = apply_facts(self.state, facts)

        if result == "TRANSFER":
            self.state.completed = True
            return self.payload(self._reply(
                "Thank you for clarifying. Since you already have an existing loan on the property "
                "or are looking to reduce your current EMI, this needs to be handled by our loan-transfer "
                "specialist. A specialist will contact you shortly. Thank you for your time."
            ))

        if result == "DISQUALIFY":
            self.state.completed = True
            return self.payload(self._reply(
                "Thank you for sharing that. Unfortunately, you do not meet the criteria for this "
                "specific offer at this time. Thank you for your time."
            ))

        # If loan amount is now valid and all items are complete, handoff.
        if all_eligibility_answered(self.state):
            self.state.status = "QUALIFIED"
            self.state.completed = True
            return self.payload(self._reply(
                "Thank you. Based on the preliminary information, you meet the initial criteria for "
                "this offer. A senior loan expert will contact you shortly to discuss the next steps "
                "and provide the exact interest-rate details."
            ))

        missing = first_missing(self.state)
        question = dict(QUESTIONS)[missing]

        # More natural question for the first missing field.
        responses = {
            "property_type": "What type of property do you have: residential, commercial, or industrial?",
            "ownership_status": "Is the property solely owned by you, or is it jointly owned?",
            "documents_available": "Do you have the original property documents available for verification?",
            "loan_amount": "How much would you like to borrow?",
            "occupation_income": "Are you salaried or self-employed, and is your income received through your bank account or in cash?",
            "market_value": "Approximately what is the current market value of the property?",
            "tenure": "How many years would you like to take to repay the loan?",
        }
        return self.payload(self._reply(responses[missing]))

    def save(self):
        save_conversation(
            self.call_id,
            self.state.status,
            self.customer_name,
            "\n".join(f"{x['speaker']}: {x['text']}" for x in self.transcript)
        )
