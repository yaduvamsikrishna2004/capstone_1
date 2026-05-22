from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
import ollama
# -----------------------------
# LOAD EMBEDDING MODEL
# -----------------------------
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# CREATE CHROMA CLIENT
# -----------------------------
client = chromadb.PersistentClient(path="./vector_store")

collection = client.get_or_create_collection(
    name="documents"
)

# -----------------------------
# LOAD PDF
# -----------------------------
def load_pdf(file_path):

    loader = PyPDFLoader(file_path)

    documents = loader.load()

    return documents


# -----------------------------
# SPLIT TEXT INTO CHUNKS
# -----------------------------
def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    return chunks


# -----------------------------
# CREATE EMBEDDINGS
# -----------------------------
def create_embeddings(chunks):

    texts = [chunk.page_content for chunk in chunks]

    embeddings = embedding_model.encode(texts)

    return texts, embeddings


# -----------------------------
# STORE EMBEDDINGS IN CHROMA
# -----------------------------
def store_embeddings(texts, embeddings):

    for i, text in enumerate(texts):

        collection.add(
            ids=[str(i)],
            documents=[text],
            embeddings=[embeddings[i].tolist()]
        )

    print("Embeddings stored successfully.")


# -----------------------------
# RETRIEVE RELEVANT CHUNKS
# -----------------------------
def retrieve_documents(query):

    query_embedding = embedding_model.encode([query])

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=3
    )

    return results

# -----------------------------
# GENERATE SUMMARY USING LLAMA3
def generate_summary(query):

    # Retrieve relevant documents
    results = retrieve_documents(query)

    retrieved_docs = results["documents"][0]

    # Combine retrieved chunks
    context = "\n".join(retrieved_docs)

    # Create prompt
    prompt = f"""
    Answer the question using the context below.

    Context:
    {context}

    Question:
    {query}

    Also provide a short summary.
    """

    # Send to Llama3
    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]

# --------------------------------
# GENERATE SHORT SUMMARY
# --------------------------------
def generate_short_summary(summary):

    prompt = f"""
    Shorten the following summary into less than 250 characters.

    Summary:
    {summary}
    """

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    short_summary = response["message"]["content"]

    return short_summary