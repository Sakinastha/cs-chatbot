// src/components/NavBar.jsx
import React, { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import "../index.css";
import "./NavBar.css";

export default function NavBar({ role, onLogout }) {
  // read saved theme or default to light
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("theme") === "dark"
  );

  // keep body class and localStorage in sync
  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  // compute link class based on active state
  const linkClass = ({ isActive }) =>
    "nav-link" + (isActive ? " nav-link--selected" : "");

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="navbar-left">
          <img src="/msu_logo.png" alt="MSU Logo" className="nav-logo" />
          <span className="nav-title">CS NAVIGATOR</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={linkClass}>
            Chatbot
          </NavLink>
          <NavLink to="/curriculum" className={linkClass}>
            Curriculum
          </NavLink>
          {/* Admin link always visible */}
          <NavLink to="/admin" className={linkClass}>
            Admin
          </NavLink>

          {/* Login/Signup vs. Logout */}
          {!role ? (
            <>
              <NavLink to="/login" className={linkClass}>
                Login
              </NavLink>
              <NavLink to="/signup" className={linkClass}>
                Sign Up
              </NavLink>
            </>
          ) : (
            <button onClick={onLogout} className="logout-btn">
              Log Out
            </button>
          )}

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
