import { Navigate, Route, Routes } from "react-router-dom"
import { AdminRoute, Shell } from "./components/Shell"
import { AdminView } from "./views/AdminView"
import { DashboardView } from "./views/DashboardView"

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<DashboardView />} />
        <Route
          path="admin"
          element={
            <AdminRoute>
              <AdminView />
            </AdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
