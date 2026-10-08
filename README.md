# Home Credit AI Voice Agent – LAP Qualification

A local demonstration project based on the provided Home Credit LAP AI Voice Agent assignment.

## Features

- Professional browser dashboard with live qualification progress and call history
- Browser-based voice input using Web Speech API
- Browser text-to-speech for AI responses
- FastAPI backend
- SQLite conversation storage
- Seven-point eligibility state
- Out-of-order information capture
- Immediate disqualification
- Existing-loan / EMI-transfer branch
- Busy-customer callback branch
- ₹75 lakh loan cap handling
- Occupation + bank/cash income rule
- 3–15 year tenure rule
- English/Hindi configuration
- Transcript saving
- Automated business-rule tests

## Important assignment rules implemented

1. Residential, Commercial and Industrial properties are eligible; Agricultural is not.
2. Sole and Joint ownership are eligible.
3. Original property documents must be available.
4. Loan amount is up to ₹75 lakh. Above that, the agent asks whether the customer wants to proceed at ₹75 lakh.
5. Salaried and Self-Employed are allowed, but income must be received through a bank.
6. Market value is captured; no minimum threshold is invented.
7. Tenure must be 3–15 years.
8. Existing property loan or EMI reduction goes to loan-transfer specialist flow.
9. Final handoff happens only after all seven checklist items are answered.

## Windows setup

### 1. Install Python

Use Python 3.10+.

Check:

    python --version

### 2. Open Command Prompt in this folder

    cd path\to\home-credit-ai-voice-agent

### 3. Create virtual environment

    python -m venv venv

### 4. Activate

    venv\Scripts\activate

### 5. Install dependencies

    pip install -r backend\requirements.txt

### 6. Create environment file

Copy:

    backend\.env.example

to:

    backend\.env

Add your OpenAI API key if you want to extend the project with OpenAI extraction. The current local demo works without the API key using deterministic business-rule extraction.

### 7. Start server (Windows)

Recommended: double-click `start_server.bat`.

Or from the project root: `venv\Scripts\python.exe -m uvicorn backend.main:app --reload --app-dir .`

Important: run the command from the project root (the folder containing `backend` and `frontend`), not from inside the `backend` folder.

### 8. Open browser

    http://127.0.0.1:8000

Use Chrome and allow microphone access.

## UI walkthrough

1. Open `http://127.0.0.1:8000`.
2. Enter a customer name and select English or Hindi.
3. Click **Start Call**.
4. Use **Speak** for browser microphone input or type responses in the test box.
5. Watch the seven-point qualification checklist update as facts are extracted.
6. The decision panel shows Qualified, Not Eligible, Transfer, Callback, or other terminal states.
7. Completed calls appear in **Recent Call History** and are stored in `data/conversations.db`.

## Testing without microphone

You can type customer responses into the text box. This is useful for exact business-rule testing.

## Automated tests

Install pytest:

    pip install pytest

Run:

    pytest -q

## Example test flow

1. Start Call
2. Say/type: "Yes, this is Rahul."
3. Say/type: "I have a residential house jointly owned with my wife, worth around one crore."
4. Say/type: "Original documents are available."
5. Say/type: "I need 50 lakhs."
6. Say/type: "I am self-employed and my income comes into my bank."
7. Say/type: "10 years."

Expected result: QUALIFIED.

## Fixed extraction behavior

The qualification engine now distinguishes a property market value from the requested loan amount. For example, `property worth 80 lakhs and I need 40 lakhs` correctly stores `₹40 lakh` as the requested loan. A property value of `1 crore` no longer incorrectly triggers the `₹75 lakh` loan-cap confirmation.

## Assignment deployment

The assignment asks for a voice platform such as Retell AI, Bolna or similar and a public call recording/log link. This local project is the development and testing version. After validating the logic locally, copy the system prompt into the selected voice platform and run the required real voice scenarios there.

## Security

Do not commit backend/.env or expose API keys.
