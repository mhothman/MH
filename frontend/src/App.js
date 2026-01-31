import { useEffect, useState, useRef, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import "@/App.css";

// Context
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AppDataProvider } from "./context/AppDataContext";

// Eager load - critical path pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Lazy load - non-critical pages (code splitting)
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage"));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const CustomersPage = lazy(() => import("./pages/CustomersPage"));
const CustomerDetailPage = lazy(() => import("./pages/CustomerDetailPage"));
const AutomationsPage = lazy(() => import("./pages/AutomationsPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const ExecutiveDashboardPage = lazy(() => import("./pages/ExecutiveDashboardPage"));
const DocumentsPage = lazy(() => import("./pages/DocumentsPage"));
const NotificationCenterPage = lazy(() => import("./pages/NotificationCenterPage"));
const BudgetApprovalsPage = lazy(() => import("./pages/BudgetApprovalsPage"));
const CustomReportsPage = lazy(() => import("./pages/CustomReportsPage"));
const APIMetricsPage = lazy(() => import("./pages/APIMetricsPage"));

// Components
import { AppLayout } from "./components/layout/AppLayout";
import { LoadingSpinner } from "./components/ui/loading-spinner";

// Loading fallback for lazy components
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <LoadingSpinner size="lg" />
  </div>
);

// Error Boundary for catching component errors
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="text-center p-8">
            <h2 className="text-2xl font-bold text-destructive mb-4">Something went wrong</h2>
            <p className="text-muted-foreground mb-4">Please refresh the page or try again later.</p>
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// Import React for ErrorBoundary class
import React from "react";

// Auth Callback Component for Google OAuth
// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const AuthCallback = () => {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = location.hash;
      const sessionId = new URLSearchParams(hash.replace('#', '?')).get('session_id');
      
      if (!sessionId) {
        navigate('/login');
        return;
      }

      try {
        const API_URL = process.env.REACT_APP_BACKEND_URL;
        const response = await fetch(`${API_URL}/api/auth/session`, {
          method: 'GET',
          headers: {
            'X-Session-ID': sessionId,
          },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Session validation failed');
        }

        const userData = await response.json();
        // Navigate to dashboard with user data to skip auth check
        navigate('/dashboard', { state: { user: userData }, replace: true });
      } catch (error) {
        console.error('Auth callback error:', error);
        navigate('/login');
      }
    };

    processAuth();
  }, [navigate, location]);

  return <PageLoader />;
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading, checkAuth } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(!location.state?.user);

  useEffect(() => {
    // If user data passed from AuthCallback, skip auth check
    if (location.state?.user) {
      setIsChecking(false);
      return;
    }

    const verifyAuth = async () => {
      const isAuthenticated = await checkAuth();
      setIsChecking(false);
      if (!isAuthenticated) {
        navigate('/login', { replace: true });
      }
    };

    verifyAuth();
  }, [checkAuth, navigate, location.state]);

  if (loading || isChecking) {
    return <PageLoader />;
  }

  if (!user && !location.state?.user) {
    return <Navigate to="/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

// Router Component with Suspense for lazy loading
const AppRouter = () => {
  const location = useLocation();

  // Check URL fragment for session_id synchronously during render
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public Routes - Eager loaded */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Routes - Lazy loaded */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
          <Route path="/customers" element={<ProtectedRoute><CustomersPage /></ProtectedRoute>} />
          <Route path="/customers/:customerId" element={<ProtectedRoute><CustomerDetailPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/automations" element={<ProtectedRoute><AutomationsPage /></ProtectedRoute>} />
          <Route path="/audit-logs" element={<ProtectedRoute><AuditLogsPage /></ProtectedRoute>} />
          <Route path="/executive-dashboard" element={<ProtectedRoute><ExecutiveDashboardPage /></ProtectedRoute>} />
          <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
          <Route path="/notifications" element={<ProtectedRoute><NotificationCenterPage /></ProtectedRoute>} />
          <Route path="/budget-approvals" element={<ProtectedRoute><BudgetApprovalsPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppDataProvider>
          <BrowserRouter>
            <AppRouter />
            <Toaster richColors position="top-right" />
          </BrowserRouter>
        </AppDataProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
