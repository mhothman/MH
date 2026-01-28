/**
 * OrganizationSettings - Organization configuration component
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";

const TIMEZONES = [
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  { value: "Africa/Cairo", label: "Cairo (Egypt Standard Time)" },
  { value: "America/New_York", label: "New York (Eastern Time)" },
  { value: "America/Chicago", label: "Chicago (Central Time)" },
  { value: "America/Denver", label: "Denver (Mountain Time)" },
  { value: "America/Los_Angeles", label: "Los Angeles (Pacific Time)" },
  { value: "Europe/London", label: "London (GMT/BST)" },
  { value: "Europe/Paris", label: "Paris (Central European Time)" },
  { value: "Europe/Berlin", label: "Berlin (Central European Time)" },
  { value: "Asia/Dubai", label: "Dubai (Gulf Standard Time)" },
  { value: "Asia/Riyadh", label: "Riyadh (Arabia Standard Time)" },
  { value: "Asia/Kolkata", label: "Mumbai (India Standard Time)" },
  { value: "Asia/Singapore", label: "Singapore (Singapore Time)" },
  { value: "Asia/Tokyo", label: "Tokyo (Japan Standard Time)" },
  { value: "Australia/Sydney", label: "Sydney (Australian Eastern Time)" },
];

export default function OrganizationSettings({ organization, onSave }) {
  const [formData, setFormData] = useState({
    name: "",
    timezone: "UTC",
    address: "",
    contact_phone: "",
    contact_email: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (organization) {
      setFormData({
        name: organization.name || "",
        timezone: organization.timezone || "UTC",
        address: organization.address || "",
        contact_phone: organization.contact_phone || "",
        contact_email: organization.contact_email || "",
      });
    }
  }, [organization]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave?.(formData);
      toast.success("Organization updated successfully");
    } catch (error) {
      toast.error("Failed to update organization");
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!organization) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization Settings</CardTitle>
        <CardDescription>Manage your organization configuration</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="org-name">Organization Name</Label>
            <Input
              id="org-name"
              value={formData.name}
              onChange={(e) => updateField("name", e.target.value)}
              data-testid="org-name-input"
            />
          </div>
          
          <div className="grid gap-2">
            <Label>Timezone</Label>
            <Select 
              value={formData.timezone} 
              onValueChange={(value) => updateField("timezone", value)}
            >
              <SelectTrigger data-testid="timezone-select">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONES.map(tz => (
                  <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="org-address">Address</Label>
            <Textarea
              id="org-address"
              placeholder="Enter organization address"
              value={formData.address}
              onChange={(e) => updateField("address", e.target.value)}
              rows={2}
              data-testid="org-address-input"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="org-phone">Contact Phone</Label>
              <Input
                id="org-phone"
                type="tel"
                placeholder="+1 (555) 000-0000"
                value={formData.contact_phone}
                onChange={(e) => updateField("contact_phone", e.target.value)}
                data-testid="org-phone-input"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="org-email">Contact Email</Label>
              <Input
                id="org-email"
                type="email"
                placeholder="contact@company.com"
                value={formData.contact_email}
                onChange={(e) => updateField("contact_email", e.target.value)}
                data-testid="org-email-input"
              />
            </div>
          </div>
        </div>

        <Button 
          onClick={handleSave} 
          disabled={saving}
          data-testid="save-org-btn"
        >
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </CardContent>
    </Card>
  );
}
