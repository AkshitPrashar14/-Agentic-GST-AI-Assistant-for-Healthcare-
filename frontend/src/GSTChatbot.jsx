import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  MessageSquare,
  Settings,
  Moon,
  Sun,
  Menu,
  X,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Paperclip,
  Mic,
} from "lucide-react";

export default function GSTChatbot() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      text: "Hello! I'm your GST AI Assistant. I can help you with GST-related queries, analyze datasets, and provide detailed information. How can I assist you today?",
      timestamp: new Date(),
      tools: [],
      planning: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [expandedAgentInfo, setExpandedAgentInfo] = useState({});
  const [messageFeedback, setMessageFeedback] = useState({}); // Track feedback for each message
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null); // Ref for file input

  const quickSuggestions = [
    "What is GST?",
    "Compare GST rates",
    "Analyze healthcare services",
    "Search for education services",
  ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
    }
  }, [input]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Please upload a PDF file.");
      return;
    }

    // Add user message about upload
    const userMessage = {
      id: messages.length + 1,
      type: "user",
      text: `Uploaded file: ${file.name}`,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:5000/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Upload failed");
      }

      const botMessage = {
        id: messages.length + 2,
        type: "bot",
        text: `Successfully processed ${file.name}! ${data.message}`,
        timestamp: new Date(),
        tools: ["pdf_processor", "faiss_indexer"],
        planning: `Extracted text from ${file.name}, chunked content, and updated vector index.`,
        steps: [
          "Read PDF file",
          "Extracted text",
          "Created chunks",
          "Updated RAG knowledge base",
        ],
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Upload Error:", error);
      const errorMessage = {
        id: messages.length + 2,
        type: "bot",
        text: `Error processing file: ${error.message}`,
        timestamp: new Date(),
        tools: [],
        planning: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handlePaperclipClick = () => {
    fileInputRef.current?.click();
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      text: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await fetch("http://localhost:5000/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: input }),
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const botMessage = {
        id: messages.length + 2,
        type: "bot",
        text: data.answer,
        timestamp: new Date(),
        tools: data.tools_used || [],
        planning: data.planning || null,
        steps: data.planning ? [data.planning] : [],
        // New agentic features
        confidence_score: data.confidence_score,
        iterations: data.iterations,
        followup_question: data.followup_question,
        needs_followup: data.needs_followup,
        user_preferences: data.user_preferences,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error fetching response:", error);
      const errorMessage = {
        id: messages.length + 2,
        type: "bot",
        text: "Sorry, I encountered an error connecting to the agent. Please make sure the backend is running.",
        timestamp: new Date(),
        tools: [],
        planning: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleNewChat = async () => {
    // Confirm with user
    if (messages.length > 1 && !window.confirm("Are you sure you want to start a new chat? This will clear the current conversation.")) {
      return;
    }

    try {
      // Clear backend history
      await fetch("http://localhost:5000/api/clear", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      // Reset frontend state
      setMessages([
        {
          id: 1,
          type: "bot",
          text: "Hello! I'm your GST AI Assistant. I can help you with GST-related queries, analyze datasets, and provide detailed information. How can I assist you today?",
          timestamp: new Date(),
          tools: [],
          planning: null,
        },
      ]);
      setInput("");
      setIsTyping(false);
    } catch (error) {
      console.error("Error clearing chat:", error);
      // Still reset frontend even if backend call fails
      setMessages([
        {
          id: 1,
          type: "bot",
          text: "Hello! I'm your GST AI Assistant. I can help you with GST-related queries, analyze datasets, and provide detailed information. How can I assist you today?",
          timestamp: new Date(),
          tools: [],
          planning: null,
        },
      ]);
      setInput("");
    }
  };

  const toggleAgentInfo = (messageId) => {
    setExpandedAgentInfo((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const copyMessage = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleFeedback = async (messageId, feedbackType) => {
    // Update local state immediately for visual feedback
    setMessageFeedback((prev) => ({
      ...prev,
      [messageId]: feedbackType,
    }));

    // Find the message to get its content
    const message = messages.find((msg) => msg.id === messageId);
    if (!message) return;

    try {
      // Send feedback to backend
      await fetch("http://localhost:5000/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message_id: messageId,
          feedback_type: feedbackType, // 'positive' or 'negative'
          message_text: message.text,
          query: message.type === "bot" ? messages.find((m) => m.id === messageId - 1)?.text : null,
          tools_used: message.tools || [],
        }),
      });
    } catch (error) {
      console.error("Error sending feedback:", error);
      // Revert feedback on error
      setMessageFeedback((prev) => {
        const newState = { ...prev };
        delete newState[messageId];
        return newState;
      });
    }
  };

  const handleRegenerate = async (messageId) => {
    // Find the original query for this bot message
    const botMessageIndex = messages.findIndex((msg) => msg.id === messageId);
    if (botMessageIndex === -1) return;

    const userMessage = messages[botMessageIndex - 1];
    if (!userMessage || userMessage.type !== "user") return;

    // Remove the old bot message and regenerate
    setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
    setInput(userMessage.text);
    setIsTyping(true);

    try {
      const response = await fetch("http://localhost:5000/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userMessage.text }),
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const botMessage = {
        id: Date.now(), // New ID for regenerated message
        type: "bot",
        text: data.answer,
        timestamp: new Date(),
        tools: data.tools_used || [],
        planning: data.planning || null,
        steps: data.planning ? [data.planning] : [],
        confidence_score: data.confidence_score,
        iterations: data.iterations,
        followup_question: data.followup_question,
        needs_followup: data.needs_followup,
        user_preferences: data.user_preferences,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error regenerating response:", error);
      const errorMessage = {
        id: Date.now(),
        type: "bot",
        text: "Sorry, I encountered an error regenerating the response. Please try again.",
        timestamp: new Date(),
        tools: [],
        planning: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      setInput("");
    }
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatMessageText = (text) => {
    if (!text) return "";
    
    // Split into paragraphs first
    let paragraphs = text.split(/\n\n+/);
    let formatted = "";
    
    paragraphs.forEach((para) => {
      para = para.trim();
      if (!para) return;
      
      // Check if paragraph contains bullet points
      const bulletLines = para.split(/\n/).filter(line => /^[-•]\s+/.test(line.trim()));
      const numberedLines = para.split(/\n/).filter(line => /^\d+\.\s+/.test(line.trim()));
      
      if (bulletLines.length > 0) {
        // It's a bullet list
        const listItems = bulletLines.map(line => 
          line.replace(/^[-•]\s+/, '').trim()
        );
        formatted += '<ul class="list-disc list-inside space-y-1.5 my-2 ml-4 text-gray-700 dark:text-gray-300">';
        listItems.forEach(item => {
          // Handle bold in list items
          item = item.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
          formatted += `<li>${item}</li>`;
        });
        formatted += '</ul>';
      } else if (numberedLines.length > 0) {
        // It's a numbered list
        const listItems = numberedLines.map(line => 
          line.replace(/^\d+\.\s+/, '').trim()
        );
        formatted += '<ol class="list-decimal list-inside space-y-1.5 my-2 ml-4 text-gray-700 dark:text-gray-300">';
        listItems.forEach(item => {
          item = item.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
          formatted += `<li>${item}</li>`;
        });
        formatted += '</ol>';
      } else {
        // Regular paragraph
        para = para.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-purple-700 dark:text-purple-300">$1</strong>');
        para = para.replace(/\*(.*?)\*/g, '<em>$1</em>');
        para = para.replace(/\n/g, '<br>');
        formatted += `<p class="my-2">${para}</p>`;
      }
    });
    
    return formatted || '<p>' + text.replace(/\n/g, '<br>') + '</p>';
  };

  return (
    <div className={`h-screen flex ${darkMode ? "dark" : ""}`}>
      {/* Sidebar */}
      <div
        className={`${
          showSidebar ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 fixed lg:relative w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 h-full transition-transform duration-300 z-20`}
      >
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="font-bold text-lg text-gray-800 dark:text-white">
            Conversations
          </h2>
        </div>
        <div className="p-3 space-y-2 overflow-y-auto h-[calc(100%-120px)]">
          <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border-l-4 border-purple-500 cursor-pointer">
            <div className="font-medium text-gray-800 dark:text-white text-sm">
              Current Chat
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Just now
            </div>
          </div>
          <div className="p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg cursor-pointer">
            <div className="font-medium text-gray-800 dark:text-white text-sm">
              GST on Healthcare
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              2 hours ago
            </div>
          </div>
          <div className="p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg cursor-pointer">
            <div className="font-medium text-gray-800 dark:text-white text-sm">
              Education Services
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Yesterday
            </div>
          </div>
        </div>
        <div className="absolute bottom-0 w-full p-3 border-t border-gray-200 dark:border-gray-700">
          <button 
            onClick={handleNewChat}
            className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
        {/* Header */}
        <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="lg:hidden text-gray-600 dark:text-gray-300"
            >
              {showSidebar ? <X size={24} /> : <Menu size={24} />}
            </button>
            <MessageSquare className="text-purple-600" size={28} />
            <div>
              <h1 className="text-xl font-bold text-gray-800 dark:text-white">
                GST AI Assistant
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Powered by Agentic AI
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              {darkMode ? (
                <Sun className="text-gray-300" size={20} />
              ) : (
                <Moon className="text-gray-600" size={20} />
              )}
            </button>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Settings
                className="text-gray-600 dark:text-gray-300"
                size={20}
              />
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.type === "user" ? "justify-end" : "justify-start"
              } animate-fadeIn`}
            >
              <div
                className={`max-w-3xl ${
                  msg.type === "user" ? "w-auto" : "w-full"
                }`}
              >
                <div
                  className={`flex gap-3 ${
                    msg.type === "user" ? "flex-row-reverse" : "flex-row"
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      msg.type === "user"
                        ? "bg-purple-600"
                        : "bg-gradient-to-br from-purple-500 to-blue-500"
                    }`}
                  >
                    {msg.type === "user" ? "👤" : "🤖"}
                  </div>
                  <div className="flex-1">
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        msg.type === "user"
                          ? "bg-purple-600 text-white"
                          : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 shadow-md"
                      }`}
                    >
                      <div 
                        className="text-sm leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: formatMessageText(msg.text) }}
                      />
                    </div>
                    <div
                      className={`flex items-center gap-2 mt-1 px-2 text-xs text-gray-500 dark:text-gray-400 ${
                        msg.type === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <span>{formatTime(msg.timestamp)}</span>
                      {msg.type === "bot" && (
                        <>
                          <button
                            onClick={() => copyMessage(msg.text)}
                            className="hover:text-purple-600 transition-colors"
                            title="Copy message"
                          >
                            <Copy size={14} />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, "positive")}
                            className={`transition-colors ${
                              messageFeedback[msg.id] === "positive"
                                ? "text-green-600 dark:text-green-400"
                                : "hover:text-purple-600"
                            }`}
                            title="Good answer"
                          >
                            <ThumbsUp size={14} />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, "negative")}
                            className={`transition-colors ${
                              messageFeedback[msg.id] === "negative"
                                ? "text-red-600 dark:text-red-400"
                                : "hover:text-purple-600"
                            }`}
                            title="Poor answer"
                          >
                            <ThumbsDown size={14} />
                          </button>
                          <button
                            onClick={() => handleRegenerate(msg.id)}
                            className="hover:text-purple-600 transition-colors"
                            title="Regenerate response"
                          >
                            <RefreshCw size={14} />
                          </button>
                        </>
                      )}
                    </div>

                    {/* Follow-up Question - Show right after bot message */}
                    {msg.type === "bot" && 
                     msg.needs_followup && 
                     msg.followup_question && (
                      <div className="mt-3 animate-fadeIn">
                        <div className="flex gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center flex-shrink-0">
                            ❓
                          </div>
                          <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 rounded-2xl px-4 py-3 shadow-md flex-1">
                            <p className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-1">
                              💡 Follow-up Question:
                            </p>
                            <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                              {msg.followup_question}
                            </p>
                            <button
                              onClick={() => setInput(msg.followup_question)}
                              className="text-xs text-yellow-700 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-300 font-medium transition-colors"
                            >
                              Use this question →
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Agent Info Panel */}
                    {msg.type === "bot" &&
                      msg.tools &&
                      msg.tools.length > 0 && (
                        <div className="mt-3 bg-purple-50 dark:bg-gray-700/50 rounded-lg overflow-hidden">
                          <button
                            onClick={() => toggleAgentInfo(msg.id)}
                            className="w-full px-4 py-2 flex items-center justify-between text-sm font-medium text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-gray-700 transition-colors"
                          >
                            <span className="flex items-center gap-2">
                              🧠 View Agent Reasoning
                            </span>
                            {expandedAgentInfo[msg.id] ? (
                              <ChevronUp size={16} />
                            ) : (
                              <ChevronDown size={16} />
                            )}
                          </button>
                          {expandedAgentInfo[msg.id] && (
                            <div className="px-4 py-3 space-y-3 border-t border-purple-100 dark:border-gray-600">
                              {msg.planning && (
                                <div>
                                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                    📋 Planning
                                  </h4>
                                  <p className="text-xs text-gray-600 dark:text-gray-400">
                                    {msg.planning}
                                  </p>
                                </div>
                              )}
                              <div>
                                <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                  🔧 Tools Used
                                </h4>
                                <div className="flex flex-wrap gap-1">
                                  {msg.tools.map((tool, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-1 bg-purple-200 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded text-xs"
                                    >
                                      {tool}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              {msg.steps && (
                                <div>
                                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                    🔄 Execution Steps
                                  </h4>
                                  <ol className="space-y-1">
                                    {msg.steps.map((step, idx) => (
                                      <li
                                        key={idx}
                                        className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-2"
                                      >
                                        <span className="text-purple-600 dark:text-purple-400 font-medium">
                                          {idx + 1}.
                                        </span>
                                        <span>{step}</span>
                                      </li>
                                    ))}
                                  </ol>
                                </div>
                              )}
                              {msg.iterations && msg.iterations > 1 && (
                                <div>
                                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                    🔄 Iterations
                                  </h4>
                                  <p className="text-xs text-gray-600 dark:text-gray-400">
                                    Completed {msg.iterations} execution cycle(s)
                                  </p>
                                </div>
                              )}
                              {msg.confidence_score !== undefined && (
                                <div>
                                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                    📊 Confidence Score
                                  </h4>
                                  <div className="flex items-center gap-2">
                                    <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                                      <div
                                        className="bg-purple-600 h-2 rounded-full transition-all"
                                        style={{
                                          width: `${msg.confidence_score * 100}%`,
                                        }}
                                      ></div>
                                    </div>
                                    <span className="text-xs text-gray-600 dark:text-gray-400">
                                      {Math.round(msg.confidence_score * 100)}%
                                    </span>
                                  </div>
                                </div>
                              )}
                              {msg.user_preferences && (
                                <div>
                                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                    💾 User Preferences
                                  </h4>
                                  <p className="text-xs text-gray-600 dark:text-gray-400">
                                    Depth: {msg.user_preferences.explanation_depth || 'medium'} | 
                                    Format: {msg.user_preferences.preferred_format || 'conversational'}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="flex gap-3 max-w-3xl">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                  🤖
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 shadow-md">
                  <div className="flex gap-1">
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0ms" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-4 py-4">
          {/* Quick Suggestions */}
          {messages.length === 1 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {quickSuggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <div className="max-w-4xl mx-auto">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf"
              className="hidden"
            />
            <div className="flex gap-2 items-end bg-gray-50 dark:bg-gray-800 rounded-2xl p-2 shadow-lg">
              <button
                onClick={handlePaperclipClick}
                className="p-2 text-gray-500 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors"
              >
                <Paperclip size={20} />
              </button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Press Enter to send)"
                className="flex-1 bg-transparent border-none outline-none resize-none text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 py-2 px-2 max-h-32"
                rows={1}
              />
              <button className="p-2 text-gray-500 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors">
                <Mic size={20} />
              </button>
              <button
                onClick={sendMessage}
                disabled={!input.trim()}
                className="p-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-xl transition-all disabled:cursor-not-allowed transform hover:scale-105"
              >
                <Send size={20} />
              </button>
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
              AI can make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div
          className="fixed inset-0 bg-black/50 z-30 flex items-center justify-center"
          onClick={() => setShowSettings(false)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 w-96 max-w-full m-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-4">
              Settings
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Theme
                </label>
                <select className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-800 dark:text-gray-200">
                  <option>Light</option>
                  <option>Dark</option>
                  <option>Auto</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Font Size
                </label>
                <input
                  type="range"
                  min="12"
                  max="20"
                  defaultValue="16"
                  className="w-full"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showAgent"
                  defaultChecked
                  className="rounded"
                />
                <label
                  htmlFor="showAgent"
                  className="text-sm text-gray-700 dark:text-gray-300"
                >
                  Show agentic details
                </label>
              </div>
            </div>
            <button
              onClick={() => setShowSettings(false)}
              className="w-full mt-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
