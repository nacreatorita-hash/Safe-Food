import { Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/layout/AppShell";
import Home from "@/pages/Home";
import Recalls from "@/pages/Recalls";
import RecallDetail from "@/pages/RecallDetail";
import Marine from "@/pages/Marine";
import Notifications from "@/pages/Notifications";
import Sources from "@/pages/Sources";
import InstallApp from "@/pages/InstallApp";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import AdminGuard from "@/components/layout/AdminGuard";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/richiami" element={<Recalls />} />
        <Route path="/recalls" element={<Recalls />} />
        <Route path="/richiami/:id" element={<RecallDetail />} />
        <Route path="/mare" element={<Marine />} />
        <Route path="/sea" element={<Marine />} />
        <Route path="/fao" element={<Marine />} />
        <Route path="/notifiche" element={<Notifications />} />
        <Route path="/fonti" element={<Sources />} />
        <Route path="/installa" element={<InstallApp />} />
        <Route path="/login" element={<Login />} />
        <Route path="/admin" element={<AdminGuard><Admin /></AdminGuard>} />
        <Route path="*" element={<Home />} />
      </Routes>
      <Toaster richColors />
    </AppShell>
  );
}
