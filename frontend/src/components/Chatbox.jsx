import React, { useState, useEffect, useRef } from "react";
import { FaMicrophone } from "@react-icons/all-files/fa/FaMicrophone";
import { FaPaperPlane } from "@react-icons/all-files/fa/FaPaperPlane";
import { FaUserCircle } from "@react-icons/all-files/fa/FaUserCircle";
import { FaRobot } from "@react-icons/all-files/fa/FaRobot";
import { FaHistory } from "@react-icons/all-files/fa/FaHistory";
import { FaTrash } from "@react-icons/all-files/fa/FaTrash";
import "./Chatbox.css";

const SUGGESTIONS = [
  "Who is the chair of computer science department?",
  "What are the degree requirements?",
  "What is the first day of class for fall 2025?",
];
const STORAGE_KEY = "chat_history";

// Helper: split text into pieces of [plain, link, plain, link...]
function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  return parts.map((part, idx) =>
    urlRegex.test(part) ? (
      <a
        key={idx}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        className="message-link"
      >
        {part}
      </a>
    ) : (
      <span key={idx}>{part}</span>
    )
  );
}

export default function Chatbox() {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
  const [serverHistory, setServerHistory] = useState([]);
  const [chatSessions, setChatSessions] = useState(() => {
    const saved = localStorage.getItem(`${STORAGE_KEY}_sessions`);
    return saved ? JSON.parse(saved) : [{ id: Date.now(), messages: [] }];
  });
  const [currentSessionId, setCurrentSessionId] = useState(
    () => chatSessions[0]?.id || Date.now()
  );
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Sync messages to the current session
    setChatSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, messages } : s
      )
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    localStorage.setItem(
      `${STORAGE_KEY}_sessions`,
      JSON.stringify(chatSessions)
    );
  }, [messages, chatSessions, currentSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, showHistoryPanel]);

  const addMessage = (text, sender) => {
    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    const newMessage = { text, sender, time };
    setMessages((prev) => [...prev, newMessage]);
  };

  const sendQuery = async (query) => {
    addMessage(query, "user");
    setIsLoading(true);
    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error(res.statusText);
      const { response } = await res.json();
      addMessage(response, "bot");
    } catch (err) {
      addMessage(`Error: ${err.message}`, "bot");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    const txt = input.trim();
    if (!txt || isLoading) return;
    sendQuery(txt);
    setInput("");
  };

  const handleSuggestion = (text) => {
    if (!isLoading) sendQuery(text);
  };

  const handleVoiceInput = () => {
    if (isListening) return;
    const SpeechAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechAPI) return alert("Speech API not supported.");
    const rec = new SpeechAPI();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => setIsListening(true);
    rec.onresult = (e) => setInput(e.results[0][0].transcript);
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);
    rec.start();
  };

  const handleViewHistory = async () => {
    try {
      const res = await fetch("http://localhost:5000/chat-history");
      if (!res.ok) throw new Error("Failed to fetch history");
      const { history } = await res.json();
      setServerHistory(history);
      setShowHistoryPanel((v) => !v);
    } catch (e) {
      console.error(e);
      alert("Could not load history");
    }
  };

  const handleNewChat = () => {
    const newSessionId = Date.now();
    setChatSessions((prev) => [
      ...prev,
      { id: newSessionId, messages: [] },
    ]);
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setShowHistoryPanel(false);
    fetch("http://localhost:5000/reset-history", { method: "POST" }).catch(
      (e) => console.error("Failed to reset server history", e)
    );
  };

  const handleDeleteChat = (sessionId) => {
    if (window.confirm("Delete this chat?")) {
      setChatSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        const next = chatSessions.find((s) => s.id !== sessionId);
        if (next) {
          setCurrentSessionId(next.id);
          setMessages(next.messages);
        } else {
          handleNewChat();
        }
      }
      fetch("http://localhost:5000/reset-history", { method: "POST" }).catch(
        (e) => console.error("Failed to reset server history", e)
      );
    }
  };

  const getChatTitle = (session) => {
    const first = session.messages[0];
    return first
      ? `Chat - ${new Date(first.time).toLocaleString([], {
          dateStyle: "short",
          timeStyle: "short",
        })}`
      : "New Chat";
  };

  return (
    <div className="chat-wrapper">
      {/* Sidebar */}
      <div className="chat-sidebar">
        <div className="sidebar-header">
          <h2>Chat Sessions</h2>
          <div className="action-bar">
            <button onClick={handleNewChat} className="action-btn">
              New Chat
            </button>
            <button onClick={handleViewHistory} className="action-btn">
              <FaHistory /> {showHistoryPanel ? "Hide" : "View"} History
            </button>
          </div>
        </div>
        <ul className="session-list">
          {chatSessions.map((session) => (
            <li
              key={session.id}
              className={`session-item ${
                session.id === currentSessionId ? "active" : ""
              }`}
              onClick={() => {
                setCurrentSessionId(session.id);
                setMessages(session.messages);
              }}
            >
              <span>{getChatTitle(session)}</span>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteChat(session.id);
                }}
              >
                <FaTrash />
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        {/* Header */}
        <div className="bot-header">
          <h2>Computer Science Department</h2>
        </div>

        {/* History panel */}
        {showHistoryPanel && (
          <div className="history-panel">
            {serverHistory.length === 0 ? (
              <p>
                <em>No previous conversation.</em>
              </p>
            ) : (
              serverHistory.map(([q, a], i) => (
                <div key={i} className="history-entry">
                  <strong>You:</strong> {q}
                  <br />
                  <strong>Bot:</strong> {a}
                </div>
              ))
            )}
          </div>
        )}

        {/* Quick replies */}
        <div className="suggestions">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              className="suggestion-btn"
              onClick={() => handleSuggestion(s)}
              disabled={isLoading}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Chat messages */}
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <div className="avatar">
                {msg.sender === "user" ? <FaUserCircle /> : <FaRobot />}
              </div>
              <div className="message-content">
                {msg.sender === "bot"
                  ? linkify(msg.text)
                  : <span>{msg.text}</span>}
                <div className="timestamp">{msg.time}</div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message bot">
              <div className="avatar">
                <FaRobot />
              </div>
              <div className="message-content">
                <div className="message-text">Loading...</div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <form onSubmit={handleSend} className="chat-input">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type or speak your message..."
            disabled={isLoading}
          />
          <button
            type="button"
            className="mic-button"
            onClick={handleVoiceInput}
            disabled={isLoading || isListening}
            title={isListening ? "Listening..." : "Speak"}
          >
            <FaMicrophone />
          </button>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            title="Send"
          >
            <FaPaperPlane />
          </button>
        </form>
      </div>
    </div>
  );
}
