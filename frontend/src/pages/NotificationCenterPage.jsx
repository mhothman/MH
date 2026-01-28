/**
 * NotificationCenterPage - Full notification history and management
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  getNotificationsPaginated,
  getNotificationTypes,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
} from "../api/notifications";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  Trash2,
  ExternalLink,
  MoreVertical,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Settings,
  ClipboardList,
  FileText,
  FolderKanban,
  ShieldCheck,
  Info,
} from "lucide-react";

// Notification type icons mapping
const typeIcons = {
  task_assigned: ClipboardList,
  task_status_changed: ClipboardList,
  task_due_soon: ClipboardList,
  task_overdue: ClipboardList,
  task_comment: ClipboardList,
  task_mention: ClipboardList,
  document_approval_requested: FileText,
  document_approved: FileText,
  document_rejected: FileText,
  document_status_changed: FileText,
  project_member_added: FolderKanban,
  project_member_removed: FolderKanban,
  project_status_changed: FolderKanban,
  project_milestone_reached: FolderKanban,
  approval_requested: ShieldCheck,
  approval_approved: ShieldCheck,
  approval_rejected: ShieldCheck,
  system_announcement: Info,
  weekly_digest: Info,
};

// Notification type colors
const typeColors = {
  task_assigned: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  task_overdue: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  task_due_soon: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  approval_approved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  approval_rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  document_approved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  document_rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  project_member_added: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
};

export default function NotificationCenterPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [notifications, setNotifications] = useState([]);
  const [notificationTypes, setNotificationTypes] = useState({});
  const [categories, setCategories] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  
  // Filters
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "all");
  const [selectedType, setSelectedType] = useState(searchParams.get("type") || "all");
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get("category") || "all");

  // Define loadNotificationTypes function
  const loadNotificationTypes = async () => {
    try {
      const data = await getNotificationTypes();
      setNotificationTypes(data.types || {});
      setCategories(data.categories || {});
    } catch (error) {
      console.error("Failed to load notification types:", error);
    }
  };

  // Define loadNotifications with useCallback before useEffect
  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      
      const unreadOnly = activeTab === "unread";
      const type = selectedType !== "all" ? selectedType : null;
      
      const data = await getNotificationsPaginated(page, pageSize, unreadOnly, type);
      
      setNotifications(data.notifications || []);
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
    } catch (error) {
      console.error("Failed to load notifications:", error);
      toast.error("Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, activeTab, selectedType]);

  // Load notification types on mount
  useEffect(() => {
    loadNotificationTypes();
  }, []);

  // Load notifications when filters change
  useEffect(() => {
    loadNotifications();
  }, [page, activeTab, selectedType, loadNotifications]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadNotifications();
    setRefreshing(false);
    toast.success("Notifications refreshed");
  };

  const handleMarkAsRead = async (notificationId) => {
    try {
      await markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) =>
          n.notification_id === notificationId ? { ...n, read: true } : n
        )
      );
    } catch (error) {
      console.error("Failed to mark as read:", error);
      toast.error("Failed to mark notification as read");
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      toast.success("All notifications marked as read");
    } catch (error) {
      console.error("Failed to mark all as read:", error);
      toast.error("Failed to mark all as read");
    }
  };

  const handleDelete = async (notificationId) => {
    try {
      await deleteNotification(notificationId);
      setNotifications((prev) =>
        prev.filter((n) => n.notification_id !== notificationId)
      );
      toast.success("Notification deleted");
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete notification");
    }
  };

  const handleNotificationClick = (notification) => {
    if (!notification.read) {
      handleMarkAsRead(notification.notification_id);
    }
    if (notification.link) {
      navigate(notification.link);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setPage(1);
    setSearchParams({ tab, type: selectedType, category: selectedCategory });
  };

  const handleTypeChange = (type) => {
    setSelectedType(type);
    setPage(1);
    setSearchParams({ tab: activeTab, type, category: selectedCategory });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 minute
    if (diff < 60000) return "Just now";
    // Less than 1 hour
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    // Less than 24 hours
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    // Less than 7 days
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
    
    return date.toLocaleDateString();
  };

  const getTypeLabel = (type) => {
    return notificationTypes[type]?.label || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getTypeIcon = (type) => {
    const Icon = typeIcons[type] || Bell;
    return Icon;
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="notification-center-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
            <Bell className="w-7 h-7" />
            Notification Center
          </h1>
          <p className="text-muted-foreground mt-1">
            {total} total notifications {unreadCount > 0 && `(${unreadCount} unread)`}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            data-testid="refresh-notifications-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleMarkAllAsRead}
            disabled={unreadCount === 0}
            data-testid="mark-all-read-btn"
          >
            <CheckCheck className="w-4 h-4 mr-2" />
            Mark All Read
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings?tab=preferences")}
            data-testid="notification-settings-btn"
          >
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full sm:w-auto">
              <TabsList>
                <TabsTrigger value="all" data-testid="tab-all">All</TabsTrigger>
                <TabsTrigger value="unread" data-testid="tab-unread">
                  Unread
                  {unreadCount > 0 && (
                    <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                      {unreadCount}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>
            </Tabs>
            
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <Select value={selectedType} onValueChange={handleTypeChange}>
                <SelectTrigger className="w-full sm:w-[200px]" data-testid="type-filter">
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {Object.entries(categories).map(([category, types]) => (
                    <div key={category}>
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        {category}
                      </div>
                      {types.map((type) => (
                        <SelectItem key={type.type} value={type.type}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </div>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications List */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <BellOff className="w-12 h-12 text-muted-foreground/30 mb-4" />
              <h3 className="text-lg font-medium text-muted-foreground">No notifications</h3>
              <p className="text-sm text-muted-foreground/70 mt-1">
                {activeTab === "unread" 
                  ? "You're all caught up!" 
                  : "You haven't received any notifications yet"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {notifications.map((notification) => {
                const TypeIcon = getTypeIcon(notification.type);
                const colorClass = typeColors[notification.type] || "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
                
                return (
                  <div
                    key={notification.notification_id}
                    className={`p-4 hover:bg-accent/50 transition-colors cursor-pointer ${
                      !notification.read ? "bg-primary/5" : ""
                    }`}
                    onClick={() => handleNotificationClick(notification)}
                    data-testid={`notification-item-${notification.notification_id}`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={`flex-shrink-0 p-2 rounded-lg ${colorClass}`}>
                        <TypeIcon className="w-5 h-5" />
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className={`text-sm ${!notification.read ? "font-semibold" : "font-medium"}`}>
                                {notification.title}
                              </h4>
                              {!notification.read && (
                                <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                              {notification.message}
                            </p>
                            <div className="flex items-center gap-3 mt-2">
                              <Badge variant="outline" className="text-xs">
                                {getTypeLabel(notification.type)}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(notification.created_at)}
                              </span>
                            </div>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            {notification.link && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(notification.link);
                                }}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </Button>
                            )}
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreVertical className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {!notification.read && (
                                  <DropdownMenuItem
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleMarkAsRead(notification.notification_id);
                                    }}
                                  >
                                    <Check className="w-4 h-4 mr-2" />
                                    Mark as read
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuItem
                                  className="text-destructive"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(notification.notification_id);
                                  }}
                                >
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          
          {/* Pagination */}
          {total > pageSize && (
            <div className="flex items-center justify-between p-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, total)} of {total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  data-testid="prev-page-btn"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasMore}
                  data-testid="next-page-btn"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
