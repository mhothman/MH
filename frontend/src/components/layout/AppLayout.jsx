import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { getOrganizations } from "../../api/organizations";
import { getNotifications, markNotificationRead, markAllNotificationsRead } from "../../api/notifications";
import { connectNotificationsWS } from "../../api/websocket";
import { getMyPermissions, hasPermission, Permission } from "../../api";
import { Button } from "../ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { GlobalTimerIndicator } from "../TimeTracker";
import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  LogOut,
  Bell,
  Sun,
  Moon,
  Menu,
  X,
  ChevronDown,
  Building2,
  Plus,
  BarChart3,
  Users,
  Zap,
  Shield,
  PieChart,
  CheckCheck,
  ExternalLink,
  FileText,
  DollarSign,
  Activity,
  FileBarChart,
} from "lucide-react";
import { toast } from "sonner";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const AppLayout = ({ children }) => {
  const { user, logout, token } = useAuth();
  const { branding, loadBranding, theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [organizations, setOrganizations] = useState([]);
  const [currentOrg, setCurrentOrg] = useState(() => {
    // Initialize from localStorage if available
    const saved = localStorage.getItem('proflow_current_org');
    return saved ? JSON.parse(saved) : null;
  });
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userPermissions, setUserPermissions] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Load organizations
  const loadOrganizations = useCallback(async () => {
    try {
      const orgs = await getOrganizations();
      setOrganizations(orgs);
      if (orgs.length > 0) {
        setCurrentOrg((prev) => {
          // If we have a saved org, verify it still exists in the list
          if (prev) {
            const stillExists = orgs.find(o => o.org_id === prev.org_id);
            if (stillExists) {
              // Update with latest data from server
              localStorage.setItem('proflow_current_org', JSON.stringify(stillExists));
              return stillExists;
            }
          }
          // Default to first org
          localStorage.setItem('proflow_current_org', JSON.stringify(orgs[0]));
          return orgs[0];
        });
      }
    } catch (error) {
      console.error("Failed to load organizations:", error);
    }
  }, []);

  // Load notifications
  const loadNotifications = useCallback(async () => {
    try {
      const notifs = await getNotifications(true);
      setNotifications(notifs);
      setUnreadCount(notifs.length);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    }
  }, []);

  // Load permissions for current org
  const loadPermissions = useCallback(async () => {
    if (!currentOrg?.org_id) return;
    try {
      const data = await getMyPermissions(currentOrg.org_id);
      // API returns {role: "finance", permissions: [...]}
      const perms = data?.permissions || data || [];
      setUserPermissions(perms);
    } catch (error) {
      console.error("Failed to load permissions:", error);
      setUserPermissions([]);
    }
  }, [currentOrg?.org_id]);

  // WebSocket connection for real-time notifications
  const connectWebSocket = useCallback(() => {
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = connectNotificationsWS(
      token,
      (data) => {
        // Handle incoming notification
        if (data.type === "notification") {
          const newNotif = data.data;
          setNotifications((prev) => [newNotif, ...prev].slice(0, 50));
          setUnreadCount((prev) => prev + 1);
          
          // Show toast for the new notification
          toast(newNotif.title, {
            description: newNotif.message,
            action: newNotif.link ? {
              label: "View",
              onClick: () => navigate(newNotif.link),
            } : undefined,
          });
        }
      },
      null // Don't auto-reconnect on error - handle in onclose
    );

    wsRef.current = ws;
  }, [token, navigate]);

  // Reconnection logic
  useEffect(() => {
    if (!wsRef.current) return;

    const handleClose = () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(() => {
        wsRef.current = null;
        connectWebSocket();
      }, 5000);
    };

    wsRef.current.onclose = handleClose;
    wsRef.current.onerror = handleClose;

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
      }
    };
  }, [connectWebSocket]);

  // Initial data load (triggered once on mount)
  useEffect(() => {
    const initializeData = async () => {
      await Promise.all([loadOrganizations(), loadNotifications()]);
    };
    initializeData();
  }, []); // Empty dep array - only run on mount

  // Load permissions when org changes
  useEffect(() => {
    if (currentOrg?.org_id) {
      loadPermissions();
    }
  }, [currentOrg?.org_id, loadPermissions]);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  // Load branding when organization changes
  useEffect(() => {
    if (currentOrg?.org_id) {
      loadBranding(currentOrg.org_id);
    }
  }, [currentOrg?.org_id, loadBranding]);

  const handleLogout = async () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    localStorage.removeItem('proflow_current_org');
    localStorage.removeItem('proflow_branding');
    await logout();
    navigate("/");
  };

  const handleMarkAsRead = async (notificationId) => {
    try {
      await markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) =>
          n.notification_id === notificationId ? { ...n, read: true } : n
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  };

  const handleNotificationClick = (notif) => {
    if (!notif.read) {
      handleMarkAsRead(notif.notification_id);
    }
    if (notif.link) {
      navigate(notif.link);
      setNotificationsOpen(false);
    }
  };

  const navItems = [
    { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
    { icon: FolderKanban, label: "Projects", path: "/projects" },
    { icon: FileText, label: "Documents", path: "/documents" },
    { icon: Users, label: "Customers", path: "/customers" },
    { icon: BarChart3, label: "Reports", path: "/reports" },
    { icon: DollarSign, label: "Budget Approvals", path: "/budget-approvals", financeOnly: true },
    { icon: PieChart, label: "Executive", path: "/executive-dashboard" },
    { icon: Activity, label: "API Metrics", path: "/api-metrics" },
    { icon: Zap, label: "Automations", path: "/automations" },
    { icon: Shield, label: "Audit Logs", path: "/audit-logs" },
    { icon: Settings, label: "Settings", path: "/settings" },
  ];

  const isActive = (path) => location.pathname === path;

  const getInitials = (name) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="min-h-screen bg-background" data-testid="app-layout">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full w-64 bg-card border-r border-border flex flex-col z-50 transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          <Link to="/dashboard" className="flex items-center gap-2">
            {branding?.logo_url ? (
              <img 
                src={`${API_URL}${branding.logo_url}`} 
                alt={branding?.organization_name || 'Organization'} 
                className="h-8 w-auto max-w-[140px] object-contain"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
            ) : null}
            <div 
              className={`w-8 h-8 rounded-md flex items-center justify-center ${branding?.logo_url ? 'hidden' : ''}`}
              style={{ backgroundColor: branding?.primary_color || '#0f172a' }}
            >
              <span className="text-white font-bold text-sm">
                {(branding?.organization_name || 'P').charAt(0).toUpperCase()}
              </span>
            </div>
            {!branding?.logo_url && (
              <span className="font-heading font-bold text-lg">{branding?.organization_name || 'ProFlow'}</span>
            )}
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 hover:bg-accent rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Organization Selector */}
        <div className="p-4 border-b border-border">
          {organizations.length > 1 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  data-testid="org-selector"
                >
                  <div className="flex items-center gap-2 truncate">
                    <Building2 className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{currentOrg?.name || "Organization"}</span>
                  </div>
                  <ChevronDown className="w-4 h-4 flex-shrink-0" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                {organizations.map((org) => (
                  <DropdownMenuItem
                    key={org.org_id}
                    onClick={() => {
                      setCurrentOrg(org);
                      localStorage.setItem('proflow_current_org', JSON.stringify(org));
                    }}
                    className="cursor-pointer"
                  >
                    <Building2 className="w-4 h-4 mr-2" />
                    {org.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 rounded-md">
              <Building2 className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <span className="font-medium truncate">{currentOrg?.name || "Organization"}</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems
            .filter(item => !item.financeOnly || hasPermission(userPermissions, Permission.BUDGET_APPROVE))
            .map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link ${isActive(item.path) ? "active" : ""}`}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3">
            <Avatar className="w-9 h-9">
              <AvatarImage src={user?.picture} />
              <AvatarFallback>{getInitials(user?.name)}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Header */}
      <header className="fixed top-0 right-0 h-16 bg-card/80 backdrop-blur-xl border-b border-border flex items-center justify-between px-4 lg:px-6 z-30 left-0 lg:left-64">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 hover:bg-accent rounded-md"
            data-testid="mobile-menu-btn"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Global Timer Indicator */}
          <GlobalTimerIndicator />

          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            data-testid="theme-toggle"
          >
            {theme === "dark" ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
          </Button>

          {/* Notifications */}
          <DropdownMenu open={notificationsOpen} onOpenChange={setNotificationsOpen}>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative" data-testid="notifications-btn">
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="notification-badge" data-testid="notification-badge">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <div className="p-3 border-b border-border flex items-center justify-between">
                <h4 className="font-semibold">Notifications</h4>
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs h-7"
                    onClick={handleMarkAllAsRead}
                    data-testid="mark-all-read-btn"
                  >
                    <CheckCheck className="w-3 h-3 mr-1" />
                    Mark all read
                  </Button>
                )}
              </div>
              <div className="max-h-[350px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground text-sm">
                    <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    No notifications
                  </div>
                ) : (
                  notifications.slice(0, 10).map((notif) => (
                    <div
                      key={notif.notification_id}
                      className={`p-3 hover:bg-accent cursor-pointer border-b border-border last:border-0 transition-colors ${
                        !notif.read ? "bg-primary/5" : ""
                      }`}
                      onClick={() => handleNotificationClick(notif)}
                      data-testid={`notification-item-${notif.notification_id}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className={`text-sm ${!notif.read ? "font-semibold" : "font-medium"}`}>
                              {notif.title}
                            </p>
                            {!notif.read && (
                              <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {notif.message}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1 opacity-70">
                            {notif.created_at && new Date(notif.created_at).toLocaleString()}
                          </p>
                        </div>
                        {notif.link && (
                          <ExternalLink className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="p-2 border-t border-border">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => {
                    navigate("/notifications");
                    setNotificationsOpen(false);
                  }}
                  data-testid="view-all-notifications-btn"
                >
                  View all notifications
                </Button>
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full" data-testid="user-menu-btn">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={user?.picture} />
                  <AvatarFallback>{getInitials(user?.name)}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <div className="px-2 py-1.5">
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/settings")} className="cursor-pointer">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive">
                <LogOut className="w-4 h-4 mr-2" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Main content */}
      <main className="lg:ml-64 pt-16 min-h-screen" data-testid="main-content">
        <div className="p-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
};
