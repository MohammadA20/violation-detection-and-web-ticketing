import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import AdminStyleLayout from "../../components/AdminStyleLayout";

const API_BASE = "http://127.0.0.1:8000";

export default function OwnerTicketDetails() {
  const { id } = useParams();

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);

  const [objectionText, setObjectionText] = useState("");
  const [objectionFile, setObjectionFile] = useState(null);
  const [submittingObjection, setSubmittingObjection] = useState(false);
  const [objectionSuccess, setObjectionSuccess] = useState("");

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
        const found = arr.find((v) => v.id === id);

        if (
          found &&
          String(found.plate || "").toLowerCase() !==
            String(plate).toLowerCase()
        ) {
          setTicket(null);
        } else {
          setTicket(found || null);
        }

        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id, plate, nav]);

  const uploadEvidenceFile = async () => {
    if (!objectionFile) return null;

    const formData = new FormData();
    formData.append("file", objectionFile);

    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Evidence upload failed");
    }

    const data = await res.json();
    return data.url;
  };

  const submitObjection = async () => {
    if (!objectionText.trim()) {
      alert("Please enter objection details");
      return;
    }

    try {
      setSubmittingObjection(true);

      const evidenceUrl = await uploadEvidenceFile();

      const res = await fetch(`${API_BASE}/api/violations/${ticket.id}/object`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          objection_text: objectionText,
          objection_evidence: evidenceUrl,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to submit objection");
      }

      const updated = await res.json();

      setTicket(updated.violation);
      setObjectionSuccess("Objection submitted successfully");
    } catch {
      alert("Failed to submit objection");
    } finally {
      setSubmittingObjection(false);
    }
  };

  const statusUpper = ticket ? String(ticket.status || "").toUpperCase() : "";

  return (
    <AdminStyleLayout
      title="Ticket Details"
      subtitle={plate ? `Plate: ${plate}` : "Citizen Portal"}
      rightActions={
        <Link to="/owner/tickets" style={btnHeader}>
          Back
        </Link>
      }
    >
      {loading ? (
        <div style={{ fontWeight: 900 }}>Loading...</div>
      ) : !ticket ? (
        <div style={{ color: "#991B1B", fontWeight: 1000 }}>
          Ticket not found (or not authorized).
        </div>
      ) : (
        <div style={{ display: "grid", gap: 14, maxWidth: 860 }}>
          <div style={box}>
            <div style={row}>
              <span style={k}>Plate</span>
              <span style={vMono}>{ticket.plate}</span>
            </div>

            <div style={row}>
              <span style={k}>Type</span>
              <span style={v}>{ticket.violation_type}</span>
            </div>

            <div style={row}>
              <span style={k}>Location</span>
              <span style={v}>{ticket.location || "-"}</span>
            </div>

            <div style={row}>
              <span style={k}>Confidence</span>
              <span style={v}>
                {typeof ticket.confidence === "number"
                  ? ticket.confidence.toFixed(2)
                  : "-"}
              </span>
            </div>

            <div style={row}>
              <span style={k}>Status</span>
              <span style={vStrong}>{statusUpper}</span>
            </div>

            {ticket.objection_status ? (
              <>
                <div style={row}>
                  <span style={k}>Objection</span>
                  <span style={vStrong}>{ticket.objection_status}</span>
                </div>

                {ticket.objection_text ? (
                  <div style={objectionViewBox}>
                    <div style={objectionTitle}>Submitted Objection</div>
                    <div style={objectionTextView}>{ticket.objection_text}</div>

                    {ticket.objection_evidence ? (
                      <div style={evidenceView}>
                        <strong>Evidence:</strong>{" "}
                        <a
                          href={ticket.objection_evidence}
                          target="_blank"
                          rel="noreferrer"
                          style={evidenceLink}
                        >
                          Open uploaded evidence
                        </a>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}

            <div style={{ ...row, borderBottom: "none" }}>
              <span style={k}>Time</span>
              <span style={v}>{ticket.timestamp || "-"}</span>
            </div>
          </div>

          <div style={box}>
            <div style={{ fontSize: 16, fontWeight: 1100, marginBottom: 8 }}>
              Actions
            </div>

            {statusUpper === "APPROVED" ? (
              <>
                <Link to={`/owner/pay/${ticket.id}`} style={btnPrimary}>
                  Proceed to Payment
                </Link>

                <div style={hint}>
                  You will be redirected to a demo checkout page.
                </div>

                {!ticket.objection_status ? (
                  <div style={{ marginTop: 16 }}>
                    <textarea
                      placeholder="Explain why you want to dispute this violation..."
                      value={objectionText}
                      onChange={(e) => setObjectionText(e.target.value)}
                      style={textarea}
                    />

                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setObjectionFile(e.target.files?.[0] || null)}
                      style={fileInput}
                    />

                    {objectionFile ? (
                      <div style={selectedFile}>
                        Selected evidence: {objectionFile.name}
                      </div>
                    ) : null}

                    <button
                      onClick={submitObjection}
                      disabled={submittingObjection}
                      style={btnDanger}
                    >
                      {submittingObjection ? "Submitting..." : "Submit Objection"}
                    </button>
                  </div>
                ) : (
                  <div style={infoBox}>
                    Your objection has already been submitted and is waiting for admin review.
                  </div>
                )}

                {objectionSuccess ? (
                  <div style={successBox}>{objectionSuccess}</div>
                ) : null}
              </>
            ) : null}

            {statusUpper === "PAID" ? (
              <>
                <div style={paidBox}>
                  ✅ Payment completed. Receipt is available.
                </div>

                <Link to={`/owner/receipt/${ticket.id}`} style={btnBlue}>
                  View Receipt (PDF)
                </Link>
              </>
            ) : null}

            {statusUpper === "PENDING" ? (
              <div style={warnBox}>
                Payment is not available yet. Please wait for admin approval.
              </div>
            ) : null}

            {statusUpper === "REJECTED" ? (
              <div style={rejectBox}>
                Ticket was rejected. No payment is required.
              </div>
            ) : null}
          </div>

          <div style={box}>
            <div style={{ fontSize: 16, fontWeight: 1100, marginBottom: 8 }}>
              Evidence
            </div>

            {Array.isArray(ticket.evidence_images) &&
            ticket.evidence_images.length > 0 ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: 12,
                }}
              >
            {ticket.evidence_images.map((img, i) => (
              
              <a
                key={i}
                href={img.startsWith("http") ? img : `${API_BASE}/${img}`}
                target="_blank"
                rel="noreferrer"
                onClick={() => console.log("EVIDENCE IMG =", img)}
              >
                <img
                  src={img.startsWith("http") ? img : `${API_BASE}/${img}`}
                  alt={`Evidence ${i + 1}`}
                  style={{
                    width: "100%",
                    borderRadius: 12,
                    border: "1px solid #E5E7EB",
                    cursor: "pointer",
                  }}
                />
              </a>
            ))}
              </div>
            ) : (
              <div style={{ color: "#667085", fontWeight: 800 }}>
                No evidence available.
              </div>
            )}
           </div>
        </div>
      )}           
    </AdminStyleLayout>
  );
}

const box = {
  border: "1px solid #EEF2F7",
  borderRadius: 18,
  padding: 16,
  background: "white",
  boxShadow: "0 18px 40px rgba(16,24,40,0.06)",
};

const row = {
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
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

const vMono = {
  color: "#111827",
  fontWeight: 1100,
  fontSize: 13,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
};

const btnPrimary = {
  display: "inline-block",
  width: "100%",
  textAlign: "center",
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #111827",
  background: "#111827",
  color: "white",
  fontWeight: 1100,
  textDecoration: "none",
};

const btnBlue = {
  display: "inline-block",
  width: "100%",
  textAlign: "center",
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #2563EB",
  background: "#2563EB",
  color: "white",
  fontWeight: 1100,
  textDecoration: "none",
  marginTop: 10,
};

const textarea = {
  width: "100%",
  minHeight: 120,
  borderRadius: 14,
  border: "1px solid #D0D5DD",
  padding: 14,
  outline: "none",
  fontWeight: 800,
  resize: "vertical",
};

const fileInput = {
  width: "100%",
  marginTop: 10,
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #D0D5DD",
  background: "#fff",
  fontWeight: 800,
};

const selectedFile = {
  marginTop: 8,
  fontSize: 12,
  color: "#475467",
  fontWeight: 900,
};

const btnDanger = {
  marginTop: 10,
  width: "100%",
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #DC2626",
  background: "#DC2626",
  color: "white",
  fontWeight: 1100,
  cursor: "pointer",
};

const successBox = {
  marginTop: 10,
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #BBF7D0",
  background: "#DCFCE7",
  color: "#166534",
  fontWeight: 1000,
};

const infoBox = {
  marginTop: 12,
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #BFDBFE",
  background: "#DBEAFE",
  color: "#1E40AF",
  fontWeight: 1000,
};

const objectionViewBox = {
  marginTop: 12,
  padding: 12,
  borderRadius: 14,
  border: "1px solid #FDBA74",
  background: "#FFF7ED",
};

const objectionTitle = {
  color: "#9A3412",
  fontWeight: 1100,
  fontSize: 13,
};

const objectionTextView = {
  marginTop: 8,
  color: "#111827",
  fontWeight: 800,
  fontSize: 13,
  lineHeight: 1.5,
};

const evidenceView = {
  marginTop: 8,
  color: "#111827",
  fontWeight: 800,
  fontSize: 13,
};

const evidenceLink = {
  color: "#2563EB",
  fontWeight: 1000,
};

const hint = {
  marginTop: 8,
  fontSize: 12,
  color: "#667085",
  fontWeight: 800,
};

const warnBox = {
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #FDE68A",
  background: "#FEF3C7",
  color: "#92400E",
  fontWeight: 1000,
};

const rejectBox = {
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #FECACA",
  background: "#FEE2E2",
  color: "#991B1B",
  fontWeight: 1000,
};

const paidBox = {
  padding: "12px 14px",
  borderRadius: 14,
  border: "1px solid #BBF7D0",
  background: "#DCFCE7",
  color: "#166534",
  fontWeight: 1000,
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