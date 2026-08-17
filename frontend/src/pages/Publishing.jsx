import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Publishing() {
  const [publishRuns, setPublishRuns] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reportError, setReportError] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [message, setMessage] = useState("");

  const token = localStorage.getItem("access_token");

  const config = {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };

  // -------------------------
  // FETCH VALIDATION REPORT
  // -------------------------
  // FIXED: this page previously had no visibility into *why* a publish
  // might be blocked - it just let you click "Publish" and hope. The
  // brief explicitly asks for "a publish button that's disabled with
  // reasons when blocked". Blocked episodes don't actually stop the
  // publish endpoint (it excludes them and still succeeds - see
  // app/api/publish.py) but an editor should still see what's about to
  // be left out *before* they publish, not discover it after.

  const fetchReport = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/admin/validation-report`,
        config
      );
      setReport(response.data);
      setReportError("");
    } catch (error) {
      setReportError(
        error.response?.data?.detail ||
          "Failed to load validation report"
      );
    }
  };

  // -------------------------
  // FETCH PUBLISH RUNS
  // -------------------------
  // FIXED: this used to call `${API_URL}/publish/` for both listing and
  // triggering a publish. The backend has never served that path - the
  // real routes are `/admin/catalog/publish` (POST, admin-only) and
  // `/admin/catalog/publish/runs` (GET) - so this whole page 404'd on
  // every load and every click.

  const fetchPublishRuns = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/admin/catalog/publish/runs`,
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
    fetchReport();
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
        `${API_URL}/admin/catalog/publish`,
        {},
        config
      );

      if (response.data.status === "failed") {
        setMessage(
          `Publish failed: ${response.data.error_message || "unknown error"}`
        );
      } else if (response.data.status === "completed_with_issues") {
        setMessage(
          `Published with ${response.data.issues_count} item(s) skipped ` +
            `(see validation report below). Shows: ${response.data.shows_count}, ` +
            `Episode variants: ${response.data.episodes_count}`
        );
      } else {
        setMessage(
          `Publish completed successfully! Shows: ${response.data.shows_count}, ` +
            `Episode variants: ${response.data.episodes_count}`
        );
      }

      await fetchPublishRuns();
      await fetchReport();
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

  const issueCount = report?.issue_count ?? 0;
  // Publishing itself is never truly "blocked" - the backend excludes
  // problem episodes and still succeeds (see app/api/publish.py) - but we
  // still warn the editor up front rather than let them discover the
  // gaps after the fact.
  const hasIssues = issueCount > 0;

  return (
    <div>
      <h1>Publishing</h1>

      {/* VALIDATION REPORT */}

      <div className="create-show">
        <h2>Validation Report</h2>

        {reportError && <p className="message">{reportError}</p>}

        {report && (
          hasIssues ? (
            <div>
              <p>
                <strong>{issueCount}</strong> item(s) will be left out of
                the next publish:
              </p>

              {report.shows_missing_section.length > 0 && (
                <div>
                  <h3>Shows missing a section</h3>
                  <ul>
                    {report.shows_missing_section.map((s) => (
                      <li key={`section-${s.id}`}>{s.title}</li>
                    ))}
                  </ul>
                </div>
              )}

              {report.episodes_missing_duration.length > 0 && (
                <div>
                  <h3>Episodes missing a duration</h3>
                  <ul>
                    {report.episodes_missing_duration.map((e) => (
                      <li key={`duration-${e.episode_id}`}>
                        {e.show} · S{e.season_number} · {e.title} ({e.language})
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {report.episodes_missing_artwork.length > 0 && (
                <div>
                  <h3>Episodes missing artwork</h3>
                  <ul>
                    {report.episodes_missing_artwork.map((e) => (
                      <li key={`artwork-${e.episode_id}`}>
                        {e.show} · S{e.season_number} · {e.title} ({e.language}) —
                        missing: {e.missing_artwork_types.join(", ")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p>Everything currently published is ready to publish cleanly.</p>
          )
        )}
      </div>

      {/* PUBLISH ACTION */}

      <div className="create-show">
        <h2>Publish Content</h2>

        <p>
          Builds the catalogue from everything currently marked "published"
          and writes it atomically. Items listed above are skipped, not
          blocking - the run still succeeds and is recorded either way.
        </p>

        <button
          onClick={handlePublish}
          disabled={publishing}
          title={
            hasIssues
              ? `${issueCount} item(s) will be skipped - see validation report above`
              : undefined
          }
        >
          {publishing
            ? "Publishing..."
            : hasIssues
            ? `Publish (${issueCount} item(s) will be skipped)`
            : "Publish Content"}
        </button>

        {message && (
          <p className="message">{message}</p>
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
                <strong>Episode variants:</strong>{" "}
                {run.episodes_count}
              </p>

              <p>
                <strong>Issues skipped:</strong>{" "}
                {run.issues_count}
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
