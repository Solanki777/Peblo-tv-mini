import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function Seasons() {
  const [shows, setShows] = useState([]);
  const [seasons, setSeasons] = useState([]);

  const [selectedShow, setSelectedShow] = useState("");
  const [seasonNumber, setSeasonNumber] = useState("");

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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShows();
    fetchSeasons();
  }, []);

  // -------------------------
  // CREATE SEASON
  // -------------------------

  const handleCreateSeason = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedShow) {
      setMessage("Please select a show.");
      return;
    }

    try {
      await axios.post(
        `${API_URL}/seasons/`,
        {
          show_id: Number(selectedShow),
          season_number: Number(seasonNumber),
        },
        config
      );

      setMessage(
        "Season created successfully!"
      );

      setSeasonNumber("");

      await fetchSeasons();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to create season"
      );
    }
  };

  // -------------------------
  // START EDIT
  // -------------------------

  const handleEditSeason = (season) => {
    setEditingId(season.id);

    setSelectedShow(
      String(season.show_id)
    );

    setSeasonNumber(
      String(season.season_number)
    );

    setMessage("");
  };

  // -------------------------
  // UPDATE SEASON
  // -------------------------

  const handleUpdateSeason = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedShow) {
      setMessage("Please select a show.");
      return;
    }

    try {
      await axios.put(
        `${API_URL}/seasons/${editingId}`,
        {
          show_id: Number(selectedShow),
          season_number: Number(seasonNumber),
        },
        config
      );

      setMessage(
        "Season updated successfully!"
      );

      clearForm();

      await fetchSeasons();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to update season"
      );
    }
  };

  // -------------------------
  // DELETE SEASON
  // -------------------------

  const handleDeleteSeason = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this season?"
    );

    if (!confirmDelete) return;

    try {
      await axios.delete(
        `${API_URL}/seasons/${id}`,
        config
      );

      setMessage(
        "Season deleted successfully!"
      );

      await fetchSeasons();
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
    setSeasonNumber("");
  };

  // -------------------------
  // GET SHOW NAME
  // -------------------------

  const getShowTitle = (showId) => {
    const show = shows.find(
      (item) => item.id === showId
    );

    return show
      ? show.title
      : `Show #${showId}`;
  };

  if (loading) {
    return <p>Loading seasons...</p>;
  }

  return (
    <div>
      <h1>Seasons</h1>

      {/* CREATE / EDIT */}

      <div className="create-show">
        <h2>
          {editingId
            ? "Edit Season"
            : "Create Season"}
        </h2>

        <form
          onSubmit={
            editingId
              ? handleUpdateSeason
              : handleCreateSeason
          }
        >
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

          <input
            type="number"
            min="1"
            placeholder="Season Number"
            value={seasonNumber}
            onChange={(e) =>
              setSeasonNumber(e.target.value)
            }
            required
          />

          <button type="submit">
            {editingId
              ? "Update Season"
              : "Create Season"}
          </button>

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

      {/* EXISTING SEASONS */}

      <h2>Existing Seasons</h2>

      {seasons.length === 0 ? (
        <p>No seasons found.</p>
      ) : (
        <div className="show-list">
          {seasons.map((season) => (
            <div
              className="show-card"
              key={season.id}
            >
              <h2>
                {getShowTitle(
                  season.show_id
                )}
              </h2>

              <p>
                <strong>Season:</strong>{" "}
                {season.season_number}
              </p>

              <p>
                <strong>Season ID:</strong>{" "}
                {season.id}
              </p>

              <div className="show-actions">
                <button
                  onClick={() =>
                    handleEditSeason(season)
                  }
                >
                  Edit
                </button>

                <button
                  onClick={() =>
                    handleDeleteSeason(
                      season.id
                    )
                  }
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Seasons;