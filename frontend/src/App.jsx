// src/App.jsx
import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";

import NavBar         from "./components/NavBar";
import ChatSidebar    from "./components/ChatSidebar";
import Chatbox        from "./components/Chatbox";
import CurriculumPage from "./components/CurriculumPage";
import AdminDashboard from "./components/AdminDashboard";
import Forbidden      from "./components/Forbidden";

import SignUp from "./SignUp";
import Login  from "./Login";

import "./index.css";

function parseJwt(token) {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(b64)
        .split("")
        .map((c) =>
          "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)
        )
        .join("")
    );
    return JSON.parse(json);
  } catch {
    return {};
  }
}

function RequireAuth({ children }) {
  return localStorage.getItem("token") 
    ? children 
    : <Navigate to="/login" replace />;
}

function ChatLayout({
  sessions,
  activeId,
  onNew,
  onSelect,
  onDelete,
  onSessionChange
}) {
  const activeSession = sessions.find((s) => s.id === activeId) || { messages: [] };
  return (
    <div className="app-layout">
      <ChatSidebar
        sessions={sessions}
        activeId={activeId}
        onNew={onNew}
        onSelect={onSelect}
        onDelete={onDelete}
      />
      <Chatbox
        key={activeId}
        initialMessages={activeSession.messages}
        onSessionChange={onSessionChange}
      />
    </div>
  );
}

export default function App() {
  const navigate = useNavigate();

  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [role, setRole]   = useState(null);

  // sync token ↔ localStorage & extract role
  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
      const { role: r } = parseJwt(token);
      setRole(r || null);
    } else {
      localStorage.removeItem("token");
      setRole(null);
    }
  }, [token]);

  // chat‐session state (unchanged)
  const [sessions, setSessions] = useState(() => {
    const saved = JSON.parse(localStorage.getItem("chat_sessions") || "[]");
    if (!saved.length) {
      const id = Date.now().toString();
      return [{ id, title: "New Chat", messages: [] }];
    }
    return saved;
  });
  const [activeId, setActiveId] = useState(sessions[0].id);
  useEffect(() => {
    localStorage.setItem("chat_sessions", JSON.stringify(sessions));
  }, [sessions]);

  // session handlers
  const handleNew = () => {
    const id = Date.now().toString();
    setSessions([{ id, title: "New Chat", messages: [] }, ...sessions]);
    setActiveId(id);
  };
  const handleSelect = (id) => setActiveId(id);
  const handleDelete = (id) => {
    if (!window.confirm("Delete this chat?")) return;
    const next = sessions.filter((s) => s.id !== id);
    setSessions(next);
    if (activeId === id) setActiveId(next[0]?.id || "");
  };
  const handleUpdateSession = (msgs) =>
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeId
          ? {
              ...s,
              messages: msgs,
              title: msgs[0]?.text.slice(0, 20) || "Chat",
            }
          : s
      )
    );

  // logout
  const handleLogout = () => {
    setToken(null);
    navigate("/login", { replace: true });
  };

  return (
    <>
      {/* nav now knows your role & logout */}
      <NavBar role={role} onLogout={handleLogout} />

      <Routes>
        {/* public */}
        <Route
          path="/signup"
          element={
            <SignUp onRegistered={() => navigate("/login", { replace: true })} />
          }
        />
        <Route
          path="/login"
          element={
            <Login
              onLoggedIn={(tk) => {
                setToken(tk);
                navigate("/", { replace: true });
              }}
            />
          }
        />

        {/* protected: chat */}
        <Route
          path="/"
          element={
            <RequireAuth>
              <ChatLayout
                sessions={sessions}
                activeId={activeId}
                onNew={handleNew}
                onSelect={handleSelect}
                onDelete={handleDelete}
                onSessionChange={handleUpdateSession}
              />
            </RequireAuth>
          }
        />

        {/* protected: curriculum */}
        <Route
          path="/curriculum"
          element={
            <RequireAuth>
              <CurriculumPage />
            </RequireAuth>
          }
        />

        {/* protected: admin */}
        <Route
          path="/admin"
          element={
            <RequireAuth>
              {role === "admin" ? <AdminDashboard /> : <Forbidden />}
            </RequireAuth>
          }
        />

        {/* fallback */}
        <Route
          path="*"
          element={<Navigate to={token ? "/" : "/login"} replace />}
        />
      </Routes>
    </>
  );
}
