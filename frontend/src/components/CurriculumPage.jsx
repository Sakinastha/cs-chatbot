// src/components/CurriculumPage.jsx
import React, { useState, useEffect } from "react";
import { FaBookOpen } from "@react-icons/all-files/fa/FaBookOpen";

export default function CurriculumPage() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("http://localhost:5000/api/curriculum")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error("Expected an array of courses");
        }
        setCourses(data);
      })
      .catch((err) => {
        console.error("Curriculum fetch error:", err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card page-container CurriculumPage">
        <p>Loading curriculum…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="card page-container CurriculumPage">
        <p>Error loading curriculum: {error}</p>
      </div>
    );
  }

  return (
    <div className="card page-container CurriculumPage">
      <header className="page-header">
        <FaBookOpen className="page-icon" />
        <h1 className="page-title">Curriculum</h1>
      </header>

      <div className="table-wrapper">
        <table className="curriculum-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Course Name</th>
              <th>Credits</th>
              <th>Prerequisites</th>
              <th>Offered</th>
            </tr>
          </thead>
          <tbody>
            {courses.map((c) => (
              <tr key={c.course_code}>
                <td>{c.course_code}</td>
                <td>{c.course_name}</td>
                <td className="center">{c.credits}</td>
                <td>
                  {c.prerequisites && c.prerequisites.length
                    ? c.prerequisites.join(", ")
                    : "None"}
                </td>
                <td>{c.offered ? c.offered.join(", ") : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
