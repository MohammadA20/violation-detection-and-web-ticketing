import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";
const SESSION_DURATION = 10 * 60 * 1000; // 10 minutes

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/auth/admin/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      if (!res.ok) {
        throw new Error("Invalid username or password");
      }

      const data = await res.json();

      const expiryTime = Date.now() + SESSION_DURATION;

      localStorage.setItem("admin_token", data.access_token);
      localStorage.setItem("admin_role", data.role);
      localStorage.setItem("admin_token_expiry", String(expiryTime));

      nav("/admin/dashboard");
    } catch (err) {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminStyleLayout title="Admin Login" subtitle="Secure access to the Admin Dashboard">
      <div style={wrap}>
        <div style={card}>
          <div style={cardHeader}>
            <div style={cardTitle}>Secure Sign In</div>
            <div style={cardSub}>Enter admin credentials to continue</div>
          </div>

          <form onSubmit={handleLogin} style={{ marginTop: 18 }}>
            <label style={label}>Username</label>
            <input
              style={input}
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <label style={{ ...label, marginTop: 14 }}>Password</label>
            <input
              style={input}
              type="password"
              placeholder="Admin@12345"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {error ? <div style={err}>{error}</div> : null}

            <button type="submit" style={btn} disabled={loading}>
              {loading ? "Checking..." : "Login"}
            </button>

            <div style={hint}>
              Protected by backend token authentication — session expires after 10 minutes
            </div>
          </form>
        </div>
      </div>
    </AdminStyleLayout>
  );
}

const wrap = {
  width: "100%",
  minHeight: "52vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "14px 0",
  transform: "translateY(-10px)",
};

const card = {
  width: "min(480px, 94vw)",
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  borderRadius: 22,
  padding: 22,
  boxShadow: "0 24px 70px rgba(16,24,40,0.14)",
};

const cardHeader = {
  paddingBottom: 12,
  borderBottom: "1px solid #EEF2F7",
};

const cardTitle = {
  fontSize: 22,
  fontWeight: 1100,
  color: "#111827",
  letterSpacing: 0.2,
};

const cardSub = {
  marginTop: 6,
  fontSize: 14,
  fontWeight: 800,
  color: "#667085",
};

const label = {
  display: "block",
  fontSize: 13,
  fontWeight: 1000,
  color: "#344054",
  marginBottom: 8,
};

const input = {
  width: "100%",
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #D0D5DD",
  outline: "none",
  fontWeight: 900,
  fontSize: 15,
  background: "#fff",
};

const btn = {
  width: "100%",
  padding: "14px 16px",
  marginTop: 18,
  borderRadius: 14,
  border: "1px solid #111827",
  background: "#111827",
  color: "white",
  fontWeight: 1100,
  fontSize: 15,
  cursor: "pointer",
  boxShadow: "0 16px 40px rgba(17,24,39,0.18)",
};

const err = {
  marginTop: 12,
  padding: "12px 14px",
  borderRadius: 14,
  background: "#FFECEC",
  border: "1px solid #FECACA",
  color: "#991B1B",
  fontWeight: 1000,
  fontSize: 13,
};

const hint = {
  marginTop: 12,
  fontSize: 13,
  color: "#667085",
  fontWeight: 900,
  textAlign: "center",
};