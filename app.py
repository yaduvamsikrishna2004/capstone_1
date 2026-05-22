import logging

from whatsapp import send_whatsapp_message
from sms import send_sms
from email_sender import send_email
from rag import (
    load_pdf,
    split_documents,
    create_embeddings,
    store_embeddings,
    generate_summary,
    generate_short_summary
)
from database import (
    initialize_database,
    save_summary,
    view_summaries
)

# --------------------------------
# INITIALIZE DATABASE
# --------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

initialize_database()

# --------------------------------
# LOAD PDF
# --------------------------------
documents = load_pdf("documents/ai.pdf")

print(f"Loaded {len(documents)} pages")

# --------------------------------
# SPLIT INTO CHUNKS
# --------------------------------
chunks = split_documents(documents)

print(f"Created {len(chunks)} chunks")

# --------------------------------
# CREATE EMBEDDINGS
# --------------------------------
texts, embeddings = create_embeddings(chunks)

print("Embeddings created")

# --------------------------------
# STORE EMBEDDINGS
# --------------------------------
store_embeddings(texts, embeddings)

# --------------------------------
# USER QUERY
# --------------------------------
query = "Explain Artificial Intelligence"

# --------------------------------
# GENERATE AI RESPONSE
# --------------------------------
summary = generate_summary(query)
short_summary = generate_short_summary(summary)

# --------------------------------
# PRINT RESPONSE
# --------------------------------
print("\nAI GENERATED RESPONSE:\n")

print(summary)

print("\nSHORT SUMMARY:\n")

print(short_summary)
# --------------------------------
# SAVE TO DATABASE
# --------------------------------
save_summary(query, summary)

# --------------------------------
# VIEW SAVED DATA
# --------------------------------
print("\nDATABASE CONTENTS:\n")

rows = view_summaries()

for row in rows:

    print(row)

# --------------------------------
# --------------------------------
# SEND TO WHATSAPP
# --------------------------------
send_whatsapp_message(short_summary)
# --------------------------------
# SEND SMS
# --------------------------------
send_sms(short_summary)
# --------------------------------
# SEND EMAIL
# --------------------------------
email_sent = send_email(summary)
if not email_sent:
    print("Email sending failed. Check logs for SMTP/auth/config details.")
