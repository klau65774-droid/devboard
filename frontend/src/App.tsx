import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Board from "./pages/Board";
import Dashboard from "./pages/Dashboard";

// Redirects to /login when there is no stored JWT.
function RequireAuth({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/board"
        element={
          <RequireAuth>
            <Board />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
