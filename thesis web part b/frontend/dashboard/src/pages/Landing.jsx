import { Link } from "react-router-dom";
import AdminStyleLayout from "../components/AdminStyleLayout";

export default function Landing() {
  return (
    <AdminStyleLayout
      title="Intelligent Traffic Violation Detection System"
      subtitle="Computer vision, digital ticketing, admin verification, and citizen services"
      showHomeOnly={false}
      hideRightActions={true}
    >
      <div style={page}>
        <section style={hero}>
          <div style={heroLeft}>
            <div style={badge}>Computer Vision • Secure Ticketing • Audit Logs</div>

            <h1 style={title}>
              Automated Traffic Violation Detection and Digital Ticketing
            </h1>

            <p style={subtitle}>
              A complete web platform for detecting traffic violations, reviewing
              tickets, handling citizen objections, managing payments, archiving paid
              records, and tracking all actions through audit logs.
            </p>

            <div style={actions}>
              <Link to="/owner/login" style={primaryBtn}>Citizen Portal</Link>
              <Link to="/admin/login" style={darkBtn}>Admin Login</Link>
            </div>

            <div style={trustRow}>
              <span style={chip}>JWT Protected</span>
              <span style={chip}>Objection Workflow</span>
              <span style={chip}>Archive System</span>
              <span style={chip}>Audit Log</span>
            </div>
          </div>

          <div style={heroPanel}>
            <div style={panelTop}>
              <div>
                <div style={panelLabel}>System Overview</div>
                <div style={panelTitle}>Violation Lifecycle</div>
              </div>
              <div style={statusDot}>Active</div>
            </div>

            <Flow n="01" title="Detect" text="Computer vision detects violation evidence." />
            <Flow n="02" title="Review" text="Admin verifies and approves or rejects the ticket." />
            <Flow n="03" title="Object / Pay" text="Citizen can dispute with evidence or proceed to payment." />
            <Flow n="04" title="Archive" text="Paid records move to archive and all actions are logged." />
          </div>
        </section>

        <section style={statsGrid}>
          <Stat value="AI" label="Violation Detection" />
          <Stat value="JWT" label="Secure Admin Access" />
          <Stat value="PDF" label="Receipt Generation" />
          <Stat value="Logs" label="Action Tracking" />
        </section>

        <section style={section}>
          <div style={eyebrow}>Core Modules</div>
          <h2 style={sectionTitle}>Professional workflow for traffic ticket management</h2>

          <div style={modulesGrid}>
            <Module icon="📸" title="Detection" text="Violations are created with evidence from the detection module." />
            <Module icon="🛡️" title="Admin Review" text="Admin reviews, approves, rejects, and handles objections." />
            <Module icon="👤" title="Citizen Portal" text="Citizens view tickets, submit objections, or continue to payment." />
            <Module icon="📝" title="Citizen Objections" text="Citizens can attach image evidence with their dispute." />
            <Module icon="📦" title="Archive" text="Paid records are removed from the active dashboard." />
            <Module icon="📊" title="Audit Log" text="Important actions are recorded for accountability." />
          </div>
        </section>

        <section style={workflow}>
          <div>
            <div style={eyebrow}>Process</div>
            <h2 style={sectionTitle}>From detection to final decision</h2>
            <p style={workflowDesc}>
              The system follows a structured lifecycle: detect, review, object,
              pay, archive, and log every critical action.
            </p>
          </div>

          <div style={steps}>
            <Step n="1" title="Detection" text="Violation is detected and stored." />
            <Step n="2" title="Admin Review" text="Admin validates the violation." />
            <Step n="3" title="Citizen Action" text="Citizen pays or submits objection." />
            <Step n="4" title="Finalization" text="Decision is finalized and record is archived if paid." />
          </div>
        </section>

        <section style={cta}>
          <div>
            <h2 style={ctaTitle}>Start using the system</h2>
            <p style={ctaText}>Choose the correct portal to continue.</p>
          </div>

          <div style={actions}>
            <Link to="/owner/login" style={lightBtn}>Citizen Portal</Link>
            <Link to="/admin/login" style={whiteDarkBtn}>Admin Dashboard</Link>
          </div>
        </section>
      </div>
    </AdminStyleLayout>
  );
}

function Flow({ n, title, text }) {
  return (
    <div style={flowItem}>
      <div style={flowNum}>{n}</div>
      <div>
        <div style={flowTitle}>{title}</div>
        <div style={flowText}>{text}</div>
      </div>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div style={statCard}>
      <div style={statValue}>{value}</div>
      <div style={statLabel}>{label}</div>
    </div>
  );
}

function Module({ icon, title, text }) {
  return (
    <div style={moduleCard}>
      <div style={moduleIcon}>{icon}</div>
      <div style={moduleTitle}>{title}</div>
      <div style={moduleText}>{text}</div>
    </div>
  );
}

function Step({ n, title, text }) {
  return (
    <div style={stepCard}>
      <div style={stepNum}>{n}</div>
      <div>
        <div style={stepTitle}>{title}</div>
        <div style={stepText}>{text}</div>
      </div>
    </div>
  );
}

const page = {
  width: "100%",
  maxWidth: 1280,
  margin: "0 auto",
  display: "grid",
  gap: 22,
};

const hero = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 20,
  alignItems: "stretch",
};

const heroLeft = {
  borderRadius: 26,
  padding: 30,
  background: "linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 48%, #EFF6FF 100%)",
  border: "1px solid #E5E7EB",
  boxShadow: "0 24px 70px rgba(15,23,42,0.10)",
};

const badge = {
  display: "inline-flex",
  padding: "8px 12px",
  borderRadius: 999,
  background: "#DBEAFE",
  color: "#1E40AF",
  fontSize: 12,
  fontWeight: 1000,
};

const title = {
  margin: "18px 0 0",
  maxWidth: 760,
  fontSize: "clamp(30px, 4vw, 42px)",
  lineHeight: 1.1,
  fontWeight: 1200,
  letterSpacing: "-1px",
  color: "#0F172A",
};

const subtitle = {
  marginTop: 16,
  maxWidth: 720,
  color: "#475569",
  fontSize: "clamp(14px, 2vw, 17px)",
  lineHeight: 1.75,
  fontWeight: 800,
};

const actions = {
  display: "flex",
  gap: 12,
  flexWrap: "wrap",
  alignItems: "center",
};

const primaryBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  background: "#2563EB",
  color: "#FFFFFF",
  textDecoration: "none",
  fontWeight: 1000,
};

const darkBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  background: "#0F172A",
  color: "#FFFFFF",
  textDecoration: "none",
  fontWeight: 1000,
};

const trustRow = {
  marginTop: 22,
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const chip = {
  padding: "7px 10px",
  borderRadius: 999,
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  color: "#334155",
  fontSize: 12,
  fontWeight: 900,
};

const heroPanel = {
  borderRadius: 26,
  padding: 22,
  background: "#0F172A",
  color: "#FFFFFF",
  boxShadow: "0 24px 70px rgba(15,23,42,0.20)",
};

const panelTop = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  alignItems: "center",
  marginBottom: 16,
};

const panelLabel = {
  color: "#93C5FD",
  fontSize: 12,
  fontWeight: 900,
};

const panelTitle = {
  marginTop: 4,
  color: "#FFFFFF",
  fontSize: 20,
  fontWeight: 1100,
};

const statusDot = {
  padding: "6px 10px",
  borderRadius: 999,
  background: "rgba(34,197,94,0.15)",
  color: "#86EFAC",
  fontSize: 12,
  fontWeight: 1000,
};

const flowItem = {
  display: "flex",
  gap: 12,
  padding: 13,
  borderRadius: 18,
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.09)",
  marginTop: 10,
};

const flowNum = {
  minWidth: 42,
  height: 42,
  borderRadius: 14,
  background: "#2563EB",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 1100,
};

const flowTitle = {
  fontWeight: 1100,
  color: "#FFFFFF",
};

const flowText = {
  marginTop: 4,
  color: "#CBD5E1",
  fontSize: 13,
  lineHeight: 1.5,
  fontWeight: 750,
};

const statsGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: 14,
};

const statCard = {
  padding: 18,
  borderRadius: 20,
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  boxShadow: "0 18px 45px rgba(15,23,42,0.07)",
};

const statValue = {
  fontSize: 26,
  fontWeight: 1200,
  color: "#0F172A",
};

const statLabel = {
  marginTop: 6,
  color: "#64748B",
  fontSize: 13,
  fontWeight: 850,
};

const section = {
  padding: 22,
  borderRadius: 26,
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  boxShadow: "0 20px 55px rgba(15,23,42,0.07)",
};

const eyebrow = {
  color: "#2563EB",
  fontSize: 12,
  fontWeight: 1100,
  textTransform: "uppercase",
  letterSpacing: 0.8,
};

const sectionTitle = {
  margin: "6px 0 16px",
  color: "#0F172A",
  fontSize: "clamp(22px, 3vw, 28px)",
  lineHeight: 1.2,
  fontWeight: 1200,
};

const modulesGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
  gap: 14,
};

const moduleCard = {
  borderRadius: 20,
  padding: 18,
  background: "#F8FAFC",
  border: "1px solid #E5E7EB",
};

const moduleIcon = {
  width: 42,
  height: 42,
  borderRadius: 14,
  background: "#FFFFFF",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 22,
};

const moduleTitle = {
  marginTop: 14,
  color: "#0F172A",
  fontSize: 16,
  fontWeight: 1100,
};

const moduleText = {
  marginTop: 8,
  color: "#64748B",
  fontSize: 13,
  lineHeight: 1.65,
  fontWeight: 800,
};

const workflow = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 18,
  padding: 22,
  borderRadius: 26,
  background: "#F8FAFC",
  border: "1px solid #E5E7EB",
};

const workflowDesc = {
  marginTop: 12,
  color: "#64748B",
  fontSize: 15,
  lineHeight: 1.7,
  fontWeight: 800,
};

const steps = {
  display: "grid",
  gap: 12,
};

const stepCard = {
  display: "flex",
  gap: 12,
  padding: 15,
  borderRadius: 20,
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
};

const stepNum = {
  width: 38,
  height: 38,
  borderRadius: 14,
  background: "#0F172A",
  color: "#FFFFFF",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 1100,
};

const stepTitle = {
  color: "#0F172A",
  fontWeight: 1100,
};

const stepText = {
  marginTop: 4,
  color: "#64748B",
  fontSize: 13,
  lineHeight: 1.55,
  fontWeight: 800,
};

const cta = {
  borderRadius: 26,
  padding: 24,
  background: "linear-gradient(135deg, #2563EB 0%, #0F172A 100%)",
  color: "#FFFFFF",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 16,
  flexWrap: "wrap",
};

const ctaTitle = {
  margin: 0,
  fontSize: 26,
  fontWeight: 1200,
};

const ctaText = {
  margin: "6px 0 0",
  color: "#DBEAFE",
  fontWeight: 850,
};

const lightBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  background: "#FFFFFF",
  color: "#1E40AF",
  textDecoration: "none",
  fontWeight: 1000,
};

const whiteDarkBtn = {
  padding: "13px 18px",
  borderRadius: 14,
  background: "#0F172A",
  color: "#FFFFFF",
  textDecoration: "none",
  fontWeight: 1000,
};