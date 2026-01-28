/**
 * PreferencesSettings - User preferences component with enhanced notification settings
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { toast } from "sonner";
import { Moon, Sun, Bell, Globe, ExternalLink } from "lucide-react";
import { NotificationPreferences } from "./NotificationPreferences";

export function PreferencesSettings({
  theme,
  onToggleTheme,
  preferences = {},
  onSavePreferences,
}) {
  const navigate = useNavigate();
  const [language, setLanguage] = useState(preferences.language || "en");
  const [saving, setSaving] = useState(false);
  const [showAdvancedNotifications, setShowAdvancedNotifications] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSavePreferences?.({
        language,
      });
      toast.success("Preferences saved");
    } catch (error) {
      toast.error("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="preferences-settings">
      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {theme === "dark" ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            Appearance
          </CardTitle>
          <CardDescription>Customize how ProFlow looks on your device</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Dark Mode</Label>
              <p className="text-sm text-muted-foreground">Toggle dark mode theme</p>
            </div>
            <Switch
              checked={theme === "dark"}
              onCheckedChange={onToggleTheme}
              data-testid="theme-toggle"
            />
          </div>
          
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => theme !== "light" && onToggleTheme?.()}
              className={`flex flex-col items-center p-4 border rounded-lg transition-colors ${
                theme === "light" ? "border-primary bg-accent" : "hover:bg-accent"
              }`}
            >
              <Sun className="w-6 h-6 mb-2" />
              <span className="text-sm">Light</span>
            </button>
            <button
              onClick={() => theme !== "dark" && onToggleTheme?.()}
              className={`flex flex-col items-center p-4 border rounded-lg transition-colors ${
                theme === "dark" ? "border-primary bg-accent" : "hover:bg-accent"
              }`}
            >
              <Moon className="w-6 h-6 mb-2" />
              <span className="text-sm">Dark</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Notifications Quick Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notifications
          </CardTitle>
          <CardDescription>Manage your notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-accent/50">
            <div>
              <Label className="text-base">Advanced Notification Settings</Label>
              <p className="text-sm text-muted-foreground">
                Configure per-type notifications, email preferences, and quiet hours
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => setShowAdvancedNotifications(!showAdvancedNotifications)}
              data-testid="toggle-advanced-notifications"
            >
              {showAdvancedNotifications ? "Hide" : "Show"} Settings
            </Button>
          </div>
          
          <div className="flex items-center justify-between p-4 rounded-lg border border-border">
            <div>
              <Label>Notification Center</Label>
              <p className="text-sm text-muted-foreground">
                View all your notifications in one place
              </p>
            </div>
            <Button
              variant="ghost"
              onClick={() => navigate("/notifications")}
              data-testid="go-to-notification-center"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Open
            </Button>
          </div>
          
          {showAdvancedNotifications && (
            <div className="pt-4 border-t border-border">
              <NotificationPreferences />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Language */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            Language & Region
          </CardTitle>
          <CardDescription>Set your preferred language</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Language</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="w-[200px]" data-testid="language-select">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="es">Español</SelectItem>
                <SelectItem value="fr">Français</SelectItem>
                <SelectItem value="de">Deutsch</SelectItem>
                <SelectItem value="ar">العربية</SelectItem>
                <SelectItem value="zh">中文</SelectItem>
                <SelectItem value="ja">日本語</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving} data-testid="save-preferences-btn">
          {saving ? "Saving..." : "Save Preferences"}
        </Button>
      </div>
    </div>
  );
}
