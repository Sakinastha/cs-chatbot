// src/components/ChatSidebar.jsx
import React from "react";
import "./ChatSidebar.css";

const ChatSidebar = ({ sessions, activeId, onNew, onSelect, onDelete }) => {
  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <h2>Chat Sessions</h2>
        <div className="action-bar">
          <button className="action-btn" onClick={onNew}>
            New Chat
          </button>
          <button
            className="action-btn"
            onClick={() => alert("View History functionality to be implemented")}
          >
            View History
          </button>
          <button
            className="action-btn"
            onClick={() => {
              const id = activeId;
              if (id && window.confirm("Delete this chat?")) onDelete(id);
            }}
          >
            Delete
          </button>
        </div>
      </div>
      <ul className="session-list">
        {sessions.map((session) => (
          <li
            key={session.id}
            className={`session-item ${session.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(session.id)}
          >
            {session.title}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ChatSidebar;