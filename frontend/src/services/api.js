import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function login(username, password) {
  const { data } = await api.post("/token/", { username, password });
  localStorage.setItem("access", data.access);
  return currentUser();
}

export const currentUser = async () => (await api.get("/me/")).data;
export const logout = () => localStorage.removeItem("access");
export const hasToken = () => !!localStorage.getItem("access");

export function errMsg(e) {
  const d = e.response?.data;
  if (!d) return "Cannot reach the server. Check that the API is running.";
  if (d.detail) return d.detail;
  return Object.entries(d).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join(" · ");
}

export default api;
