// src/components/NavBar.jsx
import React, { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import "../index.css";

export default function NavBar() {
  // read saved theme or default to light
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });

  // keep body class and localStorage in sync
  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="navbar-left">
          <img src="/msu_logo.png" alt="MSU Logo" className="nav-logo" />
          <span className="nav-title">MSU CS Chatbot</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" end className="nav-link">
            Chatbot
          </NavLink>
          <NavLink to="/curriculum" className="nav-link">
            Curriculum
          </NavLink>
          <NavLink to="/admin" className="nav-link">
            Admin
          </NavLink>
          <button
            onClick={() => setDarkMode((prev) => !prev)}
            className="theme-toggle"
            title="Toggle light/dark mode"
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>
      </div>
    </nav>
  );
}
