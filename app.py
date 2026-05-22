from rag import (
    load_pdf,
    split_documents,
    create_embeddings,
    store_embeddings,
    generate_summary
)

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

# --------------------------------
# PRINT RESPONSE
# --------------------------------
print("\nAI GENERATED RESPONSE:\n")

print(summary)