import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Artwork() {
  const [episodes, setEpisodes] = useState([]);
  const [artworks, setArtworks] = useState([]);

  const [selectedEpisode, setSelectedEpisode] = useState("");
  const [artworkType, setArtworkType] = useState("poster");
  const [storageKey, setStorageKey] = useState("");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [sizeBytes, setSizeBytes] = useState("");

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
  // FETCH EPISODES
  // -------------------------

  const fetchEpisodes = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/episodes/`,
        config
      );

      setEpisodes(response.data);

      if (
        response.data.length > 0 &&
        !selectedEpisode
      ) {
        setSelectedEpisode(
          String(response.data[0].id)
        );
      }
    } catch (error) {
      console.error(
        "Failed to load episodes:",
        error
      );
    }
  };

  // -------------------------
  // FETCH ARTWORK
  // -------------------------

  const fetchArtworks = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/artworks/`,
        config
      );

      setArtworks(response.data);
    } catch (error) {
      console.error(
        "Failed to load artworks:",
        error
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEpisodes();
    fetchArtworks();
  }, []);

  // -------------------------
  // CREATE ARTWORK
  // -------------------------

  const handleCreateArtwork = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedEpisode) {
      setMessage("Please select an episode.");
      return;
    }

    try {
      await axios.post(
        `${API_URL}/artworks/`,
        {
          episode_id: Number(selectedEpisode),
          artwork_type: artworkType,
          storage_key: storageKey,
          width: Number(width),
          height: Number(height),
          size_bytes: Number(sizeBytes),
        },
        config
      );

      setMessage(
        "Artwork created successfully!"
      );

      clearForm();

      await fetchArtworks();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to create artwork"
      );
    }
  };

  // -------------------------
  // START EDIT
  // -------------------------

  const handleEditArtwork = (artwork) => {
    setEditingId(artwork.id);

    setSelectedEpisode(
      String(artwork.episode_id)
    );

    setArtworkType(
      artwork.artwork_type
    );

    setStorageKey(
      artwork.storage_key
    );

    setWidth(
      String(artwork.width)
    );

    setHeight(
      String(artwork.height)
    );

    setSizeBytes(
      String(artwork.size_bytes)
    );

    setMessage("");
  };

  // -------------------------
  // UPDATE ARTWORK
  // -------------------------

  const handleUpdateArtwork = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!selectedEpisode) {
      setMessage("Please select an episode.");
      return;
    }

    try {
      await axios.put(
        `${API_URL}/artworks/${editingId}`,
        {
          episode_id: Number(selectedEpisode),
          artwork_type: artworkType,
          storage_key: storageKey,
          width: Number(width),
          height: Number(height),
          size_bytes: Number(sizeBytes),
        },
        config
      );

      setMessage(
        "Artwork updated successfully!"
      );

      clearForm();

      await fetchArtworks();
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to update artwork"
      );
    }
  };

  // -------------------------
  // DELETE ARTWORK
  // -------------------------

  const handleDeleteArtwork = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this artwork?"
    );

    if (!confirmDelete) return;

    try {
      await axios.delete(
        `${API_URL}/artworks/${id}`,
        config
      );

      setMessage(
        "Artwork deleted successfully!"
      );

      await fetchArtworks();
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
    setStorageKey("");
    setWidth("");
    setHeight("");
    setSizeBytes("");
  };

  // -------------------------
  // GET EPISODE TITLE
  // -------------------------

  const getEpisodeTitle = (episodeId) => {
    const episode = episodes.find(
      (item) => item.id === episodeId
    );

    return episode
      ? `${episode.episode_id} - ${episode.title}`
      : `Episode #${episodeId}`;
  };

  if (loading) {
    return <p>Loading artwork...</p>;
  }

  return (
    <div>
      <h1>Artwork</h1>

      {/* CREATE / EDIT FORM */}

      <div className="create-show">
        <h2>
          {editingId
            ? "Edit Artwork"
            : "Add Artwork"}
        </h2>

        <form
          onSubmit={
            editingId
              ? handleUpdateArtwork
              : handleCreateArtwork
          }
        >
          <select
            value={selectedEpisode}
            onChange={(e) =>
              setSelectedEpisode(
                e.target.value
              )
            }
            required
          >
            <option value="">
              Select an episode
            </option>

            {episodes.map((episode) => (
              <option
                key={episode.id}
                value={episode.id}
              >
                {episode.episode_id} -{" "}
                {episode.title}
              </option>
            ))}
          </select>

          <select
            value={artworkType}
            onChange={(e) =>
              setArtworkType(e.target.value)
            }
            required
          >
            <option value="poster">
              Poster
            </option>

            <option value="thumbnail">
              Thumbnail
            </option>

            <option value="banner">
              Banner
            </option>

            <option value="background">
              Background
            </option>
          </select>

          <input
            type="text"
            placeholder="Storage Key"
            value={storageKey}
            onChange={(e) =>
              setStorageKey(e.target.value)
            }
            required
          />

          <input
            type="number"
            min="1"
            placeholder="Width"
            value={width}
            onChange={(e) =>
              setWidth(e.target.value)
            }
            required
          />

          <input
            type="number"
            min="1"
            placeholder="Height"
            value={height}
            onChange={(e) =>
              setHeight(e.target.value)
            }
            required
          />

          <input
            type="number"
            min="1"
            placeholder="Size in bytes"
            value={sizeBytes}
            onChange={(e) =>
              setSizeBytes(e.target.value)
            }
            required
          />

          <button type="submit">
            {editingId
              ? "Update Artwork"
              : "Add Artwork"}
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

      {/* EXISTING ARTWORK */}

      <h2>Existing Artwork</h2>

      {artworks.length === 0 ? (
        <p>No artwork found.</p>
      ) : (
        <div className="show-list">
          {artworks.map((artwork) => (
            <div
              className="show-card"
              key={artwork.id}
            >
              <h2>
                {artwork.artwork_type}
              </h2>

              <p>
                <strong>Episode:</strong>{" "}
                {getEpisodeTitle(
                  artwork.episode_id
                )}
              </p>

              <p>
                <strong>Storage Key:</strong>{" "}
                {artwork.storage_key}
              </p>

              <p>
                <strong>Dimensions:</strong>{" "}
                {artwork.width} ×{" "}
                {artwork.height}
              </p>

              <p>
                <strong>Size:</strong>{" "}
                {artwork.size_bytes} bytes
              </p>

              <div className="show-actions">
                <button
                  onClick={() =>
                    handleEditArtwork(
                      artwork
                    )
                  }
                >
                  Edit
                </button>

                <button
                  onClick={() =>
                    handleDeleteArtwork(
                      artwork.id
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

export default Artwork;