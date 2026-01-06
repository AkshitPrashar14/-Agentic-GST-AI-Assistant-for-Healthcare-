# Complete Agentic AI Features

This document details all the agentic AI features implemented in the system.

## ✅ Implemented Features

### 1. Reflection Layer (MANDATORY) ⭐

**Location**: `reflection_layer()` function in `app_agentic.py`

**What it does:**
- **Confidence Scoring**: Calculates confidence (0-1) based on tool result quality
- **Ambiguity Detection**: Identifies ambiguous queries or conflicting information
- **Follow-up Decision**: Determines if clarification is needed
- **Follow-up Generation**: Creates helpful follow-up questions

**How it works:**
```python
reflection = reflection_layer(query, answer, tool_results, conversation_history)
# Returns:
# {
#     'confidence_score': 0.75,
#     'ambiguity_detected': {'is_ambiguous': False, 'indicators': []},
#     'needs_followup': False,
#     'followup_question': None
# }
```

**Confidence Calculation:**
- Based on relevance scores from search results
- Considers number of high-quality results
- Factors in result completeness

**Ambiguity Detection:**
- Checks for ambiguous words in query ("maybe", "depends", etc.)
- Detects uncertainty in answers
- Identifies conflicting information in dataset

**Follow-up Generation:**
- Only triggers when confidence < 0.6 or ambiguity detected
- Uses LLM to generate natural follow-up questions
- Helps clarify user intent

---

### 2. Memory Module 💾

**Location**: `MemoryModule` class in `app_agentic.py`

**What it stores:**

#### User Intent Patterns
- Common topics (cancer, diabetes, COVID, etc.)
- Query types (simple, comparison, category analysis)
- Frequency of different question types

#### Preferred Explanation Depth
- **Simple**: Brief, concise answers
- **Medium**: Clear, well-explained answers (default)
- **Detailed**: Comprehensive answers with examples

**How it learns:**
- Detects keywords: "explain", "detailed" → detailed preference
- Detects keywords: "simple", "brief" → simple preference
- Updates based on user queries over time

#### Domain Focus
- **Healthcare**: Focus on medical services GST
- **General**: General GST questions
- **Mixed**: Combination of both

**How it detects:**
- Analyzes query for healthcare keywords
- Tracks most common domain in user's queries
- Adapts responses accordingly

**Storage:**
```python
user_profile = {
    'explanation_depth': 'detailed',  # Learned preference
    'domain_focus': 'healthcare',     # Detected from queries
    'preferred_format': 'conversational',
    'query_count': 15,
    'common_topics': ['cancer', 'diabetes', 'hospital'],
    'last_queries': [...]  # Last 10 queries
}
```

---

### 3. Multi-Step Execution Loop 🔄

**Location**: `multi_step_execution_loop()` function in `app_agentic.py`

**The Loop:**
```
Iteration 1:
  Execute → Evaluate → [If unsatisfactory] → Re-plan

Iteration 2:
  Execute → Evaluate → [If unsatisfactory] → Re-plan

Iteration 3:
  Execute → Evaluate → [Final answer]
```

**Components:**

#### Execute Phase
- Runs planned tools
- Collects results
- Tracks execution

#### Evaluate Phase
- Checks result quality
- Verifies if results match user preferences
- Determines if more information needed

**Evaluation Criteria:**
- High-quality results (relevance > 0.5)
- Sufficient result count
- Matches user's explanation depth preference

#### Re-plan Phase
- Analyzes what was missing
- Creates new strategy
- Selects different/additional tools

**Re-planning Logic:**
- If low quality: Try `analyze_multiple_entries` with more entries
- If insufficient: Add more tool calls
- If wrong approach: Change tool selection

#### Re-execute Phase
- Runs new plan
- Combines with previous results
- Iterates until satisfactory or max iterations

**Max Iterations**: 3 (configurable)

**Example:**
```
Query: "Compare cancer and diabetes GST rules"

Iteration 1:
  Plan: search_dataset for both
  Execute: Found 3 cancer, 2 diabetes entries
  Evaluate: Not enough for comparison ❌
  Re-plan: Use compare_entries + analyze_multiple_entries

Iteration 2:
  Plan: compare_entries + analyze_multiple_entries
  Execute: Comprehensive comparison data
  Evaluate: Satisfactory ✓
  Final Answer: Generated
```

---

## 🔄 Complete Agentic Workflow

```
1. User Query
   ↓
2. Memory Module
   - Load user preferences
   - Check query patterns
   - Get explanation depth preference
   ↓
3. Planning Phase
   - Analyze query complexity
   - Create initial plan
   - Select tools
   ↓
4. Multi-Step Execution Loop
   ├─ Iteration 1: Execute → Evaluate
   ├─ If unsatisfactory: Re-plan
   ├─ Iteration 2: Execute → Evaluate
   ├─ If unsatisfactory: Re-plan
   └─ Iteration 3: Execute → Evaluate → Final
   ↓
5. Answer Generation
   - Use all collected results
   - Match user preferences
   - Generate natural answer
   ↓
6. Reflection Layer
   - Score confidence
   - Detect ambiguity
   - Generate follow-up if needed
   ↓
7. Memory Update
   - Store query pattern
   - Update preferences
   - Track domain focus
   ↓
8. Return Response
   - Answer
   - Confidence score
   - Follow-up question (if needed)
   - Agentic metadata
```

---

## 📊 Response Format

The API now returns:

```json
{
    "answer": "The answer text...",
    "query": "User's question",
    "tools_used": ["search_dataset", "analyze_multiple_entries"],
    "planning": "Reasoning for approach",
    "iterations": 2,
    "confidence_score": 0.85,
    "needs_followup": false,
    "followup_question": null,
    "user_preferences": {
        "explanation_depth": "detailed",
        "preferred_format": "conversational",
        "domain_focus": "healthcare"
    }
}
```

---

## 🎯 Key Differences from Regular RAG

| Feature | Regular RAG | Agentic AI (Now) |
|---------|------------|------------------|
| **Planning** | ❌ Fixed | ✅ Dynamic, adaptive |
| **Execution** | ❌ Single pass | ✅ Multi-step loop |
| **Evaluation** | ❌ None | ✅ After each iteration |
| **Re-planning** | ❌ No | ✅ Yes, based on results |
| **Reflection** | ❌ No | ✅ Confidence + ambiguity |
| **Follow-ups** | ❌ No | ✅ Auto-generated |
| **Memory** | ❌ Session only | ✅ User profiles + patterns |
| **Adaptation** | ❌ Static | ✅ Learns preferences |

---

## 🚀 Usage

The agentic features are **automatically enabled** when using `app_agentic.py`. No configuration needed!

Just run:
```bash
python app_agentic.py
```

The system will:
1. ✅ Plan each query
2. ✅ Execute multi-step loops
3. ✅ Reflect on answers
4. ✅ Learn user preferences
5. ✅ Generate follow-ups when needed

---

## 📝 Notes

- **Reflection Layer** is mandatory and runs after every answer
- **Memory Module** persists across sessions (session-based)
- **Multi-Step Loop** runs up to 3 iterations (configurable)
- All features work together seamlessly
- UI displays all agentic metadata

---

## 🔍 Debugging

Check console output for:
- `[AGENT] Planning approach...`
- `[AGENT] Iteration X/Y`
- `[AGENT] Evaluation: satisfactory/unsatisfactory`
- `[AGENT] Running reflection layer...`
- `[AGENT] Confidence score: X`

This shows the complete agentic decision-making process!

