/**
 * Notifications API - Enhanced notification endpoints with preferences
 */
import { get, post, put, del } from './client';

// ==================== Notifications ====================

export const getNotifications = async (unreadOnly = false, limit = 50, type = null) => {
  let url = `/api/notifications/?unread_only=${unreadOnly}&limit=${limit}`;
  if (type) url += `&notification_type=${type}`;
  return get(url);
};

export const getNotificationsPaginated = async (page = 1, pageSize = 20, unreadOnly = false, type = null) => {
  let url = `/api/notifications/paginated?page=${page}&page_size=${pageSize}&unread_only=${unreadOnly}`;
  if (type) url += `&notification_type=${type}`;
  return get(url);
};

export const getNotificationTypes = async () => {
  return get('/api/notifications/types');
};

export const markNotificationRead = async (notificationId) => {
  return put(`/api/notifications/${notificationId}/read`, {});
};

export const markAllNotificationsRead = async () => {
  return put('/api/notifications/read-all', {});
};

export const deleteNotification = async (notificationId) => {
  return del(`/api/notifications/${notificationId}`);
};

export const getUnreadCount = async () => {
  return get('/api/notifications/unread-count');
};

// ==================== Notification Preferences ====================

export const getNotificationPreferences = async () => {
  return get('/api/notifications/preferences');
};

export const updateNotificationPreferences = async (preferences) => {
  return put('/api/notifications/preferences', preferences);
};

export const updateSinglePreference = async (notificationType, enabled, channels) => {
  return put(`/api/notifications/preferences/${notificationType}?enabled=${enabled}&channels=${channels.join(',')}`);
};

// ==================== Notification Type Constants ====================

export const NotificationTypes = {
  // Task events
  TASK_ASSIGNED: 'task_assigned',
  TASK_STATUS_CHANGED: 'task_status_changed',
  TASK_DUE_SOON: 'task_due_soon',
  TASK_OVERDUE: 'task_overdue',
  TASK_COMMENT: 'task_comment',
  TASK_MENTION: 'task_mention',
  
  // Document events
  DOCUMENT_APPROVAL_REQUESTED: 'document_approval_requested',
  DOCUMENT_APPROVED: 'document_approved',
  DOCUMENT_REJECTED: 'document_rejected',
  DOCUMENT_STATUS_CHANGED: 'document_status_changed',
  
  // Project events
  PROJECT_MEMBER_ADDED: 'project_member_added',
  PROJECT_MEMBER_REMOVED: 'project_member_removed',
  PROJECT_STATUS_CHANGED: 'project_status_changed',
  PROJECT_MILESTONE_REACHED: 'project_milestone_reached',
  
  // Approval events
  APPROVAL_REQUESTED: 'approval_requested',
  APPROVAL_APPROVED: 'approval_approved',
  APPROVAL_REJECTED: 'approval_rejected',
  
  // System events
  SYSTEM_ANNOUNCEMENT: 'system_announcement',
  WEEKLY_DIGEST: 'weekly_digest',
};

export const NotificationChannels = {
  IN_APP: 'in_app',
  EMAIL: 'email',
  BROWSER_PUSH: 'browser_push',
};
