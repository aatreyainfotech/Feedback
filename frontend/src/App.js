import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";

import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import Temples from "./pages/Temples";
import Officers from "./pages/Officers";
import Services from "./pages/Services";
import FeedbackMonitoring from "./pages/FeedbackMonitoring";
import WhatsAppLogs from "./pages/WhatsAppLogs";
import Reports from "./pages/Reports";
import Administration from "./pages/Administration";
import SuperAdmin from "./pages/SuperAdmin";
import OfficerLogin from "./pages/OfficerLogin";
import OfficerDashboard from "./pages/OfficerDashboard";
import DisplayScreen from "./pages/DisplayScreen";
import PublicFeedbackSubmit from "./pages/PublicFeedbackSubmit";
import TempleSetup from "./pages/TempleSetup";
import AdminLayout from "./components/AdminLayout";
import OfficerLayout from "./components/OfficerLayout";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/setup-temple" replace />} />
          <Route path="/login" element={<AdminLogin />} />
          <Route path="/officer/login" element={<OfficerLogin />} />
          
          {/* Temple Setup (Tablet Registration) */}
          <Route path="/setup-temple" element={<TempleSetup />} />
          
          {/* Public Feedback Submission */}
          <Route path="/submit-feedback" element={<PublicFeedbackSubmit />} />
          
          {/* Admin Routes */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="dashboard" element={<AdminDashboard />} />
            <Route path="temples" element={<Temples />} />
            <Route path="officers" element={<Officers />} />
            <Route path="services" element={<Services />} />
            <Route path="feedback" element={<FeedbackMonitoring />} />
            <Route path="whatsapp-logs" element={<WhatsAppLogs />} />
            <Route path="reports" element={<Reports />} />
            <Route path="administration" element={<Administration />} />
            <Route path="super-admin" element={<SuperAdmin />} />
          </Route>
          
          {/* Officer Routes */}
          <Route path="/officer" element={<OfficerLayout />}>
            <Route index element={<Navigate to="/officer/dashboard" replace />} />
            <Route path="dashboard" element={<OfficerDashboard />} />
          </Route>
          
          {/* Display Screen */}
          <Route path="/display" element={<DisplayScreen />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;