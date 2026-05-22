from twilio.rest import Client
from dotenv import load_dotenv
import os

# LOAD ENV VARIABLES
load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
your_number = os.getenv("YOUR_WHATSAPP_NUMBER")

# CREATE CLIENT
client = Client(account_sid, auth_token)

# SEND WHATSAPP MESSAGE
def send_whatsapp_message(message):

    response = client.messages.create(
        body=message,
        from_=twilio_number,
        to=your_number
    )

    print("WhatsApp message sent successfully.")
    print("Message SID:", response.sid)