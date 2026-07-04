import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";

export default function OwnerPay() {
  const { id } = useParams();
  const nav = useNavigate();
  const plate = localStorage.getItem("owner_plate");

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [method, setMethod] = useState("card");
  const [payLoading, setPayLoading] = useState(false);

  const amount = 50;

  useEffect(() => {
    if (!plate) {
      nav("/owner/login");
      return;
    }

    fetch(`${API_BASE}/api/violations/${id}`)
      .then((r) => r.json())
      .then((data) => {
        if (
          data &&
          String(data.plate || "").toLowerCase() ===
            String(plate).toLowerCase()
        ) {
          setTicket(data);
        } else {
          setTicket(null);
        }

        setLoading(false);
      })
      .catch(() => {
        setTicket(null);
        setLoading(false);
      });
  }, [id, plate, nav]);

  const confirmPay = async () => {
    if (!ticket) return;

    if (String(ticket.status || "").toUpperCase() !== "APPROVED") {
      alert("Payment is available only when status is APPROVED.");
      return;
    }

    setPayLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/violations/${ticket.id}/pay`, {
        method: "POST",
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Payment failed");
      }

      setTicket(data.violation);

      alert("Payment successful. Ticket marked as PAID.");

      nav(`/owner/receipt/${ticket.id}`);
    } catch (e) {
      alert(e.message || "Payment failed.");
    } finally {
      setPayLoading(false);
    }
  };

  return (
    <AdminStyleLayout
      title="Checkout"
      subtitle={plate ? `Plate: ${plate}` : "Citizen Portal"}
      rightActions={
        <Link to={`/owner/tickets/${id}`} style={btnHeader}>
          Back to Ticket
        </Link>
      }
    >
      {loading ? (
        <div style={{ fontWeight: 900 }}>Loading...</div>
      ) : !ticket ? (
        <div style={{ color: "#991B1B", fontWeight: 1000 }}>
          Ticket not found or not authorized.
        </div>
      ) : (
        <div style={{ display: "grid", gap: 14, maxWidth: 820 }}>
          <div style={card}>
            <div style={{ fontSize: 18, fontWeight: 1100, marginBottom: 8 }}>
              Payment Summary
            </div>

            <div style={row}>
              <span style={k}>Ticket ID</span>
              <span style={mono}>{ticket.id}</span>
            </div>

            <div style={row}>
              <span style={k}>Plate</span>
              <span style={mono}>{ticket.plate}</span>
            </div>

            <div style={row}>
              <span style={k}>Violation</span>
              <span style={v}>{ticket.violation_type}</span>
            </div>

            <div style={row}>
              <span style={k}>Location</span>
              <span style={v}>{ticket.location || "-"}</span>
            </div>

            <div style={row}>
              <span style={k}>Status</span>
              <span style={vStrong}>
                {String(ticket.status || "").toUpperCase()}
              </span>
            </div>

            <div style={{ ...row, borderBottom: "none" }}>
              <span style={k}>Amount</span>
              <span style={{ fontWeight: 1200, fontSize: 16 }}>
                {amount} USD
              </span>
            </div>

            {String(ticket.status || "").toUpperCase() !== "APPROVED" && (
              <div style={warnBox}>
                Payment is available only after admin approval.
              </div>
            )}
          </div>

          <div style={card}>
            <div style={{ fontSize: 18, fontWeight: 1100, marginBottom: 8 }}>
              Payment Method
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              <label style={radioRow}>
                <input
                  type="radio"
                  checked={method === "card"}
                  onChange={() => setMethod("card")}
                />
                <span style={radioText}>Card Payment</span>
              </label>

              <label style={radioRow}>
                <input
                  type="radio"
                  checked={method === "cash"}
                  onChange={() => setMethod("cash")}
                />
                <span style={radioText}>Cash at Office</span>
              </label>

              <label style={radioRow}>
                <input
                  type="radio"
                  checked={method === "bank"}
                  onChange={() => setMethod("bank")}
                />
                <span style={radioText}>Bank Transfer</span>
              </label>
            </div>

            <button
              onClick={confirmPay}
              disabled={
                payLoading ||
                String(ticket.status || "").toUpperCase() !== "APPROVED"
              }
              style={{
                ...payBtn,
                opacity:
                  String(ticket.status || "").toUpperCase() === "APPROVED"
                    ? 1
                    : 0.55,
                cursor:
                  String(ticket.status || "").toUpperCase() === "APPROVED"
                    ? "pointer"
                    : "not-allowed",
              }}
            >
              {payLoading ? "Processing..." : `Confirm Payment (${amount} USD)`}
            </button>

            <div style={note}>
              This is a thesis demo checkout. It marks the ticket as PAID and
              sends you to the receipt page.
            </div>
          </div>
        </div>
      )}
    </AdminStyleLayout>
  );
}

const card = {
  border: "1px solid #EEF2F7",
  borderRadius: 18,
  padding: 16,
  background: "white",
  boxShadow: "0 18px 40px rgba(16,24,40,0.06)",
};

const row = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  padding: "10px 0",
  borderBottom: "1px solid #F2F4F7",
};

const k = {
  color: "#667085",
  fontWeight: 900,
  fontSize: 13,
};

const v = {
  color: "#111827",
  fontWeight: 900,
  fontSize: 13,
};

const vStrong = {
  color: "#111827",
  fontWeight: 1100,
  fontSize: 13,
};

const mono = {
  color: "#111827",
  fontWeight: 1100,
  fontSize: 12,
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  wordBreak: "break-all",
  textAlign: "right",
};

const radioRow = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "10px 12px",
  borderRadius: 14,
  border: "1px solid #EEF2F7",
  background: "#fff",
  fontWeight: 900,
};

const radioText = {
  color: "#111827",
};

const payBtn = {
  width: "100%",
  padding: "14px 16px",
  marginTop: 14,
  borderRadius: 14,
  border: "1px solid #111827",
  background: "#111827",
  color: "white",
  fontWeight: 1100,
  boxShadow: "0 16px 40px rgba(17,24,39,0.18)",
};

const warnBox = {
  marginTop: 12,
  padding: "12px 14px",
  borderRadius: 14,
  background: "#FEF3C7",
  border: "1px solid #FDE68A",
  color: "#92400E",
  fontWeight: 1000,
};

const note = {
  marginTop: 10,
  fontSize: 12,
  color: "#667085",
  fontWeight: 800,
};

const btnHeader = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  color: "#E5E7EB",
  fontWeight: 900,
  textDecoration: "none",
};