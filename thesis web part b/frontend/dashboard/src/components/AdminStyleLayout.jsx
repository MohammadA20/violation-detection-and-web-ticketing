import { Link } from "react-router-dom";

export default function AdminStyleLayout({
  title,
  subtitle,
  rightActions,
  showHomeOnly = true,
  hideRightActions = false,
  children,
}) {
  return (
    <div style={page}>
      <style>{`
        html, body, #root { margin: 0; padding: 0; width: 100%; height: 100%; }
        * { box-sizing: border-box; }
      `}</style>

      <div style={headerBar}>
        <div style={headerInner}>
          <div>
            <div style={agencyName}>MINISTRY OF INTERIOR</div>

            <div style={headerTitle}>
              {title || "Intelligent Traffic Violation Detection System"}
            </div>

            <div style={headerSubtitle}>
              {subtitle ||
                "Computer vision, digital ticketing, admin verification, and citizen services"}
            </div>

            {showHomeOnly ? (
              <div style={navRow}>
                <Link to="/" style={navLink}>Home</Link>
              </div>
            ) : null}
          </div>

          {!hideRightActions ? (
            <div style={headerBtns}>
              {rightActions ? rightActions : null}
            </div>
          ) : null}
        </div>
      </div>

      <div style={accentLine} />

      <div style={mainWrap}>
        <div style={contentCard}>{children}</div>
      </div>
    </div>
  );
}

const page = {
  minHeight: "100vh",
  width: "100%",
  background:
    "radial-gradient(circle at 10% 10%, #EEF2FF 0%, #F8FAFC 45%, #F6F7FB 100%)",
  fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
};

const headerBar = {
  width: "100%",
  background: "linear-gradient(180deg, #07111F 0%, #111827 100%)",
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

const agencyName = {
  fontSize: 16,
  fontWeight: 1100,
  color: "#93C5FD",
  letterSpacing: 0.5,
  textTransform: "uppercase",
};

const headerTitle = {
  fontSize: 28,
  fontWeight: 1200,
  color: "#FFFFFF",
  marginTop: 4,
};

const headerSubtitle = {
  fontSize: 12,
  fontWeight: 800,
  color: "#C7D2FE",
  marginTop: 4,
  opacity: 0.95,
};

const navRow = {
  marginTop: 10,
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const navLink = {
  padding: "8px 12px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  color: "#E5E7EB",
  fontWeight: 900,
  textDecoration: "none",
};

const headerBtns = {
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
  justifyContent: "flex-end",
  alignItems: "center",
};

const accentLine = {
  width: "100%",
  height: 3,
  background: "linear-gradient(90deg, #2563EB, #60A5FA)",
};

const mainWrap = {
  width: "100%",
  padding: "18px 24px",
};

const contentCard = {
  background: "rgba(255,255,255,0.92)",
  border: "1px solid rgba(17,24,39,0.08)",
  borderRadius: 18,
  padding: 18,
  boxShadow: "0 18px 55px rgba(16,24,40,0.10)",
};