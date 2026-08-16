import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [stats, setStats] = useState({
  shows: 0,
  seasons: 0,
  episodes: 0,
  artworks: 0,
});
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loggedIn, setLoggedIn] = useState(
    !!localStorage.getItem("access_token")
  );
  useEffect(() => {
  if (!loggedIn) return;

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem("access_token");

      const config = {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      };

      const [
        showsResponse,
        seasonsResponse,
        episodesResponse,
        artworksResponse,
      ] = await Promise.all([
        axios.get(`${API_URL}/shows/`, config),
        axios.get(`${API_URL}/seasons/`, config),
        axios.get(`${API_URL}/episodes/`, config),
        axios.get(`${API_URL}/artworks/`, config),
      ]);

      setStats({
        shows: showsResponse.data.length,
        seasons: seasonsResponse.data.length,
        episodes: episodesResponse.data.length,
        artworks: artworksResponse.data.length,
      });
    } catch (error) {
      console.error("Failed to load dashboard statistics:", error);
    }
  };

  fetchStats();
}, [loggedIn]);

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

      localStorage.setItem(
        "access_token",
        response.data.access_token
      );

      setLoggedIn(true);
    } catch (error) {
      setMessage(
        error.response?.data?.detail || "Login failed"
      );
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setLoggedIn(false);
    setUsername("");
    setPassword("");
  };

  if (loggedIn) {
    return (
      <div className="dashboard">
        <aside className="sidebar">
          <h2>Peblo TV Mini</h2>

          <nav>
            <a href="#">Dashboard</a>
            <a href="#">Shows</a>
            <a href="#">Seasons</a>
            <a href="#">Episodes</a>
            <a href="#">Artwork</a>
            <a href="#">Publishing</a>
          </nav>

          <button onClick={handleLogout}>
            Logout
          </button>
        </aside>

        <main className="main-content">
          <h1>Dashboard</h1>

          <p>
            Welcome to the Peblo TV Mini Content Management
            System.
          </p>

          <div className="stats">
            <div className="stat-card">
              <h3>Shows</h3>
              <p>{stats.shows}</p>
            </div>

            <div className="stat-card">
              <h3>Seasons</h3>
              <p>{stats.seasons}</p>
            </div>

            <div className="stat-card">
              <h3>Episodes</h3>
              <p>{stats.episodes}</p>
            </div>

            <div className="stat-card">
              <h3>Artwork</h3>
              <p>{stats.artworks}</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

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
          <p className="message">{message}</p>
        )}
      </div>
    </div>
  );
}

export default App;