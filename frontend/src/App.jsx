// src/App.jsx
import React, { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import ChatSidebar from "./components/ChatSidebar";
import Chatbox from "./components/Chatbox";
import CurriculumPage from "./components/CurriculumPage";
import AdminDashboard from "./components/AdminDashboard";
import "./index.css";

export default function App() {
  // ─── Conversation sessions state ───────────────────────────────────────────────
  const [sessions, setSessions] = useState(() => {
    const saved = JSON.parse(localStorage.getItem("chat_sessions") || "[]");
    if (saved.length === 0) {
      // if nothing in storage, auto-create one session
      const id = Date.now().toString();
      return [{ id, title: "New Chat", messages: [] }];
    }
    return saved;
  });

  // pick as active the first session
  const [activeId, setActiveId] = useState(sessions[0]?.id);

  // persist sessions
  useEffect(() => {
    localStorage.setItem("chat_sessions", JSON.stringify(sessions));
  }, [sessions]);

  // ─── Handlers ───────────────────────────────────────────────────────────────────
  const handleNew = () => {
    const id = Date.now().toString();
    setSessions([{ id, title: "New Chat", messages: [] }, ...sessions]);
    setActiveId(id);
  };

/*************  ✨ Windsurf Command ⭐  *************/
  /**
   * Set the active session ID, given the ID of the session to switch to.
   * @param {string} id - The ID of the session to switch to.
   */
/*******  c871b92d-6fec-4ccb-95ab-a231b1f1ea8b  *******/
  const handleSelect = (id) => {
    setActiveId(id);
  };

  const handleDelete = (id) => {
    if (!window.confirm("Delete this chat?")) return;
    const next = sessions.filter((s) => s.id !== id);
    setSessions(next);
    // if we just deleted the active one, pick the next
    if (activeId === id) {
      setActiveId(next[0]?.id);
    }
  };

  // callback when Chatbox messages change
  const handleUpdateSession = (msgs) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeId
          ? {
              ...s,
              messages: msgs,
              // use first message as the title, or fallback to "Chat"
              title: msgs[0]?.text.slice(0, 20) || "Chat",
            }
          : s
      )
    );
  };

  const activeSession = sessions.find((s) => s.id === activeId) || null;

  return (
    <>
      <NavBar />

      <Routes>
        {/* ─── ROOT CHAT LAYOUT ─────────────────────────────────────────────────── */}
        <Route
          path="/"
          element={
            <div className="app-layout">
              <ChatSidebar
                sessions={sessions}
                activeId={activeId}
                onNew={handleNew}
                onSelect={handleSelect}
                onDelete={handleDelete}
              />

              {/*
                Because we now always have at least one session,
                activeSession will never be null.
              */}
              <Chatbox
                key={activeId}
                initialMessages={activeSession.messages}
                onSessionChange={handleUpdateSession}
              />
            </div>
          }
        />

        {/* ─── OTHER PAGES ───────────────────────────────────────────────────────── */}
        <Route path="/curriculum" element={<CurriculumPage />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </>
  );
}
