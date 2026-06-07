from fastapi import FastAPI, Form, Response
import africastalking
from google.cloud import firestore
import os
import logging

# Initialize internal logging vectors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PPR_EWS_LOGS")

app = FastAPI()

# Initialize Third-Party Cloud Infrastructure Connections
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "your_api_key")
africastalking.initialize(AT_USERNAME, AT_API_KEY)
sms_gateway = africastalking.SMS

# Initialize Native Serverless Database Client
try:
    db = firestore.Client()
except Exception as e:
    logger.warning(f"Firestore fallback enabled for development contexts. Error: {str(e)}")
    db = None

# Mapped Regional Stakeholder Directory Profiles
VET_OFFICERS = {
    "1": {"lga": "Sumaila", "phone": "+2348031111111"},
    "2": {"lga": "Takai", "phone": "+2348032222222"},
    "3": {"lga": "Gaya", "phone": "+2348033333333"}
}

# Unified Bi-lingual Content Content Matrix
LOCALIZED_CONTENT = {
    "1": {  # =============== HAUSA WORKSPACE DICTIONARY ===============
        "main_menu": (
            "CON Barka da zuwa PPR Alert.\n"
            "1. Rahoton Rashin Lafiya (Report)\n"
            "2. Bayani akan PPR (Info)"
        ),
        "symptom_menu": (
            "CON Zabi Alamun Da Ka Gani:\n"
            "1. Zawo da Zazzabi\n"
            "2. Gyambo a baki\n"
            "3. Wahalar Numfashi\n"
            "4. Wasu daban"
        ),
        "lga_menu": (
            "CON Zabi Karamar Hukuma:\n"
            "1. Sumaila\n"
            "2. Takai\n"
            "3. Gaya"
        ),
        "symptoms": {"1": "Zawo da Zazzabi", "2": "Gyambo a baki", "3": "Wahalar Numfashi", "4": "Wasu daban"},
        "confirmation": "END Mun gode da rahotonku. An sanar da jami'an lafiyar dabbobi na yankin ku.",
        "info_payload": "END PPR cuta ce mai saurin kisa ga awaki da tumaki. Tuntubi jami'an dabbobi da wuri domin riga-kafi.",
        "invalid_error": "CON Shigarwa ba daidai ba. Latsa 1 ko 2 domin ci gaba.",
        "validation_error": "END Shigarwa ba daidai ba. Kaddamar da zama sake la."
    },
    "2": {  # =============== ENGLISH WORKSPACE DICTIONARY ===============
        "main_menu": (
            "CON Welcome to PPR Alert.\n"
            "1. Report Sick Animal\n"
            "2. Veterinary Info"
        ),
        "symptom_menu": (
            "CON Select Observed Symptom:\n"
            "1. Diarrhea/Fever\n"
            "2. Mouth Sores\n"
            "3. Difficulty Breathing\n"
            "4. Other"
        ),
        "lga_menu": (
            "CON Select Local Government Area (LGA):\n"
            "1. Sumaila\n"
            "2. Takai\n"
            "3. Gaya"
        ),
        "symptoms": {"1": "Diarrhea/Fever", "2": "Mouth Sores", "3": "Difficulty Breathing", "4": "Other"},
        "confirmation": "END Thank you. Your outbreak report has been recorded and regional veterinary officers have been alerted.",
        "info_payload": "END PPR is a highly fatal viral disease affecting goats and sheep. Contact local vet services immediately for vaccination.",
        "invalid_error": "CON Invalid selection. Please press 1 or 2 to proceed.",
        "validation_error": "END Invalid input sequence. Please restart the session."
    }
}

@app.post("/ussd")
async def handle_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form("")
):
    normalized_text = text.strip()
    segments = normalized_text.split("*") if normalized_text else []
    total_segments = len(segments)

    # -------------------------------------------------------------------------
    # LEVEL 0: ROOT SCREEN - LANGUAGE SELECTION DIALOGUE
    # -------------------------------------------------------------------------
    if total_segments == 0 or segments[0] == "":
        root_prompt = "CON Welcome to PPR Alert / Barka da zuwa.\n1. Hausa\n2. English"
        return Response(content=root_prompt, media_type="text/plain")

    # Capture selected language vector context immediately
    lang_choice = segments[0]

    # Structural Validation Catch for Root Actions
    if lang_choice not in ["1", "2"]:
        # Replay prompt with unified, bi-lingual error string
        error_prompt = "CON Input error. Choose language / Zabi yare:\n1. Hausa\n2. English"
        return Response(content=error_prompt, media_type="text/plain")

    # Fetch corresponding language profile array mapping directly
    lang_pack = LOCALIZED_CONTENT[lang_choice]

    # -------------------------------------------------------------------------
    # LEVEL 1: MAIN FUNCTIONAL BRANCH DIRECTORY
    # -------------------------------------------------------------------------
    if total_segments == 1:
        return Response(content=lang_pack["main_menu"], media_type="text/plain")

    user_action = segments[1]

    # CRITICAL ROUTE 1: Outbreak Surveillance Multi-Form Logging Framework
    if user_action == "1":
        
        # LEVEL 2: Symptom Profiling Selection
        if total_segments == 2:
            return Response(content=lang_pack["symptom_menu"], media_type="text/plain")
        
        # LEVEL 3: LGA Geographic Mapping Check
        elif total_segments == 3:
            symptom_id = segments[2]
            if symptom_id not in ["1", "2", "3", "4"]:
                return Response(content=lang_pack["invalid_error"], media_type="text/plain")
            return Response(content=lang_pack["lga_menu"], media_type="text/plain")
        
        # LEVEL 4: Data Consolidation & Downstream Alert Execution
        elif total_segments == 4:
            symptom_id = segments[2]
            lga_id = segments[3]

            if lga_id not in ["1", "2", "3"]:
                return Response(content=lang_pack["invalid_error"], media_type="text/plain")

            selected_symptom = lang_pack["symptoms"].get(symptom_id, "Unknown Symptom")
            target_officer = VET_OFFICERS.get(lga_id)

            if target_officer:
                # Compile strict programmatic notification alerts
                sms_alert_message = (
                    f"PPR SURVEILLANCE EXigent ALERT:\n"
                    f"Outbreak reported in {target_officer['lga']} LGA.\n"
                    f"Reporter Mobile: {phoneNumber}\n"
                    f"Observed Metric: {selected_symptom}."
                )
                
                # Asynchronous fire-and-forget message payload distribution
                try:
                    sms_gateway.send(sms_alert_message, [target_officer["phone"]])
                except Exception as sms_fault:
                    logger.error(f"Downstream SMS distribution channel crashed: {str(sms_fault)}")

            # Persistent non-blocking telemetry payload write execution
            if db:
                try:
                    report_ref = db.collection("outbreak_reports").document(sessionId)
                    report_ref.set({
                        "sessionId": sessionId,
                        "phoneNumber": phoneNumber,
                        "language": "Hausa" if lang_choice == "1" else "English",
                        "lga": target_officer["lga"] if target_officer else "Unknown",
                        "symptom": selected_symptom,
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
                except Exception as db_fault:
                    logger.error(f"Firestore database logging engine failure: {str(db_fault)}")

            return Response(content=lang_pack["confirmation"], media_type="text/plain")

    # CRITICAL ROUTE 2: Educational Advisory Streaming Block
    elif user_action == "2":
        return Response(content=lang_pack["info_payload"], media_type="text/plain")

    # Core Exception Fallback catch-all boundary
    else:
        return Response(content=lang_pack["validation_error"], media_type="text/plain")


@app.post("/ivr")
async def handle_ivr(
    isActive: str = Form(...),
    sessionId: str = Form(...),
    callerNumber: str = Form(...),
    dtmfDigits: str = Form(None)
):
    """
    Stateless IVR Voice Webhook routing handler.
    Generates strict XML responses for Africa's Talking Media Server.
    """
    # If network indicates hang-up drop, clean stack resources instantly
    if isActive == "0":
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="application/xml")

    # -------------------------------------------------------------------------
    # AUDIO LEVEL 0: ROOT VOICE INGESTION - LANGUAGE SIGNALLING
    # -------------------------------------------------------------------------
    if not dtmfDigits:
        xml_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '    <GetDigits timeout="10" finishOnKey="#">'
            '        <Play url="https://storage.googleapis.com/ppr-ews-bucket/audio/root_language_prompt.mp3"/>'
            '    </GetDigits>'
            '</Response>'
        )
        return Response(content=xml_payload, media_type="application/xml")

    # Parse nested digit context mapping variables safely
    digits_chain = dtmfDigits.strip()
    digits_len = len(digits_chain)
    selected_lang = digits_chain[0]

    if selected_lang not in ["1", "2"]:
        # Fallback tracking loop to play adaptive error replays upon input fault
        xml_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '    <GetDigits timeout="10" finishOnKey="#">'
            '        <Play url="https://storage.googleapis.com/ppr-ews-bucket/audio/invalid_selection.mp3"/>'
            '    </GetDigits>'
            '</Response>'
        )
        return Response(content=xml_payload, media_type="application/xml")

    # Assign distinct base cloud target locations based on active user context
    lang_folder = "hausa" if selected_lang == "1" else "english"
    base_audio_url = f"https://storage.googleapis.com/ppr-ews-bucket/audio/{lang_folder}"

    # -------------------------------------------------------------------------
    # AUDIO LEVEL 1: ISOLATED WORKSPACE PROCESSING
    # -------------------------------------------------------------------------
    if digits_len == 1:
        xml_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '    <GetDigits timeout="10" finishOnKey="#">'
            '        <Play url="' + base_audio_url + '/main_menu.mp3"/>'
            '    </GetDigits>'
            '</Response>'
        )
        return Response(content=xml_payload, media_type="application/xml")

    action_selection = digits_chain[1]

    if action_selection == "1":
        # -------------------------------------------------------------------------
        # SURVEILLANCE NESTED ROUTING SEQUENCING
        # -------------------------------------------------------------------------
        if digits_len == 2:
            xml_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                '    <GetDigits timeout="10" finishOnKey="#">'
                '        <Play url="' + base_audio_url + '/symptom_menu.mp3"/>'
                '    </GetDigits>'
                '</Response>'
            )
            return Response(content=xml_payload, media_type="application/xml")

        elif digits_len == 3:
            xml_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                '    <GetDigits timeout="10" finishOnKey="#">'
                '        <Play url="' + base_audio_url + '/lga_menu.mp3"/>'
                '    </GetDigits>'
                '</Response>'
            )
            return Response(content=xml_payload, media_type="application/xml")

        elif digits_len == 4:
            # Complete execution and drop active line socket loops
            xml_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                '    <Play url="' + base_audio_url + '/confirmation.mp3"/>'
                '    <Reject/>'
                '</Response>'
            )
            return Response(content=xml_payload, media_type="application/xml")

    elif action_selection == "2":
        # Stream Information Content and Drop Call
        xml_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '    <Play url="' + base_audio_url + '/info_payload.mp3"/>'
            '    <Reject/>'
            '</Response>'
        )
        return Response(content=xml_payload, media_type="application/xml")

    # General System Drop Fallback Exception handler
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>', 
        media_type="application/xml"
    )