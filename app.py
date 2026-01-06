from flask import Flask, request, jsonify
from flask_cors import CORS
import faiss
import torch
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from openai import OpenAI

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

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

# Global variables to store loaded models and data
embedder = None
index = None
documents = None
client = None
model_name = None
device = None

def load_models():
    """Load all models and data on startup"""
    global embedder, index, documents, client, model_name, device
    
    print("Loading GST dataset...")
    with open("dataset/dataset.txt", "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace("{s", "{")
        gst_entries = json.loads(content)
    
    # Create document strings
    documents = []
    for entry in gst_entries:
        doc_text = f"Question: {entry['question']}\nAnswer: {entry['answer']}\nGST Rate: {entry['gst_rate']}\nGST Applicable: {entry['gst_applicable']}"
        documents.append(doc_text)
    
    print(f"Loaded {len(documents)} GST entries")
    
    # Setup device
    global device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load embedding model
    print("Loading embedding model (E5)...")
    embedder = SentenceTransformer("intfloat/e5-base-v2", device=device)
    
    print("Creating embeddings...")
    doc_embeddings = embedder.encode(
        ["passage: " + d for d in documents],
        normalize_embeddings=True,
        show_progress_bar=False
    )
    
    # Build FAISS index
    print("Building FAISS index...")
    dim = doc_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(doc_embeddings.astype('float32'))
    print(f"FAISS index built with {index.ntotal} vectors")
    
    # Initialize API client
    print("Initializing HuggingFace API client...")
    os.environ["HF_TOKEN"] = HF_TOKEN
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HF_TOKEN,
    )
    model_name = "Qwen/Qwen2.5-7B-Instruct:together"
    print("API client ready!")
    
    return True

def retrieve(query, top_k=3):
    """Retrieve top-k relevant GST entries"""
    global embedder, index, documents, device
    q_emb = embedder.encode(
        ["query: " + query],
        normalize_embeddings=True,
        device=device
    )
    scores, ids = index.search(q_emb.astype('float32'), top_k)
    retrieved_docs = [documents[i] for i in ids[0]]
    return retrieved_docs, scores[0]

def rag_answer(query):
    """RAG-based answering with human-like responses"""
    global client, model_name
    
    # Retrieve relevant entries
    context_docs, scores = retrieve(query, top_k=3)
    
    # Check relevance
    avg_score = np.mean(scores) if len(scores) > 0 else 0
    has_good_match = avg_score > 0.3
    
    # Format context
    context = "\n\n".join([f"Entry {i+1}:\n{doc}" for i, doc in enumerate(context_docs)])
    
    if not has_good_match:
        context = "Note: The retrieved entries may not be highly relevant to the question. " + context
    
    # Create messages
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
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            top_p=0.9
        )
        
        response = completion.choices[0].message.content.strip()
        
        if not response or len(response) < 3:
            return "Error: Model generated empty response. Please try again."
        
        return response
        
    except Exception as e:
        return f"Error generating response: {str(e)}"

@app.route('/')
def index_page():
    """API-only endpoint - React frontend handles UI"""
    return jsonify({
        'message': 'GST RAG API',
        'status': 'running',
        'endpoints': {
            '/api/query': 'POST - Send queries'
        }
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Handle query requests"""
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Get RAG answer
        answer = rag_answer(query_text)
        
        return jsonify({
            'answer': answer,
            'query': query_text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("="*60)
    print("Loading RAG System...")
    print("="*60)
    load_models()
    print("="*60)
    print("Starting Flask server...")
    print("Open http://localhost:5000 in your browser")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)

