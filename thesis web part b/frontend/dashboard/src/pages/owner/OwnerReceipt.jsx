import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";
import html2pdf from "html2pdf.js";

const API_BASE = "http://127.0.0.1:8000";

export default function OwnerReceipt() {
  const { id } = useParams();
  const nav = useNavigate();
  const plate = localStorage.getItem("owner_plate");

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);

  const amount = 50;

  const paidAt = useMemo(
    () => new Date().toISOString().slice(0, 19).replace("T", " "),
    []
  );

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

  const downloadPDF = () => {
    const el = document.getElementById("receipt");
    if (!el || !ticket) return;

    html2pdf()
      .set({
        margin: 0.35,
        filename: `receipt_${ticket.plate}_${ticket.id}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: {
          unit: "in",
          format: "letter",
          orientation: "portrait",
        },
      })
      .from(el)
      .save();
  };

  return (
    <AdminStyleLayout
      title="Official Payment Receipt"
      subtitle="Citizen Traffic Services"
      rightActions={
        <Link to={`/owner/tickets/${id}`} style={headerBtn}>
          Back to Ticket
        </Link>
      }
    >
      {loading ? (
        <div style={{ fontWeight: 900 }}>Loading...</div>
      ) : !ticket ? (
        <div style={{ color: "#991B1B", fontWeight: 1000 }}>
          Receipt not found.
        </div>
      ) : (
        <div style={{ maxWidth: 980, margin: "0 auto" }}>
          <div id="receipt" style={receiptCard}>
            <div style={topHeader}>
              <div style={leftHeader}>
                <div style={seal}>MOI</div>

                <div>
                  <div style={ministry}>MINISTRY OF INTERIOR</div>

                  <div style={receiptTitle}>
                    Traffic Violation Payment Receipt
                  </div>

                  <div style={receiptSubtitle}>
                    Official Digital Traffic Services Platform
                  </div>
                </div>
              </div>

              <div style={paidBadge}>
                <div style={paidText}>
                  {String(ticket.status || "").toUpperCase()}
                </div>
                <div style={verifiedText}>Verified Payment</div>
              </div>
            </div>

            <div style={metaGrid}>
              <MetaCard title="Receipt ID" value={ticket.id} mono />
              <MetaCard title="Paid At" value={paidAt} />
              <MetaCard title="Citizen Plate" value={ticket.plate} mono />
              <MetaCard
                title="Violation Status"
                value={String(ticket.status || "").toUpperCase()}
                green
              />
            </div>

            <div style={mainGrid}>
              <div style={sectionCard}>
                <div style={sectionTitle}>Citizen Information</div>

                <InfoRow label="Portal" value="Citizen Portal" />
                <InfoRow label="Service" value="Digital Payment" />
                <InfoRow label="Vehicle Plate" value={ticket.plate} mono />
              </div>

              <div style={sectionCard}>
                <div style={sectionTitle}>Violation Information</div>

                <InfoRow label="Violation Type" value={ticket.violation_type} />
                <InfoRow label="Location" value={ticket.location || "-"} />
                <InfoRow
                  label="Decision"
                  value={String(ticket.status || "").toUpperCase()}
                  green
                />
              </div>
            </div>

            <div style={paymentSection}>
              <div>
                <div style={paymentTitle}>Payment Summary</div>

                <div style={paymentDesc}>
                  Payment successfully recorded in the Ministry digital audit
                  system.
                </div>
              </div>

              <div style={amountBox}>
                <div style={amountLabel}>TOTAL AMOUNT</div>

                <div style={amountValue}>{amount} USD</div>

                <div style={gateway}>Secure Payment Gateway</div>
              </div>
            </div>

            <div style={officialNote}>
              This receipt confirms successful payment of the referenced traffic
              violation through the Ministry Traffic Violation Management
              Platform.
            </div>

            <div style={footer}>
              <div>
                Generated by Ministry Traffic Violation Management System
              </div>

              <div>© Ministry of Interior</div>
            </div>
          </div>

          <div style={actions}>
            <button onClick={downloadPDF} style={downloadBtn}>
              Download PDF
            </button>

            <Link to="/owner/tickets" style={secondaryBtn}>
              Back to Tickets
            </Link>
          </div>
        </div>
      )}
    </AdminStyleLayout>
  );
}

function MetaCard({ title, value, mono, green }) {
  return (
    <div style={metaCard}>
      <div style={metaTitle}>{title}</div>

      <div style={green ? greenValue : mono ? monoValue : normalValue}>
        {value}
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono, green }) {
  return (
    <div style={infoRow}>
      <span style={rowLabel}>{label}</span>

      <span style={green ? greenValue : mono ? monoValue : rowValue}>
        {value}
      </span>
    </div>
  );
}

const receiptCard = {
  background: "#FFFFFF",
  borderRadius: 28,
  overflow: "hidden",
  border: "1px solid #E5E7EB",
  boxShadow: "0 28px 90px rgba(15,23,42,0.12)",
};

const topHeader = {
  padding: 26,
  background:
    "linear-gradient(135deg, #07111F 0%, #0F172A 70%, #1E3A8A 100%)",
  color: "#FFFFFF",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 20,
  flexWrap: "wrap",
};

const leftHeader = {
  display: "flex",
  gap: 18,
  alignItems: "center",
};

const seal = {
  width: 70,
  height: 70,
  borderRadius: 20,
  background: "rgba(255,255,255,0.08)",
  border: "1px solid rgba(255,255,255,0.16)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 1200,
  fontSize: 18,
};

const ministry = {
  fontSize: 13,
  color: "#93C5FD",
  fontWeight: 1100,
  letterSpacing: 0.7,
};

const receiptTitle = {
  marginTop: 6,
  fontSize: 30,
  fontWeight: 1200,
};

const receiptSubtitle = {
  marginTop: 6,
  color: "#CBD5E1",
  fontWeight: 800,
  fontSize: 13,
};

const paidBadge = {
  padding: "14px 18px",
  borderRadius: 18,
  background: "rgba(34,197,94,0.14)",
  border: "1px solid rgba(34,197,94,0.22)",
  textAlign: "center",
};

const paidText = {
  fontSize: 20,
  fontWeight: 1200,
  color: "#86EFAC",
};

const verifiedText = {
  marginTop: 2,
  fontSize: 12,
  fontWeight: 900,
  color: "#DCFCE7",
};

const metaGrid = {
  padding: 20,
  background: "#F8FAFC",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: 14,
};

const metaCard = {
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  borderRadius: 18,
  padding: 14,
};

const metaTitle = {
  color: "#64748B",
  fontSize: 12,
  fontWeight: 900,
};

const normalValue = {
  marginTop: 8,
  color: "#111827",
  fontWeight: 1100,
};

const monoValue = {
  marginTop: 8,
  color: "#111827",
  fontWeight: 1100,
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  wordBreak: "break-all",
};

const greenValue = {
  marginTop: 8,
  background: "#DCFCE7",
  color: "#166534",
  padding: "6px 10px",
  borderRadius: 999,
  display: "inline-flex",
  fontWeight: 1100,
  fontSize: 12,
};

const mainGrid = {
  padding: 20,
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: 16,
};

const sectionCard = {
  border: "1px solid #E5E7EB",
  borderRadius: 22,
  padding: 18,
};

const sectionTitle = {
  fontSize: 18,
  fontWeight: 1200,
  marginBottom: 14,
  color: "#0F172A",
};

const infoRow = {
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
  padding: "12px 0",
  borderBottom: "1px solid #F1F5F9",
};

const rowLabel = {
  color: "#64748B",
  fontWeight: 900,
  fontSize: 13,
};

const rowValue = {
  color: "#111827",
  fontWeight: 1000,
  fontSize: 13,
};

const paymentSection = {
  margin: "0 20px 20px",
  padding: 22,
  borderRadius: 24,
  background: "linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)",
  border: "1px solid #BFDBFE",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 18,
  flexWrap: "wrap",
};

const paymentTitle = {
  fontSize: 22,
  fontWeight: 1200,
  color: "#0F172A",
};

const paymentDesc = {
  marginTop: 6,
  color: "#64748B",
  fontWeight: 800,
  lineHeight: 1.7,
};

const amountBox = {
  background: "#0F172A",
  color: "#FFFFFF",
  padding: 20,
  borderRadius: 22,
  minWidth: 240,
  textAlign: "right",
};

const amountLabel = {
  color: "#93C5FD",
  fontSize: 12,
  fontWeight: 1000,
};

const amountValue = {
  marginTop: 6,
  fontSize: 34,
  fontWeight: 1200,
};

const gateway = {
  marginTop: 6,
  color: "#CBD5E1",
  fontSize: 12,
  fontWeight: 900,
};

const officialNote = {
  margin: "0 20px 20px",
  padding: 16,
  borderRadius: 18,
  background: "#F8FAFC",
  border: "1px dashed #CBD5E1",
  color: "#475569",
  lineHeight: 1.7,
  fontSize: 13,
  fontWeight: 800,
};

const footer = {
  padding: "16px 20px",
  borderTop: "1px solid #E5E7EB",
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
  flexWrap: "wrap",
  color: "#64748B",
  fontSize: 12,
  fontWeight: 900,
};

const actions = {
  marginTop: 16,
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const downloadBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  border: "none",
  background: "#2563EB",
  color: "#FFFFFF",
  fontWeight: 1100,
  cursor: "pointer",
};

const secondaryBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  border: "1px solid #E5E7EB",
  background: "#FFFFFF",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 1000,
};

const headerBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  background: "rgba(255,255,255,0.10)",
  border: "1px solid rgba(255,255,255,0.18)",
  color: "#FFFFFF",
  textDecoration: "none",
  fontWeight: 1000,
};