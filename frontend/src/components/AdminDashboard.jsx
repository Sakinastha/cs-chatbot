// src/components/AdminDashboard.jsx
import React, { useState, useEffect } from "react";
import { FaCog } from "@react-icons/all-files/fa/FaCog";
import "./AdminDashboard.css";


const API_BASE = "http://localhost:5000";

export default function AdminDashboard() {
  // form state
  const [course, setCourse] = useState({
    course_code: "",
    course_name: "",
    credits: "",
    prerequisites: "",
    offered: "",
  });
  const [message, setMessage] = useState("");
  const [courses, setCourses] = useState([]);

  // load from FastAPI
  const loadCourses = async () => {
    setMessage("Loading courses...");
    try {
      const res = await fetch(`${API_BASE}/api/curriculum`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCourses(data);
      setMessage("");
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  useEffect(() => {
    loadCourses();
  }, []);

  // form input
  const handleChange = (e) => {
    const { name, value } = e.target;
    setCourse((c) => ({ ...c, [name]: value }));
  };

  // add
  const handleAddCourse = async (e) => {
    e.preventDefault();
    setMessage("Adding course...");
    const payload = {
      course_code: course.course_code,
      course_name: course.course_name,
      credits: Number(course.credits),
      prerequisites: course.prerequisites
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      offered: course.offered
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      const res = await fetch(`${API_BASE}/api/curriculum/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ Added ${data.course.course_code}`);
      setCourse({
        course_code: "",
        course_name: "",
        credits: "",
        prerequisites: "",
        offered: "",
      });
      loadCourses();
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // delete course
  const handleDelete = async (code) => {
    if (!window.confirm(`Delete ${code}?`)) return;
    setMessage(`Deleting ${code}...`);
    try {
      const res = await fetch(
        `${API_BASE}/api/curriculum/delete/${encodeURIComponent(code)}`,
        { method: "DELETE" }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
      loadCourses();
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // re-ingest
  const handleReingest = async () => {
    setMessage("Re-ingesting data...");
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // clear index
  const handleClearIndex = async () => {
    setMessage("Clearing index...");
    try {
      const res = await fetch(`${API_BASE}/clear-index`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  return (
    <div className="card page-container AdminDashboard">
      <header className="page-header">
        <FaCog className="page-icon" />
        <h1 className="page-title">Admin Dashboard</h1>
      </header>

      <p>Use the controls below to manage your curriculum data.</p>

      <section className="admin-actions" style={{ marginBottom: 24 }}>
        <button onClick={handleReingest} className="action-btn">
          Re-ingest Data
        </button>
        <button onClick={handleClearIndex} className="action-btn">
          Clear Index
        </button>
      </section>

      <section>
        <h2>Add New Course</h2>
        <form onSubmit={handleAddCourse} className="admin-form">
          <input
            name="course_code"
            placeholder="Course Code (e.g. COSC 101)"
            value={course.course_code}
            onChange={handleChange}
            required
          />
          <input
            name="course_name"
            placeholder="Course Name"
            value={course.course_name}
            onChange={handleChange}
            required
          />
          <input
            name="credits"
            type="number"
            placeholder="Credits"
            value={course.credits}
            onChange={handleChange}
            required
          />
          <input
            name="prerequisites"
            placeholder="Prerequisites (comma-separated)"
            value={course.prerequisites}
            onChange={handleChange}
          />
          <input
            name="offered"
            placeholder="Offered Semesters (comma-separated)"
            value={course.offered}
            onChange={handleChange}
          />
          <button type="submit" className="action-btn">
            Add Course
          </button>
        </form>
      </section>

      <section style={{ marginTop: 32 }}>
        <h2>Existing Courses ({courses.length})</h2>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Credits</th>
              <th>Offered</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {courses.map((c) => (
              <tr key={c.course_code}>
                <td>{c.course_code}</td>
                <td>{c.course_name}</td>
                <td>{c.credits}</td>
                <td>{c.offered.join(", ")}</td>
                <td>
                  <button onClick={() => handleDelete(c.course_code)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {message && <p style={{ marginTop: 16, fontStyle: "italic" }}>{message}</p>}
    </div>
  );
}
