import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import google.generativeai as genai
import logging

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MedicalChatBotView(APIView):
    def post(self, request):
        user_message = request.data.get("message")
        user_id = request.user.id
        logger.info(f"Received POST /chatbot/ from user_id: {user_id}")
        logger.info(f"User message: {user_message}")

        if not user_message:
            return Response(
                {"error": "Message is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not self.is_medical_related(user_message):
            return Response(
                {"message": "I'm only able to assist with medical-related questions."}
            )

        prompt = f"You are a professional medical assistant. Only respond to medical questions.\nUser: {user_message}"

        try:
            # ✅ Correct usage
            model = genai.GenerativeModel("gemini-1.5-flash")
            chat = model.start_chat()
            response = chat.send_message(prompt)
            reply = response.text

            logger.info(f"Gemini response: {reply}")
            return Response({"message": reply})

        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            return Response(
                {"error": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def is_medical_related(self, text):
        medical_keywords = [
            "symptoms",
            "disease",
            "medicine",
            "treatment",
            "doctor",
            "health",
            "diagnosis",
            "infection",
            "fever",
            "pain",
            "therapy",
            "surgery",
            "injury",
            "pill",
            "tablet",
            "vaccine",
            "prescription",
            "cure",
            "allergy",
            "anxiety",
            "asthma",
            "blood pressure",
            "bp",
            "cancer",
            "cardiology",
            "checkup",
            "clinic",
            "cold",
            "covid",
            "covid-19",
            "depression",
            "diabetes",
            "diet",
            "dosage",
            "emergency",
            "epidemic",
            "fatigue",
            "fracture",
            "headache",
            "heart",
            "hormone",
            "insulin",
            "liver",
            "mental health",
            "migraine",
            "nausea",
            "neurology",
            "nutrition",
            "obesity",
            "operation",
            "orthopedic",
            "painkiller",
            "pandemic",
            "paracetamol",
            "pharmacy",
            "physical therapy",
            "physiotherapy",
            "pulse",
            "rash",
            "recovery",
            "respiratory",
            "side effects",
            "specialist",
            "surgeon",
            "swelling",
            "test",
            "therapist",
            "toothache",
            "treatment plan",
            "urine",
            "vomiting",
            "wound",
            "x-ray",
        ]

        greeting_keywords = [
            "hi",
            "hello",
            "hey",
            "how are you",
            "good morning",
            "good evening",
        ]
        all_keywords = medical_keywords + greeting_keywords
        return any(word in text.lower() for word in all_keywords)
