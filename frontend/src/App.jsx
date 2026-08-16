import { useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage("");

    try {
      const response = await axios.post(
        `${API_URL}/auth/login`,
        {
          username,
          password,
        }
      );

      localStorage.setItem("access_token", response.data.access_token);

      setMessage("Login successful!");
      console.log(response.data);
    } catch (error) {
      setMessage(
        error.response?.data?.detail || "Login failed"
      );
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Peblo TV Mini</h1>

        <p className="subtitle">
          Content Management System
        </p>

        <form onSubmit={handleLogin}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">
            Login
          </button>
        </form>

        {message && (
          <p className="message">
            {message}
          </p>
        )}
      </div>
    </div>
  );
}

export default App;