# 🤖 Agentic GST AI Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Agentic%20AI-Enabled-blueviolet?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/RAG-FAISS%20%2B%20E5-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/LLM-Qwen2.5--7B-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Tailwind-06b6d4?style=for-the-badge"/>
</p>

<p align="center">
  <b>A dataset-aware Agentic AI system for answering GST (Goods and Services Tax) questions using Retrieval-Augmented Generation.</b>
</p>

---

## ✨ What makes this project different?

Unlike traditional chatbots or basic RAG systems, this project is designed to behave like a **responsible Agentic AI**:

- ✅ Plans before answering  
- ✅ Uses tools autonomously  
- ✅ Reflects on answer quality  
- ✅ Adjusts confidence dynamically  
- ✅ Detects dataset limitations instead of hallucinating  

> **Accuracy and transparency are prioritized over blind confidence.**

---

## 🧠 Core Capabilities

- 📚 **GST Question Answering** using a structured dataset
- 🔍 **Vector Search** with FAISS + E5 embeddings
- 🧭 **Autonomous Planning** to decide how to answer
- 🔧 **Tool-based Reasoning** (search, analyze, compare, summarize)
- 🔄 **Multi-step Execution Loop** (Execute → Evaluate → Re-plan)
- 📊 **Confidence Scoring** based on dataset relevance
- 📎 **PDF Upload & Indexing** for dynamic knowledge expansion
- 💬 **Modern Chat UI** with confidence visualization

---

## 🏗️ Agentic Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  - Modern UI with Tailwind CSS                               │
│  - Real-time chat interface                                  │
│  - Agentic info display                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼─────────────────────────────────────┐
│                  Flask Backend (Python)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Agentic AI Orchestrator                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │  │
│  │  │ Planning  │→ │  Tools   │→ │ Reflection│           │  │
│  │  └──────────┘  └──────────┘  └──────────┘           │  │
│  │       ↓              ↓              ↓                  │  │
│  │  ┌──────────────────────────────────────┐            │  │
│  │  │    Multi-Step Execution Loop           │            │  │
│  │  │  Execute → Evaluate → Re-plan          │            │  │
│  │  └──────────────────────────────────────┘            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              RAG System                                 │  │
│  │  Query → E5 Embedding → FAISS Search → Top-k Results   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Memory Module                               │  │
│  │  User Preferences | Query Patterns | Domain Focus      │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│  FAISS Index │ │  E5 Model   │ │ HuggingFace │
│  (Vector DB) │ │ (Embeddings)│ │    API      │
└──────────────┘ └─────────────┘ └─────────────┘
```


---

## 🚀 Technology Stack

### 🧩 Backend
- 🐍 **Python (Flask)**
- 📦 **FAISS** – Vector database
- 🧠 **SentenceTransformers (E5-base-v2)**
- 🤖 **Qwen2.5-7B-Instruct** (via HuggingFace)
- 📄 **PyPDF** – PDF text extraction
- 🔢 **NumPy, Torch**

### 🎨 Frontend
- ⚛️ **React (Vite)**
- 🎨 **Tailwind CSS**
- 🧩 **Lucide Icons**

---
## 📁 Project Structure

```
agentic_ai/
├── app_agentic.py          # Main Flask backend with agentic AI
├── app.py                  # Simple RAG version (legacy)
├── ai_bot.py               # Initial RAG implementation
├── requirements.txt        # Python dependencies
├── dataset/
│   └── dataset.txt         # GST Q&A dataset (JSON)
├── frontend/
│   ├── src/
│   │   ├── GSTChatbot.jsx  # Main chat component
│   │   ├── App.jsx         # React app entry
│   │   └── main.jsx        # React DOM renderer
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
├── AGENTIC_FEATURES.md     # Detailed agentic features doc
└── README.md               # This file
```

## 🛠️ Technologies Used

### Backend
- **Flask**: Web framework
- **FAISS**: Vector similarity search
- **Sentence Transformers**: E5 embedding model
- **OpenAI Client**: HuggingFace API integration
- **PyPDF**: PDF text extraction
- **NumPy**: Numerical operations
- **Torch**: Deep learning framework

### Frontend
- **React 19**: UI framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Styling
- **Lucide React**: Icons

### AI/ML
- **E5-base-v2**: Embedding model (768 dimensions)
- **Qwen2.5-7B-Instruct**: LLM via HuggingFace API
- **FAISS**: Vector database for similarity search

## ⚙️ Configuration

Before running the application, make sure to set up your environment variables. See the [Security Notes](#-security-notes) section for details on configuring the `.env` file.

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Model loading fails
- **Solution**: Check HuggingFace token is valid
- **Solution**: Ensure internet connection for model download

**Problem**: FAISS index not found
- **Solution**: Delete `faiss_index.bin` and restart (will rebuild)

**Problem**: Out of memory
- **Solution**: Use CPU instead of GPU, or reduce batch size

### Frontend Issues

**Problem**: CORS errors
- **Solution**: Ensure `flask-cors` is installed and CORS is enabled

**Problem**: API connection fails
- **Solution**: Verify backend is running on port 5000
- **Solution**: Check browser console for errors

### General Issues

**Problem**: Low confidence scores
- **Normal**: Out-of-dataset queries will have lower confidence (20-40%)
- **Check**: Verify dataset has relevant entries

**Problem**: Answers not structured
- **Solution**: Check LLM is generating formatted responses
- **Solution**: Verify system prompts include formatting instructions

## 📊 Performance Benchmark

- **Embedding Generation (E5-base-v2)**: ~50ms per query
- **FAISS Search**: <10ms for top-5 results
- **LLM Response**: 2-5 seconds (depends on API)
- **Total Response Time**: 3-6 seconds typically

## 🔒 Security Notes

- **HuggingFace Token**: Use environment variables (`.env` file) - never commit tokens to git
- **Session Secret**: Change `app.secret_key` in `app_agentic.py` for production
- **CORS**: Currently enabled for all origins (restrict for production)
- **Environment Variables**: Copy `.env.example` to `.env` and add your credentials

## 📝 Project License

This project is for educational/demonstration purposes.

## 🤝 How to Contribute

Feel free to submit issues or pull requests!

## 📧 Support

For issues or questions, please open an issue on the repository.

---

**Built with ❤️ using Agentic AI principles**
