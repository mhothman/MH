/**
 * NotificationPreferences - User notification settings component
 */
import { useState, useEffect } from "react";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  getNotificationTypes,
  NotificationChannels,
} from "../../api/notifications";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Label } from "../ui/label";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";
import { Checkbox } from "../ui/checkbox";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  Bell,
  Mail,
  Clock,
  Save,
  RefreshCw,
  ClipboardList,
  FileText,
  FolderKanban,
  ShieldCheck,
  Info,
} from "lucide-react";

// Category icons
const categoryIcons = {
  Tasks: ClipboardList,
  Documents: FileText,
  Projects: FolderKanban,
  Approvals: ShieldCheck,
  System: Info,
};

export function NotificationPreferences() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState(null);
  const [notificationTypes, setNotificationTypes] = useState({});
  const [categories, setCategories] = useState({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [prefsData, typesData] = await Promise.all([
        getNotificationPreferences(),
        getNotificationTypes(),
      ]);
      setPreferences(prefsData);
      setNotificationTypes(typesData.types || {});
      setCategories(typesData.categories || {});
    } catch (error) {
      console.error("Failed to load preferences:", error);
      toast.error("Failed to load notification preferences");
    } finally {
      setLoading(false);
    }
  };

  const handleGlobalToggle = (field, value) => {
    setPreferences((prev) => ({
      ...prev,
      [field]: value,
    }));
    setHasChanges(true);
  };

  const handleTypeToggle = (type, enabled) => {
    setPreferences((prev) => ({
      ...prev,
      preferences: {
        ...prev.preferences,
        [type]: {
          ...(prev.preferences[type] || {}),
          enabled,
        },
      },
    }));
    setHasChanges(true);
  };

  const handleChannelToggle = (type, channel, enabled) => {
    setPreferences((prev) => {
      const currentChannels = prev.preferences[type]?.channels || [NotificationChannels.IN_APP];
      let newChannels;
      
      if (enabled) {
        newChannels = [...new Set([...currentChannels, channel])];
      } else {
        newChannels = currentChannels.filter((c) => c !== channel);
        // Always keep at least in_app
        if (newChannels.length === 0) {
          newChannels = [NotificationChannels.IN_APP];
        }
      }
      
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          [type]: {
            ...(prev.preferences[type] || {}),
            channels: newChannels,
          },
        },
      };
    });
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await updateNotificationPreferences(preferences);
      setHasChanges(false);
      toast.success("Notification preferences saved");
    } catch (error) {
      console.error("Failed to save preferences:", error);
      toast.error("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    loadData();
    setHasChanges(false);
  };

  const isChannelEnabled = (type, channel) => {
    const typePrefs = preferences?.preferences?.[type];
    if (!typePrefs) return channel === NotificationChannels.IN_APP;
    return typePrefs.channels?.includes(channel) ?? (channel === NotificationChannels.IN_APP);
  };

  const isTypeEnabled = (type) => {
    const typePrefs = preferences?.preferences?.[type];
    return typePrefs?.enabled ?? true;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Failed to load notification preferences
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="notification-preferences">
      {/* Global Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notification Settings
          </CardTitle>
          <CardDescription>
            Configure how you receive notifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Email Notifications */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-muted-foreground" />
              <div>
                <Label htmlFor="email-notifications" className="text-base">
                  Email Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Receive notifications via email
                </p>
              </div>
            </div>
            <Switch
              id="email-notifications"
              checked={preferences.email_notifications_enabled}
              onCheckedChange={(checked) =>
                handleGlobalToggle("email_notifications_enabled", checked)
              }
              data-testid="email-notifications-toggle"
            />
          </div>

          {/* Quiet Hours */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-muted-foreground" />
                <div>
                  <Label htmlFor="quiet-hours" className="text-base">
                    Quiet Hours
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Pause email notifications during specific hours
                  </p>
                </div>
              </div>
              <Switch
                id="quiet-hours"
                checked={preferences.quiet_hours_enabled}
                onCheckedChange={(checked) =>
                  handleGlobalToggle("quiet_hours_enabled", checked)
                }
                data-testid="quiet-hours-toggle"
              />
            </div>
            
            {preferences.quiet_hours_enabled && (
              <div className="flex items-center gap-4 pl-8">
                <div className="flex items-center gap-2">
                  <Label htmlFor="quiet-start" className="text-sm">From</Label>
                  <Input
                    id="quiet-start"
                    type="time"
                    value={preferences.quiet_hours_start || "22:00"}
                    onChange={(e) =>
                      handleGlobalToggle("quiet_hours_start", e.target.value)
                    }
                    className="w-24"
                    data-testid="quiet-hours-start"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="quiet-end" className="text-sm">To</Label>
                  <Input
                    id="quiet-end"
                    type="time"
                    value={preferences.quiet_hours_end || "08:00"}
                    onChange={(e) =>
                      handleGlobalToggle("quiet_hours_end", e.target.value)
                    }
                    className="w-24"
                    data-testid="quiet-hours-end"
                  />
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Per-Type Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Types</CardTitle>
          <CardDescription>
            Choose which notifications you want to receive and how
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" defaultValue={Object.keys(categories)} className="w-full">
            {Object.entries(categories).map(([category, types]) => {
              const CategoryIcon = categoryIcons[category] || Bell;
              
              return (
                <AccordionItem key={category} value={category}>
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-2">
                      <CategoryIcon className="w-5 h-5" />
                      <span>{category}</span>
                      <Badge variant="secondary" className="ml-2">
                        {types.length}
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-4 pt-2">
                      {types.map((type) => (
                        <div
                          key={type.type}
                          className="flex items-start justify-between p-4 rounded-lg border border-border"
                          data-testid={`notification-type-${type.type}`}
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-3">
                              <Switch
                                checked={isTypeEnabled(type.type)}
                                onCheckedChange={(checked) =>
                                  handleTypeToggle(type.type, checked)
                                }
                                data-testid={`toggle-${type.type}`}
                              />
                              <div>
                                <Label className="text-base font-medium">
                                  {type.label}
                                </Label>
                                <p className="text-sm text-muted-foreground">
                                  {type.description}
                                </p>
                              </div>
                            </div>
                            
                            {/* Channels */}
                            {isTypeEnabled(type.type) && (
                              <div className="flex items-center gap-4 mt-3 ml-11">
                                <Label className="text-sm text-muted-foreground">
                                  Channels:
                                </Label>
                                <div className="flex items-center gap-4">
                                  <div className="flex items-center gap-2">
                                    <Checkbox
                                      id={`${type.type}-in-app`}
                                      checked={isChannelEnabled(type.type, NotificationChannels.IN_APP)}
                                      onCheckedChange={(checked) =>
                                        handleChannelToggle(type.type, NotificationChannels.IN_APP, checked)
                                      }
                                      disabled // In-app always enabled
                                    />
                                    <Label
                                      htmlFor={`${type.type}-in-app`}
                                      className="text-sm"
                                    >
                                      In-App
                                    </Label>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Checkbox
                                      id={`${type.type}-email`}
                                      checked={isChannelEnabled(type.type, NotificationChannels.EMAIL)}
                                      onCheckedChange={(checked) =>
                                        handleChannelToggle(type.type, NotificationChannels.EMAIL, checked)
                                      }
                                      disabled={!preferences.email_notifications_enabled}
                                    />
                                    <Label
                                      htmlFor={`${type.type}-email`}
                                      className="text-sm"
                                    >
                                      Email
                                    </Label>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          onClick={handleReset}
          disabled={!hasChanges}
          data-testid="reset-preferences-btn"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Reset
        </Button>
        <Button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          data-testid="save-preferences-btn"
        >
          {saving ? (
            <LoadingSpinner size="sm" className="mr-2" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Preferences
        </Button>
      </div>
    </div>
  );
}
