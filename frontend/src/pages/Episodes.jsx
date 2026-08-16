import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

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

  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const token = localStorage.getItem("access_token");

  const config = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  const fetchShows = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/shows/`,
        config
      );

      setShows(response.data);

      if (response.data.length > 0) {
        setSelectedShow(String(response.data[0].id));
      }
    } catch (error) {
      console.error("Failed to load shows:", error);
    }
  };

  const fetchSeasons = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/seasons/`,
        config
      );

      setSeasons(response.data);
    } catch (error) {
      console.error("Failed to load seasons:", error);
    }
  };

  const fetchEpisodes = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/episodes/`,
        config
      );

      setEpisodes(response.data);
    } catch (error) {
      console.error("Failed to load episodes:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShows();
    fetchSeasons();
    fetchEpisodes();
  }, []);

  useEffect(() => {
    if (selectedShow) {
      const showSeasons = seasons.filter(
        (season) =>
          season.show_id === Number(selectedShow)
      );

      if (showSeasons.length > 0) {
        setSelectedSeason(String(showSeasons[0].id));
      } else {
        setSelectedSeason("");
      }
    }
  }, [selectedShow, seasons]);

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

      setMessage("Episode created successfully!");

      setEpisodeId("");
      setEpisodeNumber("");
      setTitle("");
      setDuration("");
      setLanguage("en");
      setContentGroup("");
      setStatus("draft");

      await fetchEpisodes();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to create episode"
      );
    }
  };

  const getShowTitle = (showId) => {
    const show = shows.find(
      (item) => item.id === showId
    );

    return show ? show.title : `Show #${showId}`;
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

      <div className="create-show">
        <h2>Create Episode</h2>

        <form onSubmit={handleCreateEpisode}>
          <select
            value={selectedShow}
            onChange={(e) =>
              setSelectedShow(e.target.value)
            }
            required
          >
            <option value="">Select a show</option>

            {shows.map((show) => (
              <option
                key={show.id}
                value={show.id}
              >
                {show.title}
              </option>
            ))}
          </select>

          <select
            value={selectedSeason}
            onChange={(e) =>
              setSelectedSeason(e.target.value)
            }
            required
          >
            <option value="">Select a season</option>

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

          <input
            type="text"
            placeholder="Episode ID"
            value={episodeId}
            onChange={(e) =>
              setEpisodeId(e.target.value)
            }
            required
          />

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

          <input
            type="text"
            placeholder="Episode Title"
            value={title}
            onChange={(e) =>
              setTitle(e.target.value)
            }
            required
          />

          <input
            type="number"
            min="0"
            placeholder="Duration in seconds"
            value={duration}
            onChange={(e) =>
              setDuration(e.target.value)
            }
          />

          <input
            type="text"
            placeholder="Language (e.g. en)"
            value={language}
            onChange={(e) =>
              setLanguage(e.target.value)
            }
            required
          />

          <input
            type="text"
            placeholder="Content Group"
            value={contentGroup}
            onChange={(e) =>
              setContentGroup(e.target.value)
            }
            required
          />

          <select
            value={status}
            onChange={(e) =>
              setStatus(e.target.value)
            }
          >
            <option value="draft">Draft</option>
            <option value="ready">Ready</option>
            <option value="published">Published</option>
          </select>

          <button type="submit">
            Create Episode
          </button>
        </form>

        {message && (
          <p className="message">{message}</p>
        )}
      </div>

      <h2>Existing Episodes</h2>

      {episodes.length === 0 ? (
        <p>No episodes found.</p>
      ) : (
        <div className="show-list">
          {episodes.map((episode) => (
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
                {getShowTitle(
                  seasons.find(
                    (season) =>
                      season.id ===
                      episode.season_id
                  )?.show_id
                )}
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Episodes;