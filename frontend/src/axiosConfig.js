import axios from "axios";

const instance = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    delete config.headers.Authorization;
  }

  return config;
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default instance;