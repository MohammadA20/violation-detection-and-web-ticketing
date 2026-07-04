import { Routes, Route } from "react-router-dom";

import Landing from "./pages/Landing";

import AdminLogin from "./pages/admin/AdminLogin";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminArchive from "./pages/admin/AdminArchive";

import OwnerLogin from "./pages/owner/OwnerLogin";
import OwnerTickets from "./pages/owner/OwnerTickets";
import OwnerTicketDetails from "./pages/owner/OwnerTicketDetails";
import OwnerPay from "./pages/owner/OwnerPay";
import OwnerReceipt from "./pages/owner/OwnerReceipt";

import OwnerGuard from "./components/OwnerGuard";
import AdminGuard from "./components/AdminGuard";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />

      {/* Admin */}
      <Route path="/admin/login" element={<AdminLogin />} />

      <Route
        path="/admin/dashboard"
        element={
          <AdminGuard>
            <AdminDashboard />
          </AdminGuard>
        }
      />

      <Route
        path="/admin/archive"
        element={
          <AdminGuard>
            <AdminArchive />
          </AdminGuard>
        }
      />

      {/* Owner */}
      <Route path="/owner/login" element={<OwnerLogin />} />

      <Route
        path="/owner/tickets"
        element={
          <OwnerGuard>
            <OwnerTickets />
          </OwnerGuard>
        }
      />

      <Route
        path="/owner/tickets/:id"
        element={
          <OwnerGuard>
            <OwnerTicketDetails />
          </OwnerGuard>
        }
      />

      {/* Checkout */}
      <Route
        path="/owner/pay/:id"
        element={
          <OwnerGuard>
            <OwnerPay />
          </OwnerGuard>
        }
      />

      {/* Receipt */}
      <Route
        path="/owner/receipt/:id"
        element={
          <OwnerGuard>
            <OwnerReceipt />
          </OwnerGuard>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Landing />} />
    </Routes>
  );
}