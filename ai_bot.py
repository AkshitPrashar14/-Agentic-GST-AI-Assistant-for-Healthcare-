import faiss
import torch
import numpy as np
import json
import re
import os
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# HuggingFace token for accessing models
# Get your token from: https://huggingface.co/settings/tokens
# Set it as environment variable: export HF_TOKEN="your_token_here"
# Or create a .env file with: HF_TOKEN=your_token_here
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError(
        "HF_TOKEN environment variable is required. "
        "Get your token from: https://huggingface.co/settings/tokens"
    )

# -----------------------------
# Load GST dataset (JSON format)
# -----------------------------
print("Loading GST dataset...")
with open("dataset/dataset.txt", "r", encoding="utf-8") as f:
    content = f.read()
    # Fix syntax error: replace {s with {
    content = content.replace("{s", "{")
    # Parse JSON
    gst_entries = json.loads(content)

# Create document strings from GST entries
documents = []
for entry in gst_entries:
    # Combine question and answer for better retrieval
    doc_text = f"Question: {entry['question']}\nAnswer: {entry['answer']}\nGST Rate: {entry['gst_rate']}\nGST Applicable: {entry['gst_applicable']}"
    documents.append(doc_text)

print(f"Loaded {len(documents)} GST entries")

# -----------------------------
# Check GPU availability
# -----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

# -----------------------------
# Embedding model (E5 / BGE)
# -----------------------------
print("Loading embedding model (E5)...")
embedder = SentenceTransformer("intfloat/e5-base-v2", device=device)

print("Creating embeddings for GST entries...")
doc_embeddings = embedder.encode(
    ["passage: " + d for d in documents],
    normalize_embeddings=True,
    show_progress_bar=True,
    device=device
)

# -----------------------------
# FAISS Vector DB
# -----------------------------
print("Building FAISS index...")
dim = doc_embeddings.shape[1]
index = faiss.IndexFlatIP(dim)  # Inner Product for cosine similarity (normalized embeddings)
index.add(doc_embeddings.astype('float32'))
print(f"FAISS index built with {index.ntotal} vectors")

# -----------------------------
# Initialize HuggingFace API Client
# -----------------------------
print("Initializing HuggingFace API client...")
os.environ["HF_TOKEN"] = HF_TOKEN

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

model_name = "Qwen/Qwen2.5-7B-Instruct:together"
print(f"Using model: {model_name}")
print("API client ready!")

# -----------------------------
# Retriever: Top-k relevant GST entries
# -----------------------------
def retrieve(query, top_k=3):
    """
    Retrieve top-k relevant GST entries using FAISS vector search
    """
    q_emb = embedder.encode(
        ["query: " + query],
        normalize_embeddings=True,
        device=device
    )
    scores, ids = index.search(q_emb.astype('float32'), top_k)
    retrieved_docs = [documents[i] for i in ids[0]]
    return retrieved_docs, scores[0]

# -----------------------------
# RAG Answering with human-like responses
# -----------------------------
def rag_answer(query):
    """
    RAG-based answering with dataset knowledge prioritized, 
    but allows general knowledge fallback for natural human-like responses
    """
    # Step 1: Retrieve top-k relevant GST entries
    context_docs, scores = retrieve(query, top_k=3)
    
    # Check relevance - if scores are very low, dataset might not have good matches
    avg_score = np.mean(scores) if len(scores) > 0 else 0
    has_good_match = avg_score > 0.3  # Threshold for considering dataset matches as relevant
    
    # Step 2: Format context
    context = "\n\n".join([f"Entry {i+1}:\n{doc}" for i, doc in enumerate(context_docs)])
    
    # Add relevance note to help the model understand dataset quality
    if not has_good_match:
        context = "Note: The retrieved entries may not be highly relevant to the question. " + context
    
    # Step 3: Create prompt for Qwen model with human-like instructions
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful and knowledgeable GST (Goods and Services Tax) assistant. "
                "Your primary source of information is the provided GST dataset entries. "
                "When answering questions:\n\n"
                "1. **Prioritize the dataset**: If the answer is clearly present in the provided GST entries, "
                "use that information and cite it naturally in your response.\n\n"
                "2. **Natural responses**: Write in a conversational, human-like manner. Explain things clearly "
                "as if you're helping a friend understand GST rules.\n\n"
                "3. **General knowledge fallback**: If the specific answer isn't in the dataset but you have "
                "relevant general knowledge about GST, healthcare services, or tax regulations, you may use it "
                "to provide a helpful answer. However, mention that this is general knowledge and may need verification.\n\n"
                "4. **Uncertainty**: If you truly don't know the answer, be honest and suggest consulting a tax "
                "professional or official GST guidelines.\n\n"
                "Always be clear, helpful, and conversational in your responses."
            )
        },
        {
            "role": "user",
            "content": f"""Here are some relevant GST entries from the dataset:

{context}

---

Question: {query}

Please provide a helpful, natural answer. If the answer is in the dataset entries above, prioritize that information. 
If not, you may use your general knowledge about GST and healthcare services to provide a useful response."""
        }
    ]

    # Step 4: Generate response using HuggingFace API with higher temperature for natural responses
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,  # Higher temperature for more natural, varied responses
            max_tokens=300,  # More tokens for complete, detailed answers
            top_p=0.9
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Check if response is empty or invalid
        if not response or len(response) < 3:
            return "Error: Model generated empty response. Please try again."
        
        return response
        
    except Exception as e:
        import traceback
        error_msg = f"Error generating response: {str(e)}\n{traceback.format_exc()}"
        print(f"DEBUG: {error_msg}")
        return error_msg

# -----------------------------
# Chat loop
# -----------------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("GST RAG Assistant Ready!")
    print("Ask questions about GST applicability on healthcare services.")
    print("Type 'exit' to quit.")
    print("="*60 + "\n")
    
    while True:
        q = input("Ask: ")
        if q.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break
        if not q.strip():
            continue
        print("\nAnswer:", rag_answer(q))
        print("-"*60 + "\n")
