import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

export default function OwnerLogin() {
  const [plate, setPlate] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    // Mock OTP (demo)
    if (plate.trim().length < 3) {
      setError("Please enter a valid plate number");
      return;
    }
    if (otp !== "1234") {
      setError("Invalid OTP (use 1234 for demo)");
      return;
    }

    // store plate locally for owner portal
    localStorage.setItem("owner_plate", plate.trim());
    nav("/owner/tickets");
  };

  return (
    <AdminStyleLayout title="Citizen Portal" subtitle="View traffic tickets, objections, and payment statu">
      <div style={wrap}>
        <div style={card}>
          <div style={cardHeader}>
            <div style={cardTitle}>Owner Sign In</div>
            <div style={cardSub}>Enter your plate number and OTP</div>
          </div>

          <form onSubmit={handleLogin} style={{ marginTop: 18 }}>
            <label style={label}>Plate Number</label>
            <input
              style={input}
              placeholder="e.g. N109959"
              value={plate}
              onChange={(e) => setPlate(e.target.value)}
            />

            <label style={{ ...label, marginTop: 14 }}>OTP</label>
            <input
              style={input}
              placeholder="1234"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
            />

            {error ? <div style={err}>{error}</div> : null}

            <button style={btn} type="submit">
              Continue
            </button>

            <div style={hint}>
              Demo OTP: <b>1234</b>
            </div>
          </form>
        </div>
      </div>
    </AdminStyleLayout>
  );
}

/* styles */
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
