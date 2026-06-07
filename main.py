from fastapi import FastAPI, Form, Response
import africastalking
from google.cloud import firestore
import os
import logging
import time
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PPR_EWS_LOGS")

app = FastAPI()

VALID_LANGUAGE_CHOICES = {"1", "2"}
VALID_SYMPTOMS = {"1", "2", "3", "4"}
VALID_LGAS = {"1", "2", "3"}

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")
try:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    sms_gateway = africastalking.SMS
except Exception as exc:
    logger.error("Failed to initialize Africa's Talking: %s", exc, exc_info=True)
    sms_gateway = None

try:
    db = firestore.Client()
except Exception as e:
    logger.warning(f"Firestore fallback enabled for development contexts. Error: {str(e)}")
    db = None

def normalize_ussd_text(text: str) -> List[str]:
    return [segment.strip() for segment in text.strip().split("*") if segment.strip()]

def build_text_response(content: str) -> Response:
    return Response(content=content, media_type="text/plain")

def build_xml_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")

# FIXED: Added single digit extraction parameter optimization
def build_getdigits_payload(audio_url: str, num_digits: int = 1) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'    <GetDigits timeout="10" numDigits="{num_digits}">'
        f'        <Play url="{audio_url}"/>'
        '    </GetDigits>'
        '</Response>'
    )

VET_OFFICERS = {
    "1": {"lga": "Sumaila", "phone": "+2348106999069"},
    "2": {"lga": "Takai", "phone": "+2348122274059"},
    "3": {"lga": "Gaya", "phone": "+2348034023456"}
}

LOCALIZED_CONTENT = {
    "1": {  # HAUSA
        "main_menu": "CON Barka da zuwa PPR Alert.\n1. Rahoton Rashin Lafiya (Report)\n2. Bayani akan PPR (Info)",
        "symptom_menu": "CON Zabi Alamun Da Ka Gani:\n1. Zawo da Zazzabi\n2. Gyambo a baki\n3. Wahalar Numfashi\n4. Wasu daban",
        "lga_menu": "CON Zabi Karamar Hukuma:\n1. Sumaila\n2. Takai\n3. Gaya",
        "symptoms": {"1": "Zawo da Zazzabi", "2": "Gyambo a baki", "3": "Wahalar Numfashi", "4": "Wasu daban"},
        "confirmation": "END Mun gode da rahotonku. An sanar da jami'an lafiyar dabbobi na yankin ku.",
        "info_payload": "END PPR cuta ce mai saurin kisa ga awaki da tumaki. Tuntubi jami'an dabbobi da wuri domin riga-kafi.",
        "invalid_error": "END Shigarwa ba daidai ba. Kaddamar da zama sake la."  # FIXED: Swapped to END to clear loop traps
    },
    "2": {  # ENGLISH
        "main_menu": "CON Welcome to PPR Alert.\n1. Report Sick Animal\n2. Veterinary Info",
        "symptom_menu": "CON Select Observed Symptom:\n1. Diarrhea/Fever\n2. Mouth Sores\n3. Difficulty Breathing\n4. Other",
        "lga_menu": "CON Select Local Government Area (LGA):\n1. Sumaila\n2. Takai\n3. Gaya",
        "symptoms": {"1": "Diarrhea/Fever", "2": "Mouth Sores", "3": "Difficulty Breathing", "4": "Other"},
        "confirmation": "END Thank you. Your outbreak report has been recorded and regional veterinary officers have been alerted.",
        "info_payload": "END PPR is a highly fatal viral disease affecting goats and sheep. Contact local vet services immediately for vaccination.",
        "invalid_error": "END Invalid selection. Please restart the session and choose a valid option." # FIXED: Swapped to END
    }
}

@app.post("/ussd")
async def handle_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form("")
):
    segments = normalize_ussd_text(text)
    total_segments = len(segments)

    if total_segments == 0:
        root_prompt = "CON Welcome to PPR Alert / Barka da zuwa.\n1. Hausa\n2. English"
        return build_text_response(root_prompt)

    lang_choice = segments[0]

    if lang_choice not in VALID_LANGUAGE_CHOICES:
        # If language input is bad, keep it on the root language selector screen
        error_prompt = "CON Input error. Choose language / Zabi yare:\n1. Hausa\n2. English"
        return build_text_response(error_prompt)

    lang_pack = LOCALIZED_CONTENT[lang_choice]

    if total_segments == 1:
        return build_text_response(lang_pack["main_menu"])

    user_action = segments[1]

    if user_action == "1":
        if total_segments == 2:
            return build_text_response(lang_pack["symptom_menu"])
        
        elif total_segments == 3:
            symptom_id = segments[2]
            if symptom_id not in VALID_SYMPTOMS:
                return build_text_response(lang_pack["invalid_error"])
            return build_text_response(lang_pack["lga_menu"])
        
        elif total_segments == 4:
            symptom_id = segments[2]
            lga_id = segments[3]

            if symptom_id not in VALID_SYMPTOMS or lga_id not in VALID_LGAS:
                return build_text_response(lang_pack["invalid_error"])

            selected_symptom = lang_pack["symptoms"].get(symptom_id, "Unknown Symptom")
            target_officer = VET_OFFICERS.get(lga_id)

            if target_officer and sms_gateway is not None:
                sms_alert_message = (
                    f"PPR SURVEILLANCE ALERT:\n"
                    f"Outbreak suspected in {target_officer['lga']} LGA.\n"
                    f"Reporter: {phoneNumber}\n"
                    f"Symptom: {selected_symptom}."
                )
                try:
                    sms_gateway.send(sms_alert_message, [target_officer["phone"]])
                except Exception as sms_fault:
                    logger.error("Downstream SMS distribution failed: %s", sms_fault, exc_info=True)

            if db:
                try:
                    # FIXED: Changed from .add() to .document().set() to guarantee data idempotency
                    db.collection("outbreak_reports").document(sessionId).set({
                        "sessionId": sessionId,
                        "phoneNumber": phoneNumber,
                        "language": "Hausa" if lang_choice == "1" else "English",
                        "lga": target_officer["lga"] if target_officer else "Unknown",
                        "symptom": selected_symptom,
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "createdAt": int(time.time())
                    })
                except Exception as db_fault:
                    logger.error("Firestore DB write failure: %s", db_fault, exc_info=True)

            return build_text_response(lang_pack["confirmation"])

    elif user_action == "2":
        return build_text_response(lang_pack["info_payload"])

    return build_text_response(lang_pack["invalid_error"])


@app.post("/ivr")
async def handle_ivr(
    isActive: str = Form(...),
    sessionId: str = Form(...),
    callerNumber: str = Form(...),
    dtmfDigits: Optional[str] = Form(None)
):
    if isActive == "0":
        return build_xml_response('<?xml version="1.0" encoding="UTF-8"?><Response/>')

    # LEVEL 0: Request first numeric selection input
    if not dtmfDigits:
        xml_payload = build_getdigits_payload("https://storage.googleapis.com/ppr-ews-bucket/audio/root_language_prompt.mp3", num_digits=1)
        return build_xml_response(xml_payload)

    digits_chain = dtmfDigits.strip()
    digits_len = len(digits_chain)
    selected_lang = digits_chain[0]

    if selected_lang not in ["1", "2"]:
        # Re-prompt explicitly if input is out of bounds
        xml_payload = build_getdigits_payload("https://storage.googleapis.com/ppr-ews-bucket/audio/invalid_selection.mp3", num_digits=1)
        return build_xml_response(xml_payload)

    lang_folder = "hausa" if selected_lang == "1" else "english"
    base_audio_url = f"https://storage.googleapis.com/ppr-ews-bucket/audio/{lang_folder}"

    # LEVEL 1: Evaluate selection index loops
    if digits_len == 1:
        xml_payload = build_getdigits_payload(f"{base_audio_url}/main_menu.mp3", num_digits=1)
        return build_xml_response(xml_payload)

    action_selection = digits_chain[1]

    if action_selection == "1":
        if digits_len == 2:
            xml_payload = build_getdigits_payload(f"{base_audio_url}/symptom_menu.mp3", num_digits=1)
            return build_xml_response(xml_payload)

        elif digits_len == 3:
            xml_payload = build_getdigits_payload(f"{base_audio_url}/lga_menu.mp3", num_digits=1)
            return build_xml_response(xml_payload)

        elif digits_len == 4:
            xml_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                f'    <Play url="{base_audio_url}/confirmation.mp3"/>'
                '    <Reject/>'
                '</Response>'
            )
            return build_xml_response(xml_payload)

    elif action_selection == "2":
        xml_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'    <Play url="{base_audio_url}/info_payload.mp3"/>'
            '    <Reject/>'
            '</Response>'
        )
        return build_xml_response(xml_payload)

    return build_xml_response('<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>')