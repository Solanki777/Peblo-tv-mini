import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = localStorage.getItem("access_token");

  const config = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  const fetchDashboard = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/dashboard/`,
        config
      );

      setDashboard(response.data);
      setError("");
    } catch (error) {
      console.error(
        "Failed to load dashboard:",
        error
      );

      setError(
        error.response?.data?.detail ||
          "Failed to load dashboard"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const formatDate = (date) => {
    if (!date) {
      return "—";
    }

    return new Date(date).toLocaleString();
  };

  if (loading) {
    return <p>Loading dashboard...</p>;
  }

  if (error) {
    return (
      <div>
        <h1>Dashboard</h1>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Dashboard</h1>

      {/* STATISTICS */}

      <div className="dashboard-stats">

        <div className="stat-card">
          <h3>Shows</h3>
          <p>{dashboard.shows_count}</p>
        </div>

        <div className="stat-card">
          <h3>Seasons</h3>
          <p>{dashboard.seasons_count}</p>
        </div>

        <div className="stat-card">
          <h3>Episodes</h3>
          <p>{dashboard.episodes_count}</p>
        </div>

        <div className="stat-card">
          <h3>Artwork</h3>
          <p>{dashboard.artworks_count}</p>
        </div>

        <div className="stat-card">
          <h3>Publish Runs</h3>
          <p>{dashboard.publish_runs_count}</p>
        </div>

      </div>


      {/* RECENT PUBLISHING */}

      <h2>Recent Publishing</h2>

      {dashboard.recent_publish_runs.length === 0 ? (
        <p>No publish runs found.</p>
      ) : (
        <div className="show-list">

          {dashboard.recent_publish_runs.map(
            (run) => (

              <div
                className="show-card"
                key={run.id}
              >

                <h2>
                  Publish #{run.id}
                </h2>

                <p>
                  <strong>Status:</strong>{" "}
                  {run.status}
                </p>

                <p>
                  <strong>Started:</strong>{" "}
                  {formatDate(
                    run.started_at
                  )}
                </p>

                <p>
                  <strong>Completed:</strong>{" "}
                  {formatDate(
                    run.completed_at
                  )}
                </p>

                <p>
                  <strong>Shows:</strong>{" "}
                  {run.shows_count}
                </p>

                <p>
                  <strong>Episodes:</strong>{" "}
                  {run.episodes_count}
                </p>

                {run.error_message && (
                  <p>
                    <strong>Error:</strong>{" "}
                    {run.error_message}
                  </p>
                )}

              </div>

            )
          )}

        </div>
      )}
    </div>
  );
}

export default Dashboard;