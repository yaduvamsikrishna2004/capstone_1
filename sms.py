from twilio.rest import Client
from dotenv import load_dotenv
import os

# LOAD ENV VARIABLES
load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

twilio_sms_number = os.getenv("TWILIO_SMS_NUMBER")
your_phone_number = os.getenv("YOUR_PHONE_NUMBER")

# CREATE CLIENT
client = Client(account_sid, auth_token)

# SEND SMS
def send_sms(message):

    response = client.messages.create(
        body=message,
        from_=twilio_sms_number,
        to=your_phone_number
    )

    print("SMS sent successfully.")
    print("Message SID:", response.sid)