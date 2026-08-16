import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function Publishing() {
  const [publishRuns, setPublishRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [message, setMessage] = useState("");

  const token = localStorage.getItem("access_token");

  const config = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  // -------------------------
  // FETCH PUBLISH RUNS
  // -------------------------

  const fetchPublishRuns = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/publish/`,
        config
      );

      setPublishRuns(response.data);
    } catch (error) {
      console.error(
        "Failed to load publish runs:",
        error
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPublishRuns();
  }, []);

  // -------------------------
  // START PUBLISH
  // -------------------------

  const handlePublish = async () => {
    setPublishing(true);
    setMessage("");

    try {
      const response = await axios.post(
        `${API_URL}/publish/`,
        {},
        config
      );

      setMessage(
        `Publish completed successfully! Shows: ${response.data.shows_count}, Episodes: ${response.data.episodes_count}`
      );

      await fetchPublishRuns();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Publishing failed"
      );

      await fetchPublishRuns();
    } finally {
      setPublishing(false);
    }
  };

  // -------------------------
  // FORMAT DATE
  // -------------------------

  const formatDate = (date) => {
    if (!date) return "—";

    return new Date(date).toLocaleString();
  };

  if (loading) {
    return <p>Loading publishing history...</p>;
  }

  return (
    <div>
      <h1>Publishing</h1>

      {/* PUBLISH ACTION */}

      <div className="create-show">
        <h2>Publish Content</h2>

        <p>
          Publish the current shows and episodes.
        </p>

        <button
          onClick={handlePublish}
          disabled={publishing}
        >
          {publishing
            ? "Publishing..."
            : "Publish Content"}
        </button>

        {message && (
          <p className="message">
            {message}
          </p>
        )}
      </div>

      {/* PUBLISH HISTORY */}

      <h2>Publish History</h2>

      {publishRuns.length === 0 ? (
        <p>No publish runs found.</p>
      ) : (
        <div className="show-list">
          {publishRuns.map((run) => (
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
          ))}
        </div>
      )}
    </div>
  );
}

export default Publishing;