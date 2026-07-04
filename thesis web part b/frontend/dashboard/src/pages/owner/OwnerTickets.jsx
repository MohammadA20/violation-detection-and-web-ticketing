import { Link, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";

function StatusPill({ status }) {
  const s = String(status || "").toUpperCase();
  const map = {
    PENDING: { bg: "#FEF3C7", fg: "#92400E", bd: "#FDE68A" },
    APPROVED: { bg: "#DCFCE7", fg: "#166534", bd: "#BBF7D0" },
    REJECTED: { bg: "#FEE2E2", fg: "#991B1B", bd: "#FECACA" },
    PAID: { bg: "#DBEAFE", fg: "#1E40AF", bd: "#BFDBFE" },
  };
  const st = map[s] || { bg: "#F3F4F6", fg: "#111827", bd: "#E5E7EB" };

  return (
    <span
      style={{
        padding: "6px 12px",
        borderRadius: 999,
        background: st.bg,
        color: st.fg,
        border: `1px solid ${st.bd}`,
        fontWeight: 1000,
        fontSize: 12,
        minWidth: 100,
        display: "inline-block",
        textAlign: "center",
      }}
    >
      {s}
    </span>
  );
}

export default function OwnerTickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const nav = useNavigate();

  const plate = localStorage.getItem("owner_plate");

  useEffect(() => {
    if (!plate) {
      nav("/owner/login");
      return;
    }

    fetch(`${API_BASE}/api/violations`)
      .then((r) => r.json())
      .then((data) => {
        const arr = Array.isArray(data) ? data : [];
        const mine = arr.filter(
          (v) => String(v.plate || "").toLowerCase() === String(plate).toLowerCase()
        );
        setTickets(mine);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [plate, nav]);

  const logout = () => {
    localStorage.removeItem("owner_plate");
    nav("/owner/login");
  };

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return [...tickets]
      .filter((t) => {
        if (!qq) return true;
        const type = String(t.violation_type || "").toLowerCase();
        const loc = String(t.location || "").toLowerCase();
        const st = String(t.status || "").toLowerCase();
        return type.includes(qq) || loc.includes(qq) || st.includes(qq);
      })
      .sort((a, b) => (Date.parse(b.timestamp || "") || 0) - (Date.parse(a.timestamp || "") || 0));
  }, [tickets, q]);

  return (
    <AdminStyleLayout
      title="Citizen Tickets"
      subtitle={plate ? `Plate: ${plate}` : "Citizen Portal"}
      rightActions={
        <button onClick={logout} style={btnHeader}>
          Logout
        </button>
      }
    >
      <div style={{ maxWidth: 900 }}>
        <div style={topRow}>
          <div style={{ fontWeight: 1100, color: "#111827" }}>My Tickets</div>

          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search (type / location / status)"
            style={search}
          />
        </div>

        {loading ? (
          <div style={{ fontWeight: 900 }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ color: "#667085", fontWeight: 800 }}>
            No tickets found.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {filtered.map((t) => (
              <div key={t.id} style={ticketCard}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 1100, color: "#111827" }}>
                      {String(t.violation_type || "").toUpperCase()}
                    </div>
                    <div style={{ fontSize: 13, color: "#667085", fontWeight: 800, marginTop: 4 }}>
                      {t.location || "-"} • {t.timestamp || "-"}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <StatusPill status={t.status} />
                    <Link to={`/owner/tickets/${t.id}`} style={openBtn}>
                      Open
                    </Link>
                  </div>
                </div>

                <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div style={{ fontSize: 12, color: "#667085", fontWeight: 900 }}>
                    Confidence:{" "}
                    <span style={{ color: "#111827" }}>
                      {typeof t.confidence === "number" ? t.confidence.toFixed(2) : "-"}
                    </span>
                  </div>

                  <div style={{ fontSize: 12, color: "#667085", fontWeight: 900 }}>
                    Evidence:{" "}
                    <span style={{ color: "#111827" }}>
                      {Array.isArray(t.evidence_images) ? t.evidence_images.length : 0}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminStyleLayout>
  );
}

const topRow = {
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
  alignItems: "center",
  flexWrap: "wrap",
};

const search = {
  width: "min(380px, 100%)",
  padding: "10px 12px",
  borderRadius: 12,
  border: "1px solid #E5E7EB",
  outline: "none",
  background: "#fff",
  fontWeight: 900,
  fontSize: 13,
};

const ticketCard = {
  border: "1px solid #EEF2F7",
  borderRadius: 18,
  padding: 14,
  background: "white",
  boxShadow: "0 18px 40px rgba(16,24,40,0.06)",
};

const openBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid #111827",
  background: "#111827",
  color: "white",
  fontWeight: 1000,
  textDecoration: "none",
  display: "inline-block",
};

const btnHeader = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  color: "#E5E7EB",
  fontWeight: 900,
  cursor: "pointer",
};
