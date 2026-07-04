import { Link } from "react-router-dom";

export default function AppLayout({ title, children }) {
  return (
    <div style={page}>
      <div style={headerBar}>
        <div style={headerInner}>
          <div>
            <div style={uni}>LEBANESE INTERNATIONAL UNIVERSITY</div>
            <div style={h1}>{title || "Traffic Violations System"}</div>
            <div style={sub}>
              Human-in-the-loop: review, approve/reject, and manage ticket lifecycle
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link to="/" style={linkBtn}>Home</Link>
            <Link to="/admin/login" style={linkBtn}>Admin</Link>
            <Link to="/owner/login" style={linkBtn}>Owner</Link>
          </div>
        </div>
      </div>

      <div style={contentWrap}>
        <div style={card}>{children}</div>
      </div>
    </div>
  );
}

const page = {
  minHeight: "100vh",
  width: "100%",
  background:
    "radial-gradient(circle at 10% 10%, #EEF2FF 0%, #F8FAFC 45%, #F6F7FB 100%)",
  fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial",
};

const headerBar = {
  width: "100%",
  background: "linear-gradient(180deg, #0B1020 0%, #111827 100%)",
  borderBottom: "1px solid rgba(255,255,255,0.10)",
};

const headerInner = {
  width: "100%",
  padding: "18px 24px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 14,
  flexWrap: "wrap",
};

const uni = {
  fontSize: 14,
  fontWeight: 1000,
  color: "#93C5FD",
  letterSpacing: 0.4,
};

const h1 = {
  fontSize: 26,
  fontWeight: 1100,
  color: "#FFFFFF",
  marginTop: 4,
};

const sub = {
  fontSize: 12,
  fontWeight: 800,
  color: "#C7D2FE",
  marginTop: 4,
};

const contentWrap = {
  width: "100%",
  padding: "18px 24px",
};

const card = {
  background: "rgba(255,255,255,0.92)",
  border: "1px solid rgba(17,24,39,0.08)",
  borderRadius: 18,
  padding: 18,
  boxShadow: "0 18px 55px rgba(16,24,40,0.10)",
};

const linkBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  color: "#E5E7EB",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
};
