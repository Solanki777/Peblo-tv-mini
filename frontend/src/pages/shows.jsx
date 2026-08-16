import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

function Shows() {
  const [shows, setShows] = useState([]);
  const [loading, setLoading] = useState(true);

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [section, setSection] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [categories, setCategories] = useState("");

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

    } catch (error) {
      console.error("Failed to load shows:", error);

    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchShows();
  }, []);



  const handleCreateShow = async (e) => {
    e.preventDefault();
    setMessage("");

    try {
      await axios.post(
        `${API_URL}/shows/`,
        {
          title,
          slug,
          section: section || null,
          synopsis: synopsis || null,
          categories,
        },
        config
      );


      setMessage("Show created successfully!");

      setTitle("");
      setSlug("");
      setSection("");
      setSynopsis("");
      setCategories("");

      fetchShows();


    } catch (error) {

      setMessage(
        error.response?.data?.detail ||
        "Failed to create show"
      );
    }
  };



  const handleDeleteShow = async (id) => {

    const confirmDelete = window.confirm(
      "Are you sure you want to delete this show?"
    );


    if (!confirmDelete) return;


    try {

      await axios.delete(
        `${API_URL}/shows/${id}`,
        config
      );


      setMessage(
        "Show deleted successfully!"
      );


      fetchShows();


    } catch (error) {

      setMessage(
        error.response?.data?.detail ||
        "Delete failed"
      );
    }
  };



  if (loading) {
    return <p>Loading shows...</p>;
  }



  return (
    <div>

      <h1>Shows</h1>


      {/* Create Show */}

      <div className="create-show">

        <h2>Create Show</h2>


        <form onSubmit={handleCreateShow}>

          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e)=>setTitle(e.target.value)}
            required
          />


          <input
            type="text"
            placeholder="Slug"
            value={slug}
            onChange={(e)=>setSlug(e.target.value)}
            required
          />


          <input
            type="text"
            placeholder="Section"
            value={section}
            onChange={(e)=>setSection(e.target.value)}
          />


          <input
            type="text"
            placeholder="Categories"
            value={categories}
            onChange={(e)=>setCategories(e.target.value)}
          />


          <textarea
            placeholder="Synopsis"
            value={synopsis}
            onChange={(e)=>setSynopsis(e.target.value)}
          />


          <button type="submit">
            Create Show
          </button>


        </form>


        {message && (
          <p className="message">
            {message}
          </p>
        )}

      </div>



      {/* Existing Shows */}


      <h2>Existing Shows</h2>


      {
        shows.length === 0 ? (

          <p>No shows found.</p>

        ) : (

          <div className="show-list">

            {
              shows.map((show)=>(

                <div
                  className="show-card"
                  key={show.id}
                >

                  <h2>
                    {show.title}
                  </h2>


                  <p>
                    <strong>Slug:</strong>{" "}
                    {show.slug}
                  </p>


                  <p>
                    <strong>Section:</strong>{" "}
                    {show.section || "—"}
                  </p>


                  <p>
                    <strong>Categories:</strong>{" "}
                    {show.categories || "—"}
                  </p>


                  <p>
                    {show.synopsis ||
                    "No synopsis available."}
                  </p>



                  <button
                    onClick={() =>
                      handleDeleteShow(show.id)
                    }
                  >
                    Delete
                  </button>


                </div>

              ))
            }

          </div>

        )
      }


    </div>
  );
}


export default Shows;