import { Navigate } from "react-router-dom";

export default function OwnerGuard({ children }) {
  const plate = localStorage.getItem("owner_plate");
  if (!plate) return <Navigate to="/owner/login" replace />;
  return children;
}
