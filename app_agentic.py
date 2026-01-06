from flask import Flask, request, jsonify, session
from flask_cors import CORS
import faiss
import torch
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from datetime import datetime
import re

app = Flask(__name__)
CORS(app) # Enable CORS for all routes
app.secret_key = 'agentic-ai-secret-key-change-in-production'

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

# Global variables
embedder = None
index = None
documents = None
gst_entries = None
client = None
model_name = None
device = None

# Agentic AI Tools/Functions
class AgenticTools:
    """Tools that the AI agent can use autonomously"""
    
    def __init__(self, embedder, index, documents, gst_entries):
        self.embedder = embedder
        self.index = index
        self.documents = documents
        self.gst_entries = gst_entries
        self.device = device
    
    def search_dataset(self, query, top_k=5):
        """Search the GST dataset for relevant entries"""
        q_emb = self.embedder.encode(
            ["query: " + query],
            normalize_embeddings=True,
            device=self.device
        )
        scores, ids = self.index.search(q_emb.astype('float32'), top_k)
        results = []
        for i, idx in enumerate(ids[0]):
            results.append({
                'entry': self.gst_entries[idx],
                'score': float(scores[0][i]),
                'index': int(idx)
            })
        return results
    
    def analyze_multiple_entries(self, query, num_entries=10):
        """Analyze multiple entries to find patterns or comprehensive answers"""
        results = self.search_dataset(query, top_k=num_entries)
        analysis = {
            'total_found': len(results),
            'high_relevance': [r for r in results if r['score'] > 0.5],
            'medium_relevance': [r for r in results if 0.3 < r['score'] <= 0.5],
            'low_relevance': [r for r in results if r['score'] <= 0.3],
            'gst_applicable_count': sum(1 for r in results if r['entry'].get('gst_applicable', False)),
            'gst_exempt_count': sum(1 for r in results if not r['entry'].get('gst_applicable', False)),
            'common_gst_rates': {}
        }
        
        # Count GST rates
        for r in results:
            rate = r['entry'].get('gst_rate', 'NIL')
            analysis['common_gst_rates'][rate] = analysis['common_gst_rates'].get(rate, 0) + 1
        
        return analysis
    
    def compare_entries(self, query1, query2):
        """Compare two different queries to find similarities/differences"""
        results1 = self.search_dataset(query1, top_k=3)
        results2 = self.search_dataset(query2, top_k=3)
        
        comparison = {
            'query1_results': results1,
            'query2_results': results2,
            'similarities': [],
            'differences': []
        }
        
        # Find common GST rates
        rates1 = set(r['entry'].get('gst_rate') for r in results1)
        rates2 = set(r['entry'].get('gst_rate') for r in results2)
        comparison['common_rates'] = list(rates1.intersection(rates2))
        comparison['different_rates'] = list(rates1.symmetric_difference(rates2))
        
        return comparison
    
    def get_category_summary(self, category_keyword):
        """Get summary of all entries related to a specific category"""
        category_entries = []
        for entry in self.gst_entries:
            question = entry.get('question', '').lower()
            answer = entry.get('answer', '').lower()
            if category_keyword.lower() in question or category_keyword.lower() in answer:
                category_entries.append(entry)
        
        summary = {
            'category': category_keyword,
            'total_entries': len(category_entries),
            'gst_applicable': sum(1 for e in category_entries if e.get('gst_applicable', False)),
            'gst_exempt': sum(1 for e in category_entries if not e.get('gst_applicable', False)),
            'entries': category_entries[:10]  # Limit to first 10
        }
        return summary

from pypdf import PdfReader

def extract_pdf_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def chunk_text(text, chunk_size=400, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def load_models():
    """Load all models and data on startup"""
    global embedder, index, documents, gst_entries, client, model_name, device, tools
    
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

    # Load and process PDF if exists
    pdf_path = "new_gst_notification.pdf"
    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        pdf_text = extract_pdf_text(pdf_path)
        if pdf_text:
            pdf_chunks = chunk_text(pdf_text)
            print(f"Created {len(pdf_chunks)} chunks from PDF")
            
            # Add PDF chunks to documents and gst_entries (as virtual entries)
            for i, chunk in enumerate(pdf_chunks):
                documents.append(f"Source: PDF Notification\nContent: {chunk}")
                # Create a virtual entry for agent compatibility
                gst_entries.append({
                    'question': 'Information from New GST Notification',
                    'answer': chunk,
                    'gst_rate': 'Refer to content',
                    'gst_applicable': True,
                    'source': 'PDF'
                })
        else:
            print("PDF found but no text extracted")
    else:
        print(f"PDF not found at {pdf_path}, skipping.")
    
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
    
    # Initialize tools
    global tools
    tools = AgenticTools(embedder, index, documents, gst_entries)
    print("Agentic tools initialized!")
    
    return True

# Initialize tools
tools = None

# ============================================================================
# MEMORY MODULE - Stores user preferences and patterns
# ============================================================================
class MemoryModule:
    """Stores user intent patterns, preferences, and domain focus"""
    
    def __init__(self):
        self.user_profiles = {}  # session_id -> user profile
        self.intent_patterns = {}  # Track common query patterns
        self.domain_focus = {}  # Track domain preferences (healthcare GST vs others)
    
    def get_user_profile(self, session_id):
        """Get or create user profile"""
        if session_id not in self.user_profiles:
            self.user_profiles[session_id] = {
                'explanation_depth': 'medium',  # 'simple', 'medium', 'detailed'
                'domain_focus': 'healthcare',  # 'healthcare', 'general', 'mixed'
                'preferred_format': 'conversational',  # 'conversational', 'formal', 'technical'
                'query_count': 0,
                'common_topics': [],
                'last_queries': []
            }
        return self.user_profiles[session_id]
    
    def update_profile(self, session_id, query, answer, tools_used):
        """Update user profile based on interaction"""
        profile = self.get_user_profile(session_id)
        profile['query_count'] += 1
        profile['last_queries'].append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'tools_used': tools_used
        })
        # Keep only last 10 queries
        if len(profile['last_queries']) > 10:
            profile['last_queries'] = profile['last_queries'][-10:]
        
        # Detect domain focus
        query_lower = query.lower()
        if any(word in query_lower for word in ['cancer', 'diabetes', 'hospital', 'treatment', 'medical', 'healthcare']):
            profile['domain_focus'] = 'healthcare'
        elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
            profile['preferred_format'] = 'comparative'
        
        # Detect explanation depth preference
        if any(word in query_lower for word in ['explain', 'detailed', 'comprehensive', 'full']):
            profile['explanation_depth'] = 'detailed'
        elif any(word in query_lower for word in ['simple', 'brief', 'quick', 'short']):
            profile['explanation_depth'] = 'simple'
        
        # Track common topics
        topics = self._extract_topics(query)
        for topic in topics:
            if topic not in profile['common_topics']:
                profile['common_topics'].append(topic)
    
    def _extract_topics(self, query):
        """Extract topics from query"""
        topics = []
        healthcare_keywords = ['cancer', 'diabetes', 'covid', 'hiv', 'tb', 'asthma', 'heart', 'kidney', 'liver']
        for keyword in healthcare_keywords:
            if keyword in query.lower():
                topics.append(keyword)
        return topics
    
    def get_preferences(self, session_id):
        """Get user preferences for answer generation"""
        profile = self.get_user_profile(session_id)
        return {
            'explanation_depth': profile['explanation_depth'],
            'domain_focus': profile['domain_focus'],
            'preferred_format': profile['preferred_format']
        }

# Initialize memory module
memory = MemoryModule()

# ============================================================================
# REFLECTION LAYER - Confidence scoring, ambiguity detection, follow-ups
# ============================================================================
def reflection_layer(query, answer, tool_results, conversation_history):
    """Reflection layer: Score confidence, detect ambiguity, decide on follow-ups"""
    
    # Calculate confidence score based on tool results
    # Pass answer length and quality for better calculation
    confidence_score = calculate_confidence(tool_results, answer)
    
    # Detect ambiguity in the query
    ambiguity_detected = detect_ambiguity(query, answer, tool_results)
    
    # Decide if follow-up question is needed
    needs_followup = should_ask_followup(query, answer, confidence_score, ambiguity_detected)
    
    # Generate follow-up question if needed
    followup_question = None
    if needs_followup:
        followup_question = generate_followup(query, answer, ambiguity_detected)
    
    return {
        'confidence_score': confidence_score,
        'ambiguity_detected': ambiguity_detected,
        'needs_followup': needs_followup,
        'followup_question': followup_question
    }

def calculate_confidence(tool_results, answer=""):
    """Calculate confidence score (0-1) based on tool results quality and answer completeness.
    Detects out-of-dataset queries and adjusts confidence accordingly."""
    if not tool_results:
        return 0.25  # Lower confidence if no results at all
    
    all_scores = []
    total_results = 0
    high_quality_count = 0
    max_score = 0
    low_relevance_count = 0
    out_of_dataset = False
    
    for result in tool_results:
        if isinstance(result, dict) and 'error' in result:
            continue  # Skip errors
            
        if isinstance(result, list):  # search_dataset results
            if result:
                total_results += len(result)
                # Extract actual relevance scores from FAISS results
                for r in result:
                    score = r.get('score', 0)
                    if score > 0:
                        all_scores.append(score)
                        max_score = max(max_score, score)
                        if score > 0.65:  # High quality threshold
                            high_quality_count += 1
                        elif score < 0.3:  # Very low relevance - likely out of dataset
                            low_relevance_count += 1
            else:
                # Empty result list - query not in dataset
                out_of_dataset = True
        elif isinstance(result, dict):
            # For analyze_multiple_entries, compare_entries, etc.
            high_rel = result.get('high_relevance', [])
            medium_rel = result.get('medium_relevance', [])
            low_rel = result.get('low_relevance', [])
            total_found = result.get('total_found', 0)
            
            if high_rel:
                total_results += len(high_rel)
                for entry in high_rel:
                    entry_score = entry.get('score', 0.7) if isinstance(entry, dict) else 0.7
                    all_scores.append(entry_score)
                    max_score = max(max_score, entry_score)
                    if entry_score > 0.65:
                        high_quality_count += 1
            elif medium_rel:
                total_results += len(medium_rel)
                for entry in medium_rel:
                    entry_score = entry.get('score', 0.45) if isinstance(entry, dict) else 0.45
                    all_scores.append(entry_score)
            elif low_rel:
                total_results += len(low_rel)
                low_relevance_count += len(low_rel)
                for entry in low_rel:
                    entry_score = entry.get('score', 0.25) if isinstance(entry, dict) else 0.25
                    all_scores.append(entry_score)
            elif total_found > 0:
                total_results += total_found
                # Medium quality for general results
                estimated_score = 0.55
                for _ in range(min(total_found, 5)):
                    all_scores.append(estimated_score)
            else:
                # No results found - out of dataset
                out_of_dataset = True
    
    # Detect out-of-dataset query
    # Criteria: All scores are very low (< 0.3) OR no results OR mostly low relevance
    if out_of_dataset or (all_scores and max_score < 0.3):
        # Query is clearly out of dataset - using general knowledge fallback
        # Confidence should be lower (20-40%) since it's not from dataset
        fallback_confidence = 0.30
        
        # Adjust based on answer quality (if answer is good, slightly higher confidence)
        if answer:
            answer_length = len(answer)
            if answer_length > 150 and ('gst' in answer.lower() or 'tax' in answer.lower()):
                # Answer seems relevant even if not in dataset
                fallback_confidence = 0.40
            elif answer_length < 50:
                # Very short answer - lower confidence
                fallback_confidence = 0.20
        
        return round(fallback_confidence, 2)
    
    # If most results are low relevance, query is partially out of dataset
    if low_relevance_count > 0 and low_relevance_count >= total_results * 0.6:
        # More than 60% are low relevance - likely out of dataset
        out_of_dataset = True
    
    if not all_scores:
        return 0.25  # No valid scores
    
    # Calculate confidence based on multiple factors
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    # Factor 1: Average relevance score (0-1) - weighted by max score
    score_factor = (avg_score * 0.7 + max_score * 0.3)
    
    # Factor 2: Proportion of high-quality results
    quality_factor = high_quality_count / total_results if total_results > 0 else 0
    
    # Factor 3: Result count (more results = higher confidence if quality is good)
    # Optimal is 3-5 results, too many might indicate uncertainty
    if total_results >= 3 and total_results <= 5:
        count_factor = 1.0
    elif total_results > 5:
        count_factor = 0.9  # Slightly lower if too many results
    else:
        count_factor = total_results / 3.0  # Scale up to 3 results
    
    # Factor 4: Score distribution (if top results are very high, boost confidence)
    if all_scores:
        top_scores = sorted(all_scores, reverse=True)[:3]
        top_avg = sum(top_scores) / len(top_scores)
        if top_avg > 0.75:
            top_factor = 1.0
        elif top_avg > 0.6:
            top_factor = 0.85
        elif top_avg > 0.45:
            top_factor = 0.7
        else:
            top_factor = 0.5
    else:
        top_factor = 0.5
    
    # Factor 5: Answer completeness (longer, structured answers = higher confidence)
    answer_factor = 1.0
    if answer:
        answer_length = len(answer)
        if answer_length > 200:  # Comprehensive answer
            answer_factor = 1.0
        elif answer_length > 100:  # Good answer
            answer_factor = 0.9
        elif answer_length > 50:  # Basic answer
            answer_factor = 0.75
        else:  # Very short answer
            answer_factor = 0.6
        
        # Bonus if answer has structure (bullet points, lists)
        if '-' in answer or '•' in answer or any(str(i) + '.' in answer for i in range(1, 10)):
            answer_factor = min(1.0, answer_factor + 0.1)
    
    # Factor 6: Dataset relevance penalty (if query is partially out of dataset)
    dataset_relevance_factor = 1.0
    if low_relevance_count > 0:
        # Penalize if many low-relevance results
        low_relevance_ratio = low_relevance_count / total_results if total_results > 0 else 0
        dataset_relevance_factor = 1.0 - (low_relevance_ratio * 0.3)  # Up to 30% penalty
    
    # Weighted combination - more dynamic
    confidence = (
        score_factor * 0.35 +      # 35% weight on average/max score
        quality_factor * 0.25 +     # 25% weight on quality proportion
        count_factor * 0.15 +       # 15% weight on result count
        top_factor * 0.15 +         # 15% weight on top results
        answer_factor * 0.10         # 10% weight on answer completeness
    ) * dataset_relevance_factor  # Apply dataset relevance penalty
    
    # Round to 2 decimal places for cleaner display
    confidence = round(confidence, 2)
    
    return min(1.0, max(0.0, confidence))

def detect_ambiguity(query, answer, tool_results):
    """Detect if query or answer has ambiguity"""
    ambiguity_indicators = []
    
    # Check query for ambiguous terms
    ambiguous_words = ['maybe', 'might', 'could', 'possibly', 'perhaps', 'sometimes', 'depends']
    if any(word in query.lower() for word in ambiguous_words):
        ambiguity_indicators.append("Query contains ambiguous language")
    
    # Check answer for uncertainty
    if any(word in answer.lower() for word in ['depends', 'may vary', 'could be', 'might be', 'uncertain']):
        ambiguity_indicators.append("Answer contains uncertainty")
    
    # Check if multiple conflicting results
    if tool_results:
        gst_applicable = []
        for result in tool_results:
            if isinstance(result, list):
                for r in result:
                    entry = r.get('entry', {})
                    if entry.get('gst_applicable') is not None:
                        gst_applicable.append(entry.get('gst_applicable'))
        
        if gst_applicable and len(set(gst_applicable)) > 1:
            ambiguity_indicators.append("Conflicting information found in dataset")
    
    return {
        'is_ambiguous': len(ambiguity_indicators) > 0,
        'indicators': ambiguity_indicators
    }

def should_ask_followup(query, answer, confidence_score, ambiguity_detected):
    """Decide if a follow-up question should be asked"""
    # Ask follow-up if:
    # 1. Confidence is low (< 0.6)
    # 2. Ambiguity is detected
    # 3. Answer is too short or generic
    
    if confidence_score < 0.6:
        return True
    
    if ambiguity_detected.get('is_ambiguous', False):
        return True
    
    if len(answer) < 50:  # Very short answer might need clarification
        return True
    
    return False

def generate_followup(query, answer, ambiguity_detected):
    """Generate a helpful follow-up question"""
    followup_prompt = f"""Based on this interaction:

User Query: {query}
Answer Given: {answer}
Ambiguity Issues: {ambiguity_detected.get('indicators', [])}

Generate a helpful follow-up question that would clarify the user's intent or provide more specific information. 
The question should be:
1. Natural and conversational
2. Helpful for getting better information
3. Not repetitive of the original query

Respond with ONLY the follow-up question, nothing else."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": followup_prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return None

# ============================================================================
# MULTI-STEP EXECUTION LOOP - Execute → Evaluate → Re-plan → Re-execute
# ============================================================================
def multi_step_execution_loop(query, conversation_history, user_preferences, max_iterations=3):
    """Multi-step execution: Execute → Evaluate → Re-plan → Re-execute"""
    
    iteration = 0
    all_tool_results = []
    all_plans = []
    previous_answer = None
    
    while iteration < max_iterations:
        iteration += 1
        print(f"[AGENT] Iteration {iteration}/{max_iterations}")
        
        # Step 1: Planning (or re-planning)
        if iteration == 1:
            plan = agentic_plan(query, conversation_history)
        else:
            # Re-plan based on previous results
            plan = re_plan(query, conversation_history, all_tool_results, previous_answer)
        
        all_plans.append(plan)
        print(f"[AGENT] Plan {iteration}: {plan.get('reasoning', 'N/A')}")
        
        # Step 2: Execute tools
        tool_results = []
        for step in plan.get('steps', []):
            tool_name = step.get('tool')
            parameters = step.get('parameters', {})
            print(f"[AGENT] Executing tool: {tool_name}")
            result = execute_tool(tool_name, parameters)
            tool_results.append(result)
        
        all_tool_results.extend(tool_results)
        
        # Step 3: Evaluate results
        evaluation = evaluate_results(tool_results, query, user_preferences)
        print(f"[AGENT] Evaluation: {evaluation.get('satisfactory', False)} - {evaluation.get('reason', 'N/A')}")
        
        # Step 4: Generate answer
        previous_answer = agentic_answer(query, conversation_history, all_tool_results, user_preferences)
        
        # Step 5: Check if we should continue
        if evaluation.get('satisfactory', False):
            print(f"[AGENT] Results satisfactory after {iteration} iteration(s)")
            break
        
        if iteration >= max_iterations:
            print(f"[AGENT] Reached max iterations ({max_iterations})")
            break
    
    return {
        'answer': previous_answer,
        'plans': all_plans,
        'iterations': iteration,
        'all_tool_results': all_tool_results
    }

def re_plan(query, conversation_history, previous_results, previous_answer):
    """Re-plan based on previous execution results"""
    
    # Analyze what was missing or unsatisfactory
    results_summary = summarize_results(previous_results)
    
    re_planning_prompt = f"""Previous attempt to answer this query was not fully satisfactory.

Original Query: {query}
Previous Answer: {previous_answer}
Previous Results Summary: {results_summary}

Create a NEW plan to improve the answer. Consider:
1. What information was missing?
2. What tools should be used differently?
3. What additional analysis is needed?

Respond with JSON plan:
{{
    "reasoning": "Why the new approach will be better",
    "steps": [
        {{"tool": "tool_name", "parameters": {{"param": "value"}}, "reason": "why"}}
    ],
    "expected_outcome": "What you expect to learn"
}}"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": re_planning_prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        plan_text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Re-planning error: {e}")
    
    # Fallback: try different tools
    return {
        "reasoning": "Trying alternative approach with different tools",
        "steps": [{"tool": "analyze_multiple_entries", "parameters": {"query": query, "num_entries": 15}, "reason": "Get more comprehensive analysis"}],
        "expected_outcome": "More complete information"
    }

def evaluate_results(tool_results, query, user_preferences):
    """Evaluate if tool results are satisfactory"""
    if not tool_results:
        return {'satisfactory': False, 'reason': 'No results obtained'}
    
    # Check if we have high-quality results
    has_high_quality = False
    for result in tool_results:
        if isinstance(result, list):
            for r in result:
                if r.get('score', 0) > 0.5:
                    has_high_quality = True
                    break
    
    # Check if results match user's explanation depth preference
    depth = user_preferences.get('explanation_depth', 'medium')
    result_count = sum(len(r) if isinstance(r, list) else 1 for r in tool_results)
    
    if depth == 'detailed' and result_count < 5:
        return {'satisfactory': False, 'reason': 'Need more results for detailed explanation'}
    
    if not has_high_quality and result_count < 3:
        return {'satisfactory': False, 'reason': 'Low quality or insufficient results'}
    
    return {'satisfactory': True, 'reason': 'Results meet quality threshold'}

def summarize_results(results):
    """Summarize tool results for re-planning"""
    summary = []
    for i, result in enumerate(results):
        if isinstance(result, list):
            summary.append(f"Result {i+1}: Found {len(result)} entries")
        elif isinstance(result, dict):
            if 'total_found' in result:
                summary.append(f"Result {i+1}: Analysis found {result['total_found']} entries")
            else:
                summary.append(f"Result {i+1}: Analysis completed")
    return "\n".join(summary)

def format_answer(answer):
    """Post-process answer to ensure proper formatting with bullet points and structure"""
    if not answer:
        return answer
    
    lines = answer.split('\n')
    formatted_lines = []
    in_list = False
    list_type = None  # 'bullet' or 'numbered'
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if in_list:
                formatted_lines.append('')  # End list with blank line
                in_list = False
                list_type = None
            continue
        
        # Check for bullet points
        if re.match(r'^[-•]\s+', line):
            if not in_list or list_type != 'bullet':
                if in_list:
                    formatted_lines.append('')
                formatted_lines.append(line)
                in_list = True
                list_type = 'bullet'
            else:
                formatted_lines.append(line)
        # Check for numbered lists
        elif re.match(r'^\d+\.\s+', line):
            if not in_list or list_type != 'numbered':
                if in_list:
                    formatted_lines.append('')
                formatted_lines.append(line)
                in_list = True
                list_type = 'numbered'
            else:
                formatted_lines.append(line)
        # Regular text
        else:
            if in_list:
                formatted_lines.append('')  # End list
                in_list = False
                list_type = None
            
            # Ensure important terms are bold
            if any(word in line.lower() for word in ['gst', 'rate', 'applicable', 'exempt', 'nil', '%']):
                # Add bold to GST rates
                line = re.sub(r'(\d+%)', r'**\1**', line)
                line = re.sub(r'(GST\s+rate[:\s]+)([^\n]+)', r'\1**\2**', line, flags=re.IGNORECASE)
            
            formatted_lines.append(line)
    
    # Join with proper spacing
    result = '\n\n'.join([line for line in formatted_lines if line.strip()])
    
    # Ensure minimum structure: if no bullets, add them for key points
    if '-' not in result and '•' not in result and len(result) > 100:
        # Try to convert to bullet points
        sentences = result.split('. ')
        if len(sentences) > 3:
            # Convert first few sentences to bullets
            key_points = sentences[:3]
            rest = '. '.join(sentences[3:])
            result = '- ' + '\n- '.join([s.strip() for s in key_points if s.strip()]) + '\n\n' + rest
    
    return result

def agentic_plan(query, conversation_history):
    """Agentic planning phase - decides what tools to use and how to approach the query"""
    
    planning_prompt = f"""You are an intelligent AI agent that needs to answer GST-related questions. 

Available Tools:
1. search_dataset(query, top_k) - Search for specific entries in the GST dataset
2. analyze_multiple_entries(query, num_entries) - Analyze multiple entries to find patterns
3. compare_entries(query1, query2) - Compare two different queries
4. get_category_summary(category) - Get summary of entries in a category

Conversation History:
{conversation_history}

Current Query: {query}

Create a PLAN to answer this query. Your plan should:
1. Determine if this is a simple question (use search_dataset) or complex (use analyze_multiple_entries)
2. Identify if comparison is needed
3. Decide if category analysis would help
4. Plan the sequence of tool calls

Respond ONLY with a JSON plan in this format:
{{
    "reasoning": "Why you chose this approach",
    "steps": [
        {{"tool": "tool_name", "parameters": {{"param": "value"}}, "reason": "why"}},
        ...
    ],
    "expected_outcome": "What you expect to learn"
}}

Be concise and strategic."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        plan_text = response.choices[0].message.content.strip()
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group())
            return plan
        else:
            # Fallback plan
            return {
                "reasoning": "Using default search approach",
                "steps": [{"tool": "search_dataset", "parameters": {"query": query, "top_k": 5}, "reason": "Direct search"}],
                "expected_outcome": "Find relevant GST entries"
            }
    except Exception as e:
        print(f"Planning error: {e}")
        return {
            "reasoning": "Fallback to simple search",
            "steps": [{"tool": "search_dataset", "parameters": {"query": query, "top_k": 5}, "reason": "Direct search"}],
            "expected_outcome": "Find relevant GST entries"
        }

def execute_tool(tool_name, parameters):
    """Execute a tool call"""
    global tools
    
    try:
        if tool_name == "search_dataset":
            return tools.search_dataset(**parameters)
        elif tool_name == "analyze_multiple_entries":
            return tools.analyze_multiple_entries(**parameters)
        elif tool_name == "compare_entries":
            return tools.compare_entries(**parameters)
        elif tool_name == "get_category_summary":
            return tools.get_category_summary(**parameters)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}

def agentic_answer(query, conversation_history, tool_results, user_preferences=None):
    """Generate final answer using tool results and agentic reasoning"""
    
    if user_preferences is None:
        user_preferences = {'explanation_depth': 'medium', 'preferred_format': 'conversational'}
    
    # Format tool results for context
    context_parts = []
    for i, result in enumerate(tool_results):
        if isinstance(result, dict) and 'error' not in result:
            if isinstance(result, list):  # search_dataset returns list
                context_parts.append(f"Search Results {i+1}:\n" + 
                    "\n\n".join([f"Entry: {r['entry']['question']}\nAnswer: {r['entry']['answer']}\nGST Rate: {r['entry']['gst_rate']}\nRelevance: {r['score']:.3f}" 
                                for r in result[:3]]))
            else:  # Other tools return dict
                context_parts.append(f"Analysis {i+1}:\n{json.dumps(result, indent=2)}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Adjust answer style based on user preferences
    depth_instruction = {
        'simple': "Provide a brief, concise answer with 2-3 key bullet points.",
        'medium': "Provide a clear, well-explained answer with structured bullet points and sections.",
        'detailed': "Provide a comprehensive, detailed answer with bullet points, numbered lists, examples, and clear sections."
    }.get(user_preferences.get('explanation_depth', 'medium'), "Provide a clear answer with bullet points.")
    
    format_instruction = {
        'conversational': "Write in a friendly, conversational tone. Use bullet points and clear structure.",
        'formal': "Write in a formal, professional tone. Use structured formatting with bullet points.",
        'technical': "Write in a technical, precise tone. Use bullet points and numbered lists for clarity."
    }.get(user_preferences.get('preferred_format', 'conversational'), "Write conversationally with bullet points.")
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an intelligent, agentic AI assistant specialized in GST (Goods and Services Tax) questions. "
                "You have access to a comprehensive GST dataset and can use various tools to find information.\n\n"
                "Your capabilities:\n"
                "1. You can search and analyze the GST dataset autonomously\n"
                "2. You can reason about complex questions by breaking them into steps\n"
                "3. You can compare different scenarios and find patterns\n"
                "4. You provide human-like, conversational answers\n\n"
                "IMPORTANT - Answer Formatting:\n"
                "- Use bullet points (- or •) for lists and key points\n"
                "- Use numbered lists (1., 2., 3.) for step-by-step explanations\n"
                "- Use **bold** for important terms and GST rates\n"
                "- Break answers into clear sections with line breaks\n"
                "- Structure your answer: Brief summary, then detailed points, then conclusion\n"
                "- Make it scannable and easy to read\n\n"
                "When answering:\n"
                "- Use the tool results provided to give accurate, data-driven answers\n"
                "- If the data shows clear patterns, explain them naturally with bullet points\n"
                "- If information is incomplete, acknowledge it and provide what you can\n"
                "- Be conversational and helpful, as if explaining to a friend\n"
                "- Reference specific details from the dataset when relevant\n"
                "- Always format with proper structure, bullet points, and clear sections"
            )
        },
        {
            "role": "user",
            "content": f"""Conversation History:
{conversation_history}

Current Question: {query}

Tool Results and Analysis:
{context}

User Preferences:
- Explanation Depth: {user_preferences.get('explanation_depth', 'medium')}
- Preferred Format: {user_preferences.get('preferred_format', 'conversational')}

Instructions:
{depth_instruction}
{format_instruction}

Based on the tool results above, provide a well-structured answer that matches the user's preferences. 

CRITICAL FORMATTING REQUIREMENTS:
- Use bullet points (- or •) for lists, key points, and important information
- Use numbered lists (1., 2., 3.) for step-by-step explanations or sequences
- Use **bold** for GST rates, important terms, and key concepts
- Break your answer into clear sections with line breaks
- Structure: Brief summary → Detailed points (bullets) → Conclusion
- Make it scannable, readable, and professional

Use the data to support your answer, format it clearly with bullet points, and explain your reasoning in a structured way."""
        }
    ]
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=400,
            top_p=0.9
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Post-process to ensure proper formatting with bullet points
        response = format_answer(response)
        
        return response
    except Exception as e:
        return f"Error generating response: {str(e)}"

def agentic_rag(query, conversation_history="", session_id=None):
    """Main agentic RAG function with full agentic capabilities"""
    
    # Get user preferences from memory
    if session_id:
        user_preferences = memory.get_preferences(session_id)
    else:
        user_preferences = {'explanation_depth': 'medium', 'preferred_format': 'conversational'}
    
    # MULTI-STEP EXECUTION LOOP
    print(f"[AGENT] Starting multi-step execution for: {query}")
    execution_result = multi_step_execution_loop(query, conversation_history, user_preferences, max_iterations=3)
    
    answer = execution_result['answer']
    all_plans = execution_result['plans']
    iterations = execution_result['iterations']
    all_tool_results = execution_result['all_tool_results']
    
    # REFLECTION LAYER
    print(f"[AGENT] Running reflection layer...")
    reflection = reflection_layer(query, answer, all_tool_results, conversation_history)
    
    # Update memory with this interaction
    if session_id:
        tools_used = [step.get('tool') for plan in all_plans for step in plan.get('steps', [])]
        memory.update_profile(session_id, query, answer, tools_used)
    
    return {
        'answer': answer,
        'plan': all_plans[-1] if all_plans else {},
        'plans': all_plans,  # All plans from iterations
        'tools_used': [step.get('tool') for plan in all_plans for step in plan.get('steps', [])],
        'iterations': iterations,
        'reflection': reflection,
        'user_preferences': user_preferences
    }

@app.route('/')
def index_page():
    """API-only endpoint - React frontend handles UI"""
    return jsonify({
        'message': 'Agentic GST AI API',
        'status': 'running',
        'endpoints': {
            '/api/query': 'POST - Send queries',
            '/api/clear': 'POST - Clear history',
            '/api/upload': 'POST - Upload PDF files'
        }
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Handle query requests with agentic AI"""
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Get conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        conversation_history = "\n".join([
            f"User: {h['user']}\nAssistant: {h['assistant']}" 
            for h in session['conversation_history'][-5:]  # Last 5 exchanges
        ])
        
        # Get session ID for memory
        session_id = session.get('session_id', None)
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"
            session['session_id'] = session_id
        
        # Get agentic answer with full capabilities
        result = agentic_rag(query_text, conversation_history, session_id)
        
        # Update conversation history
        session['conversation_history'].append({
            'user': query_text,
            'assistant': result['answer'],
            'timestamp': datetime.now().isoformat()
        })
        session.modified = True
        
        # Prepare response with reflection and memory info
        response_data = {
            'answer': result['answer'],
            'query': query_text,
            'tools_used': result.get('tools_used', []),
            'planning': result.get('plan', {}).get('reasoning', ''),
            'iterations': result.get('iterations', 1),
            'confidence_score': result.get('reflection', {}).get('confidence_score', 0.5),
            'needs_followup': result.get('reflection', {}).get('needs_followup', False),
            'followup_question': result.get('reflection', {}).get('followup_question'),
            'user_preferences': result.get('user_preferences', {})
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Handle user feedback on responses"""
    try:
        data = request.json
        message_id = data.get('message_id')
        feedback_type = data.get('feedback_type')  # 'positive' or 'negative'
        message_text = data.get('message_text', '')
        query = data.get('query', '')
        tools_used = data.get('tools_used', [])
        
        # Store feedback (in production, save to database)
        feedback_data = {
            'message_id': message_id,
            'feedback_type': feedback_type,
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'message_text': message_text[:200],  # Truncate for storage
            'tools_used': tools_used
        }
        
        # In production, save to database
        # For now, just log it
        print(f"[FEEDBACK] {feedback_type.upper()}: Message {message_id}")
        print(f"  Query: {query[:100]}")
        print(f"  Tools: {', '.join(tools_used)}")
        
        # Update memory based on feedback
        session_id = session.get('session_id', 'default')
        if feedback_type == 'negative':
            # Negative feedback - might indicate preference mismatch
            # Could trigger learning/adjustment in future
            pass
        elif feedback_type == 'positive':
            # Positive feedback - reinforce current approach
            # Could update preferences to match what worked
            pass
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded',
            'feedback_type': feedback_type
        })
    except Exception as e:
        print(f"Feedback error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear conversation history and reset memory"""
    session['conversation_history'] = []
    
    # Reset memory module for this session
    session_id = session.get('session_id', 'default')
    if session_id in memory.user_profiles:
        # Reset user profile to defaults
        memory.user_profiles[session_id] = {
            'explanation_depth': 'medium',
            'domain_focus': 'healthcare',
            'preferred_format': 'conversational',
            'query_count': 0,
            'common_topics': [],
            'last_queries': []
        }
    
    return jsonify({'status': 'cleared', 'message': 'Conversation history and memory cleared'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF file uploads and index them immediately"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.pdf'):
        try:
            # Save file
            filename = file.filename
            file.save(filename)
            print(f"File saved: {filename}")
            
            # Process PDF immediately
            pdf_text = extract_pdf_text(filename)
            if pdf_text:
                pdf_chunks = chunk_text(pdf_text)
                
                # Update FAISS index
                new_embeddings = embedder.encode(
                    ["passage: Source: PDF Notification\nContent: " + c for c in pdf_chunks],
                    normalize_embeddings=True
                )
                index.add(new_embeddings.astype('float32'))
                
                # Update documents and entries
                for chunk in pdf_chunks:
                    documents.append(f"Source: PDF Notification ({filename})\nContent: {chunk}")
                    gst_entries.append({
                        'question': f'Information from {filename}',
                        'answer': chunk,
                        'gst_rate': 'Refer to content',
                        'gst_applicable': True,
                        'source': 'PDF'
                    })
                
                return jsonify({'message': f'Successfully uploaded and indexed {len(pdf_chunks)} chunks from {filename}'})
            else:
                return jsonify({'error': 'Could not extract text from PDF'}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invalid file type. Only PDF allowed.'}), 400

if __name__ == '__main__':
    print("="*60)
    print("Loading Agentic AI RAG System...")
    print("="*60)
    load_models()
    print("="*60)
    print("Starting Flask server...")
    print("Open http://localhost:5000 in your browser")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)

