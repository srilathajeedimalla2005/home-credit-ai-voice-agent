from backend.agent import VoiceAgent

def answer(agent, text):
    return agent.process(text)

def test_eligible_flow():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    answer(a, "I have a residential house jointly owned with my wife, worth about 1 crore.")
    answer(a, "Yes, the original documents are available.")
    answer(a, "I need 50 lakhs.")
    answer(a, "I am self-employed and my income comes into my bank.")
    result = answer(a, "I want a tenure of 10 years.")
    assert result["state"]["status"] == "QUALIFIED"

def test_existing_loan_transfer():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    result = answer(a, "I already have a loan on this property.")
    assert result["state"]["status"] == "TRANSFER"
    assert result["finished"] is True

def test_busy_callback():
    a = VoiceAgent("Rahul")
    a.start()
    result = answer(a, "I'm in a meeting, please call later.")
    assert result["state"]["status"] == "CALLBACK"
    assert result["finished"] is True

def test_above_cap_then_confirm():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    answer(a, "I have a residential house.")
    answer(a, "I need 90 lakhs.")
    assert a.state.status == "AWAITING_LOAN_CAP_CONFIRMATION"
    result = answer(a, "Yes, proceed.")
    assert result["state"]["loan_amount"] == 7_500_000


def test_above_cap_turn_preserves_market_value_and_confirmation_continues():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    answer(a, "I have a residential house that I own myself.")
    answer(a, "It is solely owned by me.")
    answer(a, "Yes, the original property documents are available.")
    answer(a, "I need 90 lakhs. The property is worth about 1 crore.")
    assert a.state.status == "AWAITING_LOAN_CAP_CONFIRMATION"
    assert a.state.market_value == 10_000_000

    result = answer(a, "Yes, proceed with 75 lakhs.")
    assert result["state"]["loan_amount"] == 7_500_000
    assert result["state"]["status"] == "IN_PROGRESS"

    answer(a, "I am self-employed and my income comes into my bank.")
    result = answer(a, "I want a tenure of 10 years.")
    assert result["state"]["market_value"] == 10_000_000
    assert result["state"]["tenure"] == 10
    assert result["state"]["status"] == "QUALIFIED"


def test_confirmation_turn_can_also_capture_market_value():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    answer(a, "I have a residential house.")
    answer(a, "I need 90 lakhs.")
    assert a.state.status == "AWAITING_LOAN_CAP_CONFIRMATION"
    result = answer(a, "Yes, proceed. The property is worth 1 crore.")
    assert result["state"]["loan_amount"] == 7_500_000
    assert result["state"]["market_value"] == 10_000_000
    assert result["state"]["status"] == "IN_PROGRESS"


def test_screenshot_flow_finishes_after_market_value_arrives_late():
    a = VoiceAgent("Rahul")
    a.start()
    answer(a, "Yes, this is Rahul.")
    answer(a, "I have a residential house and it is my own.")
    answer(a, "It is solely owned by me.")
    answer(a, "Yes, the original property documents are available.")
    answer(a, "I need 90 lakhs.")
    assert a.state.status == "AWAITING_LOAN_CAP_CONFIRMATION"
    answer(a, "Yes, proceed with 75 lakhs.")
    answer(a, "I am self-employed and my income comes into my bank.")
    answer(a, "I want a tenure of 10 years.")
    assert a.state.tenure == 10
    assert a.state.market_value is None
    assert a.state.status == "IN_PROGRESS"

    result = answer(a, "The property is worth about 1 crore.")
    assert result["state"]["market_value"] == 10_000_000
    assert result["state"]["tenure"] == 10
    assert result["state"]["loan_amount"] == 7_500_000
    assert result["state"]["status"] == "QUALIFIED"
    assert result["finished"] is True
