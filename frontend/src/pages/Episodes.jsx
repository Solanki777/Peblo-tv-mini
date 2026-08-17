import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Episodes() {
  const [shows, setShows] = useState([]);
  const [seasons, setSeasons] = useState([]);
  const [episodes, setEpisodes] = useState([]);

  const [selectedShow, setSelectedShow] = useState("");
  const [selectedSeason, setSelectedSeason] = useState("");

  const [episodeId, setEpisodeId] = useState("");
  const [episodeNumber, setEpisodeNumber] = useState("");
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("");
  const [language, setLanguage] = useState("en");
  const [contentGroup, setContentGroup] = useState("");
  const [status, setStatus] = useState("draft");

  const [editingId, setEditingId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const token = localStorage.getItem("access_token");

  const config = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  // -------------------------
  // FETCH SHOWS
  // -------------------------

  const fetchShows = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/shows/`,
        config
      );

      setShows(response.data);

      if (
        response.data.length > 0 &&
        !selectedShow
      ) {
        setSelectedShow(
          String(response.data[0].id)
        );
      }
    } catch (error) {
      console.error(
        "Failed to load shows:",
        error
      );
    }
  };

  // -------------------------
  // FETCH SEASONS
  // -------------------------

  const fetchSeasons = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/seasons/`,
        config
      );

      setSeasons(response.data);
    } catch (error) {
      console.error(
        "Failed to load seasons:",
        error
      );
    }
  };

  // -------------------------
  // FETCH EPISODES
  // -------------------------

  const fetchEpisodes = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/episodes/`,
        config
      );

      setEpisodes(response.data);
    } catch (error) {
      console.error(
        "Failed to load episodes:",
        error
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShows();
    fetchSeasons();
    fetchEpisodes();
  }, []);

  // -------------------------
  // AUTO SELECT SEASON
  // -------------------------

  useEffect(() => {
    if (selectedShow) {
      const showSeasons = seasons.filter(
        (season) =>
          season.show_id === Number(selectedShow)
      );

      if (
        showSeasons.length > 0 &&
        !editingId
      ) {
        setSelectedSeason(
          String(showSeasons[0].id)
        );
      } else if (showSeasons.length === 0) {
        setSelectedSeason("");
      }
    }
  }, [selectedShow, seasons, editingId]);

  // -------------------------
  // CREATE EPISODE
  // -------------------------

  const handleCreateEpisode = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedSeason) {
      setMessage("Please select a season.");
      return;
    }

    try {
      await axios.post(
        `${API_URL}/episodes/`,
        {
          episode_id: episodeId,
          season_id: Number(selectedSeason),
          episode_number: Number(episodeNumber),
          title,
          duration_seconds: duration
            ? Number(duration)
            : null,
          language,
          content_group: contentGroup,
          status,
        },
        config
      );

      setMessage(
        "Episode created successfully!"
      );

      clearForm();

      await fetchEpisodes();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to create episode"
      );
    }
  };

  // -------------------------
  // START EDIT
  // -------------------------

  const handleEditEpisode = (episode) => {
    const season = seasons.find(
      (item) => item.id === episode.season_id
    );

    setEditingId(episode.id);

    if (season) {
      setSelectedShow(
        String(season.show_id)
      );
    }

    setSelectedSeason(
      String(episode.season_id)
    );

    setEpisodeId(episode.episode_id);
    setEpisodeNumber(
      String(episode.episode_number)
    );
    setTitle(episode.title);
    setDuration(
      episode.duration_seconds !== null &&
      episode.duration_seconds !== undefined
        ? String(episode.duration_seconds)
        : ""
    );
    setLanguage(episode.language);
    setContentGroup(episode.content_group);
    setStatus(episode.status);

    setMessage("");
  };

  // -------------------------
  // UPDATE EPISODE
  // -------------------------

  const handleUpdateEpisode = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedSeason) {
      setMessage("Please select a season.");
      return;
    }

    try {
      await axios.put(
        `${API_URL}/episodes/${editingId}`,
        {
          episode_id: episodeId,
          season_id: Number(selectedSeason),
          episode_number: Number(episodeNumber),
          title,
          duration_seconds: duration
            ? Number(duration)
            : null,
          language,
          content_group: contentGroup,
          status,
        },
        config
      );

      setMessage(
        "Episode updated successfully!"
      );

      clearForm();

      await fetchEpisodes();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to update episode"
      );
    }
  };

  // -------------------------
  // DELETE EPISODE
  // -------------------------

  const handleDeleteEpisode = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this episode?"
    );

    if (!confirmDelete) return;

    try {
      await axios.delete(
        `${API_URL}/episodes/${id}`,
        config
      );

      setMessage(
        "Episode deleted successfully!"
      );

      await fetchEpisodes();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Delete failed"
      );
    }
  };

  // -------------------------
  // CLEAR FORM
  // -------------------------

  const clearForm = () => {
    setEditingId(null);

    setEpisodeId("");
    setEpisodeNumber("");
    setTitle("");
    setDuration("");
    setLanguage("en");
    setContentGroup("");
    setStatus("draft");
  };

  // -------------------------
  // HELPERS
  // -------------------------

  const getShowTitle = (showId) => {
    const show = shows.find(
      (item) => item.id === showId
    );

    return show
      ? show.title
      : `Show #${showId}`;
  };

  const getSeasonNumber = (seasonId) => {
    const season = seasons.find(
      (item) => item.id === seasonId
    );

    return season
      ? `Season ${season.season_number}`
      : `Season #${seasonId}`;
  };

  if (loading) {
    return <p>Loading episodes...</p>;
  }

  return (
    <div>
      <h1>Episodes</h1>

      {/* CREATE / EDIT FORM */}

      <div className="create-show">
        <h2>
          {editingId
            ? "Edit Episode"
            : "Create Episode"}
        </h2>

        <form
          onSubmit={
            editingId
              ? handleUpdateEpisode
              : handleCreateEpisode
          }
        >
          {/* SHOW */}

          <select
            value={selectedShow}
            onChange={(e) =>
              setSelectedShow(e.target.value)
            }
            required
          >
            <option value="">
              Select a show
            </option>

            {shows.map((show) => (
              <option
                key={show.id}
                value={show.id}
              >
                {show.title}
              </option>
            ))}
          </select>

          {/* SEASON */}

          <select
            value={selectedSeason}
            onChange={(e) =>
              setSelectedSeason(e.target.value)
            }
            required
          >
            <option value="">
              Select a season
            </option>

            {seasons
              .filter(
                (season) =>
                  season.show_id ===
                  Number(selectedShow)
              )
              .map((season) => (
                <option
                  key={season.id}
                  value={season.id}
                >
                  Season {season.season_number}
                </option>
              ))}
          </select>

          {/* EPISODE ID */}

          <input
            type="text"
            placeholder="Episode ID"
            value={episodeId}
            onChange={(e) =>
              setEpisodeId(e.target.value)
            }
            required
          />

          {/* EPISODE NUMBER */}

          <input
            type="number"
            min="1"
            placeholder="Episode Number"
            value={episodeNumber}
            onChange={(e) =>
              setEpisodeNumber(e.target.value)
            }
            required
          />

          {/* TITLE */}

          <input
            type="text"
            placeholder="Episode Title"
            value={title}
            onChange={(e) =>
              setTitle(e.target.value)
            }
            required
          />

          {/* DURATION */}

          <input
            type="number"
            min="0"
            placeholder="Duration in seconds"
            value={duration}
            onChange={(e) =>
              setDuration(e.target.value)
            }
          />

          {/* LANGUAGE */}

          <input
            type="text"
            placeholder="Language (e.g. en)"
            value={language}
            onChange={(e) =>
              setLanguage(e.target.value)
            }
            required
          />

          {/* CONTENT GROUP */}

          <input
            type="text"
            placeholder="Content Group"
            value={contentGroup}
            onChange={(e) =>
              setContentGroup(e.target.value)
            }
            required
          />

          {/* STATUS */}

          <select
            value={status}
            onChange={(e) =>
              setStatus(e.target.value)
            }
          >
            <option value="draft">
              Draft
            </option>

            <option value="ready">
              Ready
            </option>

            <option value="published">
              Published
            </option>
          </select>

          {/* SUBMIT */}

          <button type="submit">
            {editingId
              ? "Update Episode"
              : "Create Episode"}
          </button>

          {/* CANCEL */}

          {editingId && (
            <button
              type="button"
              onClick={clearForm}
            >
              Cancel Edit
            </button>
          )}
        </form>

        {message && (
          <p className="message">
            {message}
          </p>
        )}
      </div>

      {/* EXISTING EPISODES */}

      <h2>Existing Episodes</h2>

      {episodes.length === 0 ? (
        <p>No episodes found.</p>
      ) : (
        <div className="show-list">
          {episodes.map((episode) => {
            const season = seasons.find(
              (item) =>
                item.id === episode.season_id
            );

            return (
              <div
                className="show-card"
                key={episode.id}
              >
                <h2>{episode.title}</h2>

                <p>
                  <strong>Episode ID:</strong>{" "}
                  {episode.episode_id}
                </p>

                <p>
                  <strong>Show:</strong>{" "}
                  {season
                    ? getShowTitle(
                        season.show_id
                      )
                    : "Unknown"}
                </p>

                <p>
                  <strong>Season:</strong>{" "}
                  {getSeasonNumber(
                    episode.season_id
                  )}
                </p>

                <p>
                  <strong>Episode:</strong>{" "}
                  {episode.episode_number}
                </p>

                <p>
                  <strong>Language:</strong>{" "}
                  {episode.language}
                </p>

                <p>
                  <strong>Content Group:</strong>{" "}
                  {episode.content_group}
                </p>

                <p>
                  <strong>Status:</strong>{" "}
                  {episode.status}
                </p>

                <p>
                  <strong>Duration:</strong>{" "}
                  {episode.duration_seconds
                    ? `${episode.duration_seconds} seconds`
                    : "—"}
                </p>

                <div className="show-actions">
                  <button
                    onClick={() =>
                      handleEditEpisode(
                        episode
                      )
                    }
                  >
                    Edit
                  </button>

                  <button
                    onClick={() =>
                      handleDeleteEpisode(
                        episode.id
                      )
                    }
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default Episodes;