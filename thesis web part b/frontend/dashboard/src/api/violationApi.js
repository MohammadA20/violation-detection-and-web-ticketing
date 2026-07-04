const API_BASE = "http://127.0.0.1:8000/api";

export const getAllViolations = async () => {
  const res = await fetch(${API_BASE}/violations);
  return res.json();
};

export const getOwnerViolations = async (plate) => {
  const res = await fetch(${API_BASE}/owner/${plate}/violations);
  return res.json();
};

export const getViolationById = async (id) => {
  const res = await fetch(${API_BASE}/violations/${id});
  return res.json();
};

export const payViolation = async (id) => {
  const res = await fetch(${API_BASE}/violations/${id}/pay, {
    method: "POST",
  });
  return res.json();
};

export const getStats = async () => {
  const res = await fetch(${API_BASE}/stats);
  return res.json();
};