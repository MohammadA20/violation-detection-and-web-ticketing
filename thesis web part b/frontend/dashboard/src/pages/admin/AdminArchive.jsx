import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";

export default function AdminArchive() {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);

  const nav = useNavigate();

  const fetchArchived = async () => {
    try {
      setLoading(true);

      const res = await fetch(
        `${API_BASE}/api/violations?include_archived=true`
      );

      const data = await res.json();

      const archivedOnly = Array.isArray(data)
        ? data.filter((v) => v.archived)
        : [];

      setViolations(archivedOnly);
    } catch {
      setViolations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("admin_token");

    if (!token) {
      nav("/admin/login");
      return;
    }

    fetchArchived();
  }, [nav]);

  const restoreViolation = async (id) => {
    try {
      const token = localStorage.getItem("admin_token");

      const res = await fetch(
        `${API_BASE}/api/violations/${id}/archive`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            archived: false,
          }),
        }
      );

      if (!res.ok) {
        throw new Error();
      }

      fetchArchived();
    } catch {
      alert("Failed to restore violation");
    }
  };

  return (
    <AdminStyleLayout
      title="Archived Violations"
      subtitle="Paid and archived records"
      rightActions={
        <Link to="/admin/dashboard" style={btn}>
          Back to Dashboard
        </Link>
      }
    >
      {loading ? (
        <div style={loadingBox}>Loading archive...</div>
      ) : violations.length === 0 ? (
        <div style={emptyBox}>
          No archived violations found.
        </div>
      ) : (
        <div style={grid}>
          {violations.map((v) => (
            <div key={v.id} style={card}>
              <div style={row}>
                <span style={label}>Plate</span>
                <span style={value}>{v.plate}</span>
              </div>

              <div style={row}>
                <span style={label}>Type</span>
                <span style={value}>
                  {v.violation_type}
                </span>
              </div>

              <div style={row}>
                <span style={label}>Status</span>
                <span style={paidPill}>
                  {v.status}
                </span>
              </div>

              <div style={row}>
                <span style={label}>Location</span>
                <span style={value}>
                  {v.location || "-"}
                </span>
              </div>

              <div style={row}>
                <span style={label}>Time</span>
                <span style={value}>
                  {v.timestamp || "-"}
                </span>
              </div>

              {v.admin_comment ? (
                <div style={commentBox}>
                  <strong>Admin Comment:</strong>{" "}
                  {v.admin_comment}
                </div>
              ) : null}

              <button
                style={restoreBtn}
                onClick={() =>
                  restoreViolation(v.id)
                }
              >
                Restore to Dashboard
              </button>
            </div>
          ))}
        </div>
      )}
    </AdminStyleLayout>
  );
}

const grid = {
  display: "grid",
  gridTemplateColumns:
    "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 16,
  marginTop: 16,
};

const card = {
  background: "#fff",
  border: "1px solid #E5E7EB",
  borderRadius: 18,
  padding: 18,
  boxShadow:
    "0 18px 40px rgba(16,24,40,0.08)",
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

const commentBox = {
  marginTop: 12,
  padding: 12,
  borderRadius: 12,
  background: "#F9FAFB",
  fontSize: 13,
  fontWeight: 800,
};

const restoreBtn = {
  marginTop: 14,
  width: "100%",
  padding: "12px 14px",
  borderRadius: 12,
  border: "none",
  background: "#2563EB",
  color: "#fff",
  fontWeight: 1000,
  cursor: "pointer",
};

const btn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  color: "#E5E7EB",
  fontWeight: 900,
  textDecoration: "none",
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

const paidPill = {
  padding: "5px 10px",
  borderRadius: 999,
  background: "#DBEAFE",
  color: "#1E40AF",
  fontWeight: 900,
  fontSize: 12,
};