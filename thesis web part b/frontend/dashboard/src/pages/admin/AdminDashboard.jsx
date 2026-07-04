import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";

export default function AdminDashboard() {
  const [violations, setViolations] = useState([]);
  const [aiReport, setAiReport] = useState({ cars: [], motorcycles: [] });
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  const nav = useNavigate();

  const isActiveViolation = (v) => {
    const status = String(v.status || "").toUpperCase();
    return !v.archived && status !== "PAID";
  };

  const hasCarViolation = (car) => {
    return (
      car.speed?.violation === true ||
      car.seatbelt?.violation === true ||
      car.phone?.violation === true
    );
  };

  const hasMotoViolation = (moto) => {
    return moto.speed?.violation === true || moto.helmet?.violation === true;
  };

  const aiCarsWithViolations = aiReport.cars.filter(hasCarViolation);
  const aiMotosWithViolations = aiReport.motorcycles.filter(hasMotoViolation);

  const fetchViolations = async () => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/violations`);
      const data = await res.json();
      setViolations(Array.isArray(data) ? data.filter(isActiveViolation) : []);
    } catch {
      setError("Failed to load violations");
    } finally {
      setLoading(false);
    }
  };

  const fetchAIReport = async () => {
    setAiLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/ai/final-report`);
      const data = await res.json();

      setAiReport({
        cars: Array.isArray(data.cars) ? data.cars : [],
        motorcycles: Array.isArray(data.motorcycles) ? data.motorcycles : [],
      });
    } catch {
      setError("Failed to load AI final report");
    } finally {
      setAiLoading(false);
    }
  };

  const importAIResults = async () => {
    setError("");

    try {
      const token = localStorage.getItem("admin_token");

      if (!token) {
        nav("/admin/login");
        return;
      }

      const res = await fetch(`${API_BASE}/api/ai/import-final-report`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Import failed");
      }

      alert(`Imported ${data.created_count} AI violations successfully`);

      await fetchViolations();
      await fetchAIReport();
    } catch (err) {
      setError(err.message || "Import failed");
      alert(err.message || "Import failed");
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("admin_token");

    if (!token) {
      nav("/admin/login");
      return;
    }

    fetchViolations();
    fetchAIReport();
  }, [nav]);

  const logout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_role");
    localStorage.removeItem("admin_logged");
    localStorage.removeItem("admin_token_expiry");
    nav("/admin/login");
  };

  const updateStatus = async (id, status, comment, objectionStatus = null) => {
    setBusyId(id);
    setError("");

    try {
      const token = localStorage.getItem("admin_token");

      if (!token) {
        nav("/admin/login");
        return;
      }

      const res = await fetch(`${API_BASE}/api/violations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status,
          admin_comment: comment,
          objection_status: objectionStatus,
        }),
      });

      if (!res.ok) {
        throw new Error("Unauthorized or update failed");
      }

      await fetchViolations();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const acceptObjection = (id) => {
    updateStatus(
      id,
      "REJECTED",
      "Objection accepted by admin. Ticket dismissed.",
      "ACCEPTED"
    );
  };

  const rejectObjection = (id) => {
    updateStatus(
      id,
      "APPROVED",
      "Objection rejected by admin. Payment still required.",
      "REJECTED"
    );
  };

  return (
    <AdminStyleLayout
      title="Smart Traffic Violation Management platform"
      subtitle="Secure admin review panel"
      rightActions={
        <>
          <button
            onClick={() => {
              fetchViolations();
              fetchAIReport();
            }}
            style={btn}
          >
            Refresh
          </button>

          <Link to="/admin/archive" style={archiveBtn}>
            Archive
          </Link>

          <button onClick={logout} style={btn}>
            Logout
          </button>
        </>
      }
    >
      {error && <div style={errorBox}>Error: {error}</div>}

      <section style={aiSection}>
        <div style={sectionHeader}>
          <div>
            <h2 style={sectionTitle}>AI Detected Violations</h2>
            <p style={sectionSub}>
              Only vehicles with violations are shown from final_report.json
            </p>
          </div>

          <div style={aiActions}>
            <button onClick={fetchAIReport} style={aiRefreshBtn}>
              {aiLoading ? "Loading..." : "Load AI Results"}
            </button>

            <button onClick={importAIResults} style={importBtn}>
              Import AI Violations
            </button>
          </div>
        </div>

        {aiCarsWithViolations.length === 0 &&
        aiMotosWithViolations.length === 0 ? (
          <div style={emptyBox}>No AI violations detected.</div>
        ) : (
          <div style={grid}>
            {aiCarsWithViolations.map((car) => (
              <div key={`car-${car.car_id}`} style={aiCard}>
                <div style={aiBadge}>CAR VIOLATION</div>

                <div style={row}>
                  <span style={label}>Plate</span>
                  <span style={value}>{car.plate?.value || "UNKNOWN"}</span>
                </div>

                <div style={row}>
                  <span style={label}>Speed</span>
                  <span style={value}>
                    {car.speed?.max_stable_kmh ?? "-"} km/h
                  </span>
                </div>

                {car.speed?.violation === true && (
                  <div style={violationLine}>Speed violation detected</div>
                )}

                {car.seatbelt?.violation === true && (
                  <div style={violationLine}>No seatbelt detected</div>
                )}

                {car.phone?.violation === true && (
                  <div style={violationLine}>Phone usage detected</div>
                )}

                <div style={row}>
                  <span style={label}>Seatbelt</span>
                  <span style={value}>
                    {car.seatbelt?.final_decision || "UNKNOWN"}
                  </span>
                </div>

                <div style={row}>
                  <span style={label}>Phone</span>
                  <span style={value}>
                    {car.phone?.final_decision || "UNKNOWN"}
                  </span>
                </div>

                <div style={row}>
                  <span style={label}>Tracks</span>
                  <span style={value}>{car.tracks?.join(", ") || "-"}</span>
                </div>
              </div>
            ))}

            {aiMotosWithViolations.map((moto) => (
              <div key={`moto-${moto.moto_id}`} style={aiCard}>
                <div style={motoBadge}>MOTORCYCLE VIOLATION</div>

                <div style={row}>
                  <span style={label}>Master ID</span>
                  <span style={value}>{moto.master_id || "-"}</span>
                </div>

                <div style={row}>
                  <span style={label}>Speed</span>
                  <span style={value}>
                    {moto.speed?.max_stable_kmh ?? "-"} km/h
                  </span>
                </div>

                {moto.speed?.violation === true && (
                  <div style={violationLine}>Motorcycle speeding detected</div>
                )}

                {moto.helmet?.violation === true && (
                  <div style={violationLine}>No helmet detected</div>
                )}

                <div style={row}>
                  <span style={label}>Helmet</span>
                  <span style={value}>
                    {moto.helmet?.final_decision || "UNKNOWN"}
                  </span>
                </div>

                <div style={row}>
                  <span style={label}>Tracks</span>
                  <span style={value}>{moto.tracks?.join(", ") || "-"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={normalSection}>
        <h2 style={sectionTitle}>Manual / Saved Violations</h2>

        {loading ? (
          <div style={loadingBox}>Loading...</div>
        ) : violations.length === 0 ? (
          <div style={emptyBox}>No active violations found.</div>
        ) : (
          <div style={grid}>
            {violations.map((v) => {
              const status = String(v.status || "").toUpperCase();
              const objectionStatus = String(
                v.objection_status || ""
              ).toUpperCase();
              const hasObjection = Boolean(
                v.objection_status || v.objection_text
              );
              const isObjectionPending =
                objectionStatus === "PENDING_REVIEW";

              return (
                <div key={v.id} style={card}>
                  <div style={row}>
                    <span style={label}>Plate</span>
                    <span style={value}>{v.plate}</span>
                  </div>

                  <div style={row}>
                    <span style={label}>Type</span>
                    <span style={value}>{v.violation_type}</span>
                  </div>

                  <div style={row}>
                    <span style={label}>Location</span>
                    <span style={value}>{v.location || "-"}</span>
                  </div>

                  <div style={row}>
                    <span style={label}>Confidence</span>
                    <span style={value}>
                      {typeof v.confidence === "number"
                        ? v.confidence.toFixed(2)
                        : "-"}
                    </span>
                  </div>

                  <div style={row}>
                    <span style={label}>Status</span>
                    <span style={pill(v.status)}>{status}</span>
                  </div>

                  <div style={row}>
                    <span style={label}>Time</span>
                    <span style={value}>{v.timestamp || "-"}</span>
                  </div>

                  {v.ai_details && (
                    <div style={aiDetailsBox}>
                      <div style={aiDetailsTitle}>AI Details</div>

                      <div style={row}>
                        <span style={label}>Source</span>
                        <span style={value}>
                          {v.ai_details.source || "AI"}
                        </span>
                      </div>

                      <div style={row}>
                        <span style={label}>Master ID</span>
                        <span style={value}>
                          {v.ai_details.master_id || "-"}
                        </span>
                      </div>

                      <div style={row}>
                        <span style={label}>Tracks</span>
                        <span style={value}>
                          {Array.isArray(v.ai_details.tracks)
                            ? v.ai_details.tracks.join(", ")
                            : "-"}
                        </span>
                      </div>

                      {v.ai_details.speed && (
                        <>
                          <div style={row}>
                            <span style={label}>Detected Speed</span>
                            <span style={value}>
                              {v.ai_details.speed.max_stable_kmh ?? "-"} km/h
                            </span>
                          </div>

                          <div style={row}>
                            <span style={label}>Speed Limit</span>
                            <span style={value}>
                              {v.ai_details.speed.limit_kmh ?? "-"} km/h
                            </span>
                          </div>
                        </>
                      )}

                      {v.ai_details.seatbelt && (
                        <div style={row}>
                          <span style={label}>Seatbelt Decision</span>
                          <span style={value}>
                            {v.ai_details.seatbelt.final_decision || "-"}
                          </span>
                        </div>
                      )}

                      {v.ai_details.phone && (
                        <div style={row}>
                          <span style={label}>Phone Decision</span>
                          <span style={value}>
                            {v.ai_details.phone.final_decision || "-"}
                          </span>
                        </div>
                      )}

                      {v.ai_details.helmet && (
                        <div style={row}>
                          <span style={label}>Helmet Decision</span>
                          <span style={value}>
                            {v.ai_details.helmet.final_decision || "-"}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {v.admin_comment && (
                    <div style={commentBox}>
                      <strong>Admin Comment:</strong> {v.admin_comment}
                    </div>
                  )}

                  {hasObjection && (
                    <div style={objectionBox}>
                      <div style={objectionTitle}>Owner Objection</div>

                      <div style={objectionStatusStyle}>
                        Status: {objectionStatus || "PENDING_REVIEW"}
                      </div>

                      <div style={objectionText}>
                        {v.objection_text || "No objection text provided."}
                      </div>

                      {v.objection_evidence && (
                        <div style={evidenceBox}>
                          <strong>Evidence:</strong>{" "}
                          {String(v.objection_evidence).startsWith("http") ? (
                            <a
                              href={v.objection_evidence}
                              target="_blank"
                              rel="noreferrer"
                              style={evidenceLink}
                            >
                              Open evidence
                            </a>
                          ) : (
                            <span>{v.objection_evidence}</span>
                          )}
                        </div>
                      )}

                      {isObjectionPending ? (
                        <div style={actions}>
                          <button
                            style={approveBtn}
                            disabled={busyId === v.id}
                            onClick={() => acceptObjection(v.id)}
                          >
                            Accept Objection
                          </button>

                          <button
                            style={rejectBtn}
                            disabled={busyId === v.id}
                            onClick={() => rejectObjection(v.id)}
                          >
                            Reject Objection
                          </button>
                        </div>
                      ) : (
                        <div style={finalDecisionBox}>
                          Final decision: {objectionStatus}
                        </div>
                      )}
                    </div>
                  )}

                  <div style={actions}>
                    {status === "PENDING" && (
                      <>
                        <button
                          style={approveBtn}
                          disabled={busyId === v.id}
                          onClick={() =>
                            updateStatus(v.id, "APPROVED", "Approved by admin")
                          }
                        >
                          Approve
                        </button>

                        <button
                          style={rejectBtn}
                          disabled={busyId === v.id}
                          onClick={() =>
                            updateStatus(v.id, "REJECTED", "Rejected by admin")
                          }
                        >
                          Reject
                        </button>
                      </>
                    )}

                    {status === "APPROVED" && (
                      <button
                        style={paidBtn}
                        disabled={busyId === v.id}
                        onClick={() =>
                          updateStatus(v.id, "PAID", "Payment confirmed")
                        }
                      >
                        Mark as Paid
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </AdminStyleLayout>
  );
}

const aiSection = {
  marginTop: 12,
  marginBottom: 28,
};

const normalSection = {
  marginTop: 26,
};

const sectionHeader = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 16,
  flexWrap: "wrap",
};

const sectionTitle = {
  margin: 0,
  fontSize: 22,
  fontWeight: 1000,
  color: "#111827",
};

const sectionSub = {
  margin: "6px 0 0",
  color: "#667085",
  fontWeight: 800,
  fontSize: 13,
};

const aiActions = {
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const grid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 16,
  marginTop: 16,
};

const card = {
  background: "#fff",
  border: "1px solid #E5E7EB",
  borderRadius: 18,
  padding: 18,
  boxShadow: "0 18px 40px rgba(16,24,40,0.08)",
};

const aiCard = {
  background: "#fff",
  border: "1px solid #FCA5A5",
  borderRadius: 18,
  padding: 18,
  boxShadow: "0 18px 40px rgba(220,38,38,0.10)",
};

const aiBadge = {
  display: "inline-block",
  marginBottom: 12,
  padding: "6px 10px",
  borderRadius: 999,
  background: "#FEE2E2",
  color: "#991B1B",
  fontWeight: 1000,
  fontSize: 12,
};

const motoBadge = {
  display: "inline-block",
  marginBottom: 12,
  padding: "6px 10px",
  borderRadius: 999,
  background: "#FEF3C7",
  color: "#92400E",
  fontWeight: 1000,
  fontSize: 12,
};

const violationLine = {
  marginTop: 10,
  padding: "10px 12px",
  borderRadius: 12,
  background: "#FEF2F2",
  color: "#991B1B",
  fontWeight: 1000,
  fontSize: 13,
  border: "1px solid #FCA5A5",
};

const row = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  padding: "8px 0",
  borderBottom: "1px solid #F3F4F6",
};

const label = {
  color: "#667085",
  fontWeight: 900,
  fontSize: 13,
};

const value = {
  color: "#111827",
  fontWeight: 900,
  fontSize: 13,
  textAlign: "right",
};

const aiDetailsBox = {
  marginTop: 14,
  padding: 14,
  borderRadius: 14,
  background: "#EFF6FF",
  border: "1px solid #BFDBFE",
};

const aiDetailsTitle = {
  marginBottom: 8,
  fontSize: 14,
  fontWeight: 1100,
  color: "#1E40AF",
};

const commentBox = {
  marginTop: 12,
  padding: 12,
  borderRadius: 12,
  background: "#F9FAFB",
  fontSize: 13,
  fontWeight: 800,
};

const objectionBox = {
  marginTop: 14,
  padding: 14,
  borderRadius: 14,
  background: "#FFF7ED",
  border: "1px solid #FDBA74",
};

const objectionTitle = {
  fontSize: 14,
  fontWeight: 1100,
  color: "#9A3412",
};

const objectionStatusStyle = {
  marginTop: 6,
  fontSize: 12,
  fontWeight: 1000,
  color: "#C2410C",
};

const objectionText = {
  marginTop: 8,
  fontSize: 13,
  fontWeight: 800,
  color: "#111827",
  lineHeight: 1.5,
};

const evidenceBox = {
  marginTop: 10,
  padding: 10,
  borderRadius: 10,
  background: "#FFFFFF",
  border: "1px solid #FED7AA",
  fontSize: 13,
  fontWeight: 800,
  color: "#111827",
};

const evidenceLink = {
  color: "#2563EB",
  fontWeight: 1000,
};

const finalDecisionBox = {
  marginTop: 12,
  padding: "10px 12px",
  borderRadius: 12,
  background: "#F3F4F6",
  color: "#111827",
  fontWeight: 1000,
  fontSize: 13,
};

const actions = {
  marginTop: 14,
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const btn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid #E5E7EB",
  background: "#fff",
  color: "#111827",
  fontWeight: 900,
  cursor: "pointer",
  textDecoration: "none",
};

const aiRefreshBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid #2563EB",
  background: "#2563EB",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
};

const importBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "none",
  background: "#7C3AED",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
};

const archiveBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid #2563EB",
  background: "#2563EB",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
  textDecoration: "none",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
};

const approveBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "none",
  background: "#16A34A",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
};

const rejectBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "none",
  background: "#DC2626",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
};

const paidBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "none",
  background: "#0EA5E9",
  color: "#fff",
  fontWeight: 900,
  cursor: "pointer",
};

const errorBox = {
  marginTop: 12,
  padding: 12,
  borderRadius: 12,
  background: "#FEE2E2",
  color: "#991B1B",
  fontWeight: 900,
};

const loadingBox = {
  marginTop: 20,
  fontWeight: 900,
};

const emptyBox = {
  marginTop: 20,
  color: "#667085",
  fontWeight: 900,
};

const pill = (status) => {
  const s = String(status || "").toUpperCase();

  if (s === "APPROVED") {
    return {
      padding: "5px 10px",
      borderRadius: 999,
      background: "#DCFCE7",
      color: "#166534",
      fontWeight: 900,
      fontSize: 12,
    };
  }

  if (s === "REJECTED") {
    return {
      padding: "5px 10px",
      borderRadius: 999,
      background: "#FEE2E2",
      color: "#991B1B",
      fontWeight: 900,
      fontSize: 12,
    };
  }

  if (s === "PAID") {
    return {
      padding: "5px 10px",
      borderRadius: 999,
      background: "#DBEAFE",
      color: "#1E40AF",
      fontWeight: 900,
      fontSize: 12,
    };
  }

  return {
    padding: "5px 10px",
    borderRadius: 999,
    background: "#FEF3C7",
    color: "#92400E",
    fontWeight: 900,
    fontSize: 12,
  };
};