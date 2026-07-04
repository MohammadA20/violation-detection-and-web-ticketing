import { Navigate } from "react-router-dom";

export default function AdminGuard({ children }) {
  const token = localStorage.getItem("admin_token");
  const expiry = localStorage.getItem("admin_token_expiry");

  if (!token || !expiry || Date.now() > Number(expiry)) {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_token_expiry");
    return <Navigate to="/admin/login" replace />;
  }

  return children;
}