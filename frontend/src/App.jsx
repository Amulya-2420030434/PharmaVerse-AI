import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/common/ProtectedRoute";
import MainLayout from "./layouts/MainLayout";
import AI from "./pages/AI";
import AIResearch from "./pages/AIResearch";
import Audit from "./pages/Audit";
import Batches from "./pages/Batches";
import Blockchain from "./pages/Blockchain";
import Dashboard from "./pages/Dashboard";
import AdminDashboard from "./pages/AdminDashboard";
import DrugDetails from "./pages/DrugDetails";
import Drugs from "./pages/Drugs";
import Identities from "./pages/Identities";
import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyEmail from "./pages/VerifyEmail";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import TwoFactorVerify from "./pages/TwoFactorVerify";
import Settings from "./pages/Settings";
import Profile from "./pages/Profile";
import ShipmentDetails from "./pages/ShipmentDetails";
import Shipments from "./pages/Shipments";
import Simulation from "./pages/Simulation";
import Verification from "./pages/Verification";
import { ROLE_ACCESS } from "./utils/roles";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email/:token" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:token" element={<ResetPassword />} />
        <Route path="/two-factor" element={<TwoFactorVerify />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.all}><Dashboard /></ProtectedRoute>} />
            <Route element={<ProtectedRoute allowedRoles={["ADMIN"]} />}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
            </Route>
            <Route path="/drugs" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.drugs}><Drugs /></ProtectedRoute>} />
            <Route path="/drugs/:id" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.drugs}><DrugDetails /></ProtectedRoute>} />
            <Route path="/batches" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.batches}><Batches /></ProtectedRoute>} />
            <Route path="/identities" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.identity}><Identities /></ProtectedRoute>} />
            <Route path="/shipments" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.shipments}><Shipments /></ProtectedRoute>} />
            <Route path="/shipments/:id" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.shipments}><ShipmentDetails /></ProtectedRoute>} />
            <Route path="/verification" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.verification}><Verification /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.oversight}><Audit /></ProtectedRoute>} />
            <Route path="/blockchain" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.oversight}><Blockchain /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.ai}><AI /></ProtectedRoute>} />
            <Route path="/ai-research" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.oversight}><AIResearch /></ProtectedRoute>} />
            <Route path="/simulation" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.simulation}><Simulation /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.all}><Profile /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute allowedRoles={ROLE_ACCESS.all}><Settings /></ProtectedRoute>} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
