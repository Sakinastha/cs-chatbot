// frontend/src/components/Chatbot.tsx
"use client";

import { useState } from "react";
import axios from "axios";

const Chatbot = () => {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post("http://127.0.0.1:8000/chat", {
        query: query,  // Send query as the body content
      });

      // Add the user query and AI response to the messages state
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: "user", content: query },
        { role: "ai", content: res.data.response },
      ]);

      setQuery(""); // Clear the input field
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <div className="flex flex-col justify-between h-screen bg-secondary p-6">
      <div className="flex-1 overflow-auto mb-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs p-3 rounded-lg text-white ${
                  message.role === "user" ? "bg-primary" : "bg-gray-600"
                }`}
              >
                {message.content}
              </div>
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex items-center space-x-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Ask something..."
        />
        <button
          type="submit"
          className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-700 focus:outline-none"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default Chatbot;

