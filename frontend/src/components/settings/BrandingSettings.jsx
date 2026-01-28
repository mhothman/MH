/**
 * BrandingSettings - Organization branding and theming component
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Switch } from "../ui/switch";
import { Textarea } from "../ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  Upload,
  Trash2,
  RotateCcw,
  Eye,
  Check,
  Sparkles,
} from "lucide-react";

export function BrandingSettings({
  organization,
  brandingData,
  presetFonts = [],
  presetThemes = [],
  onUpdateBranding,
  onPublishBranding,
  onResetBranding,
  onUploadLogo,
  onDeleteLogo,
  previewBranding,
  revertPreview,
}) {
  const [preview, setPreview] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  const currentData = { ...brandingData, ...preview };

  const handleColorChange = (field, value) => {
    setPreview(prev => ({ ...prev, [field]: value }));
    previewBranding?.({ [field]: value });
  };

  const handleFontChange = (field, value) => {
    const updates = { [field]: value };
    if (value !== 'custom') {
      updates[`${field}_url`] = null;
    }
    setPreview(prev => ({ ...prev, ...updates }));
    if (value !== 'custom') {
      previewBranding?.(updates);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ["image/png", "image/jpeg", "image/svg+xml", "image/webp"];
    if (!validTypes.includes(file.type)) {
      toast.error("Invalid file type. Please upload PNG, JPG, SVG, or WebP.");
      return;
    }
    if (file.size > 1024 * 1024) {
      toast.error("File too large. Maximum size is 1MB");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    setPreview(prev => ({ ...prev, logo_url: previewUrl, _logoFile: file }));
  };

  const handleRemoveLogo = async () => {
    if (preview?._logoFile) {
      setPreview(prev => ({ ...prev, logo_url: null, _logoFile: null }));
    } else if (brandingData.logo_url) {
      try {
        await onDeleteLogo?.();
        toast.success("Logo deleted");
      } catch (error) {
        toast.error("Failed to delete logo");
      }
    }
  };

  const handleApplyTheme = (selectedTheme) => {
    const updates = {
      primary_color: selectedTheme.primary_color || selectedTheme.colors?.primary,
      secondary_color: selectedTheme.secondary_color || selectedTheme.colors?.secondary,
      accent_color: selectedTheme.accent_color || selectedTheme.colors?.accent,
      heading_font: selectedTheme.heading_font || selectedTheme.fonts?.heading || 'inter',
      body_font: selectedTheme.body_font || selectedTheme.fonts?.body || 'inter',
    };
    setPreview(prev => ({ ...prev, ...updates }));
    previewBranding?.(updates);
    toast.success(`Applied "${selectedTheme.name}" theme`);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (preview?._logoFile) {
        setUploadingLogo(true);
        await onUploadLogo?.(preview._logoFile);
        setUploadingLogo(false);
      }

      const updates = { ...preview };
      delete updates._logoFile;
      delete updates.logo_url;
      
      if (Object.keys(updates).length > 0) {
        await onUpdateBranding?.(updates);
      }
      
      await onPublishBranding?.();
      setPreview(null);
      toast.success("Branding published successfully!");
    } catch (error) {
      toast.error(error.message || "Failed to save branding");
    } finally {
      setSaving(false);
      setUploadingLogo(false);
    }
  };

  const handleCancel = () => {
    setPreview(null);
    revertPreview?.();
  };

  const handleReset = async () => {
    try {
      await onResetBranding?.();
      setPreview(null);
      toast.success("Branding reset to defaults");
    } catch (error) {
      toast.error("Failed to reset branding");
    }
  };

  if (!organization) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Branding & Customization</CardTitle>
        <CardDescription>Customize your organization's visual identity</CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Theme Templates */}
        <div className="space-y-3">
          <Label className="text-base font-medium flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Theme Templates
          </Label>
          <p className="text-sm text-muted-foreground">
            Quick start with a pre-designed theme
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {presetThemes.map((theme) => (
              <button
                key={theme.id}
                onClick={() => handleApplyTheme(theme)}
                className="p-3 border rounded-lg hover:border-primary transition-colors text-left"
              >
                <div className="flex gap-1 mb-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: theme.colors?.primary }} />
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: theme.colors?.secondary }} />
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: theme.colors?.accent }} />
                </div>
                <p className="text-sm font-medium">{theme.name}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Logo Upload */}
        <div className="space-y-3">
          <Label className="text-base font-medium">Logo</Label>
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-lg border flex items-center justify-center bg-muted">
              {(preview?.logo_url || brandingData.logo_url) ? (
                <img
                  src={preview?.logo_url || brandingData.logo_url}
                  alt="Logo"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <span className="text-2xl font-bold text-muted-foreground">
                  {organization?.name?.charAt(0) || 'O'}
                </span>
              )}
            </div>
            <div className="space-y-2">
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                className="hidden"
                id="logo-upload"
                onChange={handleLogoUpload}
              />
              <Button variant="outline" size="sm" onClick={() => document.getElementById('logo-upload').click()}>
                <Upload className="w-4 h-4 mr-2" />
                Upload Logo
              </Button>
              {(preview?.logo_url || brandingData.logo_url) && (
                <Button variant="ghost" size="sm" className="text-destructive" onClick={handleRemoveLogo}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Remove
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Color Pickers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <Label>Primary Color</Label>
            <p className="text-xs text-muted-foreground">Main brand color</p>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={currentData.primary_color || "#0f172a"}
                onChange={(e) => handleColorChange("primary_color", e.target.value)}
                className="w-12 h-10 rounded cursor-pointer border"
              />
              <Input
                value={currentData.primary_color || "#0f172a"}
                onChange={(e) => {
                  if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
                    handleColorChange("primary_color", e.target.value);
                  }
                }}
                className="w-28 font-mono text-sm"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Secondary Color</Label>
            <p className="text-xs text-muted-foreground">Accents and highlights</p>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={currentData.secondary_color || "#3b82f6"}
                onChange={(e) => handleColorChange("secondary_color", e.target.value)}
                className="w-12 h-10 rounded cursor-pointer border"
              />
              <Input
                value={currentData.secondary_color || "#3b82f6"}
                onChange={(e) => {
                  if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
                    handleColorChange("secondary_color", e.target.value);
                  }
                }}
                className="w-28 font-mono text-sm"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Accent Color</Label>
            <p className="text-xs text-muted-foreground">Success states and CTAs</p>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={currentData.accent_color || "#10b981"}
                onChange={(e) => handleColorChange("accent_color", e.target.value)}
                className="w-12 h-10 rounded cursor-pointer border"
              />
              <Input
                value={currentData.accent_color || "#10b981"}
                onChange={(e) => {
                  if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
                    handleColorChange("accent_color", e.target.value);
                  }
                }}
                className="w-28 font-mono text-sm"
              />
            </div>
          </div>
        </div>

        {/* Dark Mode Support */}
        <div className="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <Label>Dark Mode Support</Label>
            <p className="text-sm text-muted-foreground">
              Allow users to switch between light and dark themes
            </p>
          </div>
          <Switch
            checked={currentData.dark_mode_supported ?? true}
            onCheckedChange={(checked) => setPreview(prev => ({ ...prev, dark_mode_supported: checked }))}
          />
        </div>

        {/* Font Selection */}
        <div className="space-y-4">
          <Label className="text-base font-medium">Typography</Label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Heading Font</Label>
              <Select
                value={currentData.heading_font || "inter"}
                onValueChange={(value) => handleFontChange("heading_font", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select font" />
                </SelectTrigger>
                <SelectContent>
                  {presetFonts.map((font) => (
                    <SelectItem key={font.id} value={font.id}>{font.name}</SelectItem>
                  ))}
                  <SelectItem value="custom">Custom Font URL</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Body Font</Label>
              <Select
                value={currentData.body_font || "inter"}
                onValueChange={(value) => handleFontChange("body_font", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select font" />
                </SelectTrigger>
                <SelectContent>
                  {presetFonts.map((font) => (
                    <SelectItem key={font.id} value={font.id}>{font.name}</SelectItem>
                  ))}
                  <SelectItem value="custom">Custom Font URL</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Custom CSS */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-base font-medium">Custom CSS</Label>
              <p className="text-sm text-muted-foreground">Add custom styles (max 10KB)</p>
            </div>
            <Badge variant="outline">
              {((currentData.custom_css || '').length / 1024).toFixed(1)} KB / 10 KB
            </Badge>
          </div>
          <Textarea
            className="font-mono text-sm min-h-[120px]"
            placeholder={`.my-custom-class {\n  color: var(--org-primary-color);\n}`}
            value={currentData.custom_css || ''}
            onChange={(e) => {
              if (e.target.value.length <= 10240) {
                setPreview(prev => ({ ...prev, custom_css: e.target.value }));
                previewBranding?.({ custom_css: e.target.value });
              }
            }}
          />
        </div>

        {/* Live Preview */}
        <div className="space-y-3">
          <Label className="text-base font-medium flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Live Preview
          </Label>
          <div className="border rounded-lg p-4 bg-card">
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
                style={{ backgroundColor: currentData.primary_color }}
              >
                {organization?.name?.charAt(0) || 'O'}
              </div>
              <span className="font-bold">{organization?.name}</span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" style={{ backgroundColor: currentData.primary_color, color: 'white' }}>
                Primary
              </Button>
              <Button
                size="sm"
                variant="outline"
                style={{ borderColor: currentData.secondary_color, color: currentData.secondary_color }}
              >
                Secondary
              </Button>
              <Badge style={{ backgroundColor: currentData.accent_color, color: 'white' }}>
                Accent
              </Badge>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            {brandingData.published ? (
              <Badge variant="default" className="bg-green-500">
                <Check className="w-3 h-3 mr-1" />
                Published
              </Badge>
            ) : (
              <Badge variant="secondary">Draft</Badge>
            )}
            {preview && (
              <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                Unsaved Changes
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleCancel} disabled={!preview}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button variant="outline" onClick={handleReset}>
              Reset to Default
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <><LoadingSpinner size="sm" className="mr-2" />Publishing...</>
              ) : (
                <><Check className="w-4 h-4 mr-2" />Save & Publish</>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
