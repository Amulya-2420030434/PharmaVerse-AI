import { useContext, useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { AuthContext } from "../../context/AuthContext";
import { getCurrentUser, getStoredUser } from "../../services/authService";

function ProtectedRoute({ allowedRoles, children }) {
  const parentUser = useContext(AuthContext);
  const storedToken = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const storedUser = typeof window !== "undefined" ? getStoredUser() : null;

  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(storedToken));
  const [user, setUser] = useState(() => storedUser);
  const [isReady, setIsReady] = useState(
    () => Boolean(parentUser !== undefined || !storedToken || (storedToken && storedUser)),
  );

  useEffect(() => {
    if (parentUser !== undefined) return undefined;
    let isMounted = true;

    const validateSession = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setIsReady(true);
        }
        return;
      }

      try {
        const me = await getCurrentUser();
        if (isMounted) {
          setUser(me);
          setIsAuthenticated(Boolean(me));
          setIsReady(true);
        }
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setIsReady(true);
        }
      }
    };

    validateSession();
    return () => {
      isMounted = false;
    };
  }, [parentUser]);

  if (parentUser !== undefined) {
    if (allowedRoles && !allowedRoles.includes(parentUser?.role)) {
      return <Navigate to="/dashboard" replace />;
    }
    return children || <Outlet />;
  }

  if (!isReady) {
    return (
      <div className="min-h-screen bg-[#f7f8fa] px-4 py-16 text-center text-sm text-slate-500">
        Verifying session...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const currentUser = user || getStoredUser();
  if (allowedRoles && !allowedRoles.includes(currentUser?.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <AuthContext.Provider value={currentUser}>
      {children || <Outlet />}
    </AuthContext.Provider>
  );
}

export default ProtectedRoute;
