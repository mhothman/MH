/**
 * DomainSettings - White-label domain configuration with SSL automation
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { Switch } from "../../components/ui/switch";
import { Separator } from "../../components/ui/separator";
import { 
  Globe, 
  CheckCircle, 
  AlertCircle, 
  Lock, 
  ExternalLink, 
  Copy, 
  Trash2,
  Shield,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Clock,
  FileCode
} from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { getSSLStatus, requestSSLCertificate, renewSSLCertificate, toggleSSLAutoRenew, getNginxConfig } from "../../api/ssl";

export default function DomainSettings({ 
  orgId, 
  domainConfig, 
  canEdit, 
  onSetDomain, 
  onVerifyDomain, 
  onRemoveDomain,
  onRefresh 
}) {
  const [newDomain, setNewDomain] = useState("");
  const [settingDomain, setSettingDomain] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [removing, setRemoving] = useState(false);
  
  // SSL State
  const [sslStatus, setSSLStatus] = useState(null);
  const [sslLoading, setSSLLoading] = useState(false);
  const [requestingSSL, setRequestingSSL] = useState(false);
  const [renewingSSL, setRenewingSSL] = useState(false);
  const [nginxConfigOpen, setNginxConfigOpen] = useState(false);
  const [nginxConfig, setNginxConfig] = useState("");

  // Load SSL status when domain is configured and verified
  useEffect(() => {
    if (orgId && domainConfig?.domain_verified) {
      loadSSLStatus();
    }
  }, [orgId, domainConfig?.domain_verified]);

  const loadSSLStatus = async () => {
    setSSLLoading(true);
    try {
      const status = await getSSLStatus(orgId);
      setSSLStatus(status);
    } catch (error) {
      console.error("Failed to load SSL status:", error);
    } finally {
      setSSLLoading(false);
    }
  };

  const handleSetDomain = async () => {
    if (!newDomain.trim()) {
      toast.error("Please enter a domain");
      return;
    }
    
    setSettingDomain(true);
    try {
      await onSetDomain?.(orgId, newDomain.trim());
      setNewDomain("");
      toast.success("Domain configured. Please add the DNS record to verify.");
      onRefresh?.();
    } catch (error) {
      toast.error(error.message || "Failed to set domain");
    } finally {
      setSettingDomain(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const result = await onVerifyDomain?.(orgId);
      if (result?.verified) {
        toast.success("Domain verified successfully!");
        onRefresh?.();
      } else {
        toast.error(result?.message || "Verification failed. Please check DNS records.");
      }
    } catch (error) {
      toast.error("Failed to verify domain");
    } finally {
      setVerifying(false);
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await onRemoveDomain?.(orgId);
      setSSLStatus(null);
      toast.success("Domain removed");
      onRefresh?.();
    } catch (error) {
      toast.error("Failed to remove domain");
    } finally {
      setRemoving(false);
    }
  };

  const handleRequestSSL = async () => {
    if (!domainConfig?.custom_domain) {
      toast.error("Please configure a domain first");
      return;
    }
    
    setRequestingSSL(true);
    try {
      const result = await requestSSLCertificate(orgId, domainConfig.custom_domain);
      if (result.success) {
        toast.success(result.message || "SSL certificate requested successfully!");
        loadSSLStatus();
      } else {
        toast.error(result.error || "Failed to request SSL certificate");
      }
    } catch (error) {
      toast.error(error.message || "Failed to request SSL certificate");
    } finally {
      setRequestingSSL(false);
    }
  };

  const handleRenewSSL = async () => {
    setRenewingSSL(true);
    try {
      const result = await renewSSLCertificate(orgId);
      if (result.success) {
        toast.success("SSL certificate renewed successfully!");
        loadSSLStatus();
      } else {
        toast.error(result.error || "Failed to renew certificate");
      }
    } catch (error) {
      toast.error(error.message || "Failed to renew certificate");
    } finally {
      setRenewingSSL(false);
    }
  };

  const handleToggleAutoRenew = async (enabled) => {
    try {
      await toggleSSLAutoRenew(orgId, enabled);
      setSSLStatus(prev => ({ ...prev, auto_renew: enabled }));
      toast.success(`Auto-renewal ${enabled ? 'enabled' : 'disabled'}`);
    } catch (error) {
      toast.error("Failed to update auto-renewal setting");
    }
  };

  const handleShowNginxConfig = async () => {
    try {
      const result = await getNginxConfig(orgId);
      setNginxConfig(result.nginx_config);
      setNginxConfigOpen(true);
    } catch (error) {
      toast.error("Failed to get nginx configuration");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const getSSLStatusBadge = () => {
    if (!sslStatus || sslStatus.status === "not_configured") {
      return <Badge variant="secondary">Not Configured</Badge>;
    }
    if (sslStatus.status === "active" && sslStatus.is_valid) {
      return <Badge className="bg-green-500">Active</Badge>;
    }
    if (sslStatus.status === "pending") {
      return <Badge variant="outline" className="text-yellow-600 border-yellow-600">Pending</Badge>;
    }
    if (sslStatus.status === "expired" || !sslStatus.is_valid) {
      return <Badge variant="destructive">Expired</Badge>;
    }
    return <Badge variant="secondary">{sslStatus.status}</Badge>;
  };

  if (!canEdit) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            White-Label Domain
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 p-4 bg-muted rounded-lg">
            <Lock className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              You don't have permission to configure domain settings
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Domain Configuration Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            White-Label Domain
          </CardTitle>
          <CardDescription>
            Configure a custom domain for your organization (e.g., app.yourcompany.com)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current Domain Status */}
          {domainConfig?.custom_domain && (
            <div className={`p-4 rounded-lg border ${
              domainConfig.domain_verified 
                ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800' 
                : 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {domainConfig.domain_verified ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-yellow-600" />
                  )}
                  <div>
                    <p className="font-medium">{domainConfig.custom_domain}</p>
                    <p className="text-sm text-muted-foreground">
                      {domainConfig.domain_verified ? 'Domain verified and active' : 'Pending verification'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  {!domainConfig.domain_verified && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleVerify}
                      disabled={verifying}
                    >
                      {verifying ? "Verifying..." : "Verify Now"}
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleRemove}
                    disabled={removing}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* DNS Instructions */}
              {!domainConfig.domain_verified && domainConfig.dns_verification_token && (
                <div className="mt-4 p-3 bg-background rounded border">
                  <p className="text-sm font-medium mb-2">Add this DNS TXT record:</p>
                  <div className="grid gap-2 text-sm">
                    <div className="flex items-center justify-between p-2 bg-muted rounded">
                      <span className="font-mono">Type: TXT</span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-muted rounded">
                      <span className="font-mono truncate">Host: _proflow-verify</span>
                      <Button size="sm" variant="ghost" onClick={() => copyToClipboard("_proflow-verify")}>
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-muted rounded">
                      <span className="font-mono truncate">{domainConfig.dns_verification_token}</span>
                      <Button size="sm" variant="ghost" onClick={() => copyToClipboard(domainConfig.dns_verification_token)}>
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Add New Domain */}
          {!domainConfig?.custom_domain && (
            <div className="space-y-3">
              <div className="grid gap-2">
                <Label>Custom Domain</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="app.yourcompany.com"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    data-testid="domain-input"
                  />
                  <Button onClick={handleSetDomain} disabled={settingDomain}>
                    {settingDomain ? "Setting..." : "Set Domain"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Enter your custom domain without http:// or https://
                </p>
              </div>
            </div>
          )}

          {/* Visit Domain Link */}
          {domainConfig?.domain_verified && (
            <Button variant="outline" className="w-full" asChild>
              <a href={`https://${domainConfig.custom_domain}`} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                Visit {domainConfig.custom_domain}
              </a>
            </Button>
          )}
        </CardContent>
      </Card>

      {/* SSL Certificate Card - Only shown when domain is verified */}
      {domainConfig?.domain_verified && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              SSL Certificate
              {getSSLStatusBadge()}
            </CardTitle>
            <CardDescription>
              Secure your custom domain with HTTPS using Let's Encrypt
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {sslLoading ? (
              <div className="flex items-center justify-center py-4">
                <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                <span className="text-muted-foreground">Loading SSL status...</span>
              </div>
            ) : sslStatus?.status === "active" && sslStatus?.is_valid ? (
              /* SSL Active Status */
              <div className="space-y-4">
                <div className="p-4 rounded-lg border bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-3">
                    <ShieldCheck className="w-5 h-5 text-green-600" />
                    <span className="font-medium text-green-800 dark:text-green-200">
                      SSL Certificate Active
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Issuer</p>
                      <p className="font-medium">{sslStatus.issuer || "Let's Encrypt"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Days Remaining</p>
                      <p className={`font-medium ${sslStatus.days_remaining <= 30 ? 'text-yellow-600' : 'text-green-600'}`}>
                        {sslStatus.days_remaining} days
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Valid Until</p>
                      <p className="font-medium">
                        {sslStatus.valid_until ? new Date(sslStatus.valid_until).toLocaleDateString() : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Auto Renewal</p>
                      <p className={`font-medium ${sslStatus.auto_renew ? 'text-green-600' : 'text-yellow-600'}`}>
                        {sslStatus.auto_renew ? 'Enabled' : 'Disabled'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* SSL Options */}
                <Separator />
                
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto-Renewal</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically renew certificate before expiration
                    </p>
                  </div>
                  <Switch
                    checked={sslStatus.auto_renew}
                    onCheckedChange={handleToggleAutoRenew}
                  />
                </div>

                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={handleRenewSSL} 
                    disabled={renewingSSL}
                    className="flex-1"
                  >
                    {renewingSSL ? (
                      <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Renewing...</>
                    ) : (
                      <><RefreshCw className="w-4 h-4 mr-2" />Renew Now</>
                    )}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={handleShowNginxConfig}
                  >
                    <FileCode className="w-4 h-4 mr-2" />
                    View Nginx Config
                  </Button>
                </div>
              </div>
            ) : sslStatus?.needs_renewal ? (
              /* Needs Renewal */
              <div className="p-4 rounded-lg border bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert className="w-5 h-5 text-yellow-600" />
                  <span className="font-medium text-yellow-800 dark:text-yellow-200">
                    Certificate Expiring Soon
                  </span>
                </div>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
                  Your SSL certificate expires in {sslStatus.days_remaining} days. Renew now to avoid service interruption.
                </p>
                <Button onClick={handleRenewSSL} disabled={renewingSSL}>
                  {renewingSSL ? "Renewing..." : "Renew Certificate"}
                </Button>
              </div>
            ) : (
              /* No SSL - Request New */
              <div className="space-y-4">
                <div className="p-4 rounded-lg border bg-muted">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="w-5 h-5 text-muted-foreground" />
                    <span className="font-medium">SSL Not Configured</span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Secure your custom domain with a free SSL certificate from Let's Encrypt. 
                    This enables HTTPS and shows a padlock icon in browsers.
                  </p>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="w-4 h-4" />
                    <span>Free certificate from Let's Encrypt</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="w-4 h-4" />
                    <span>Automatic renewal before expiration</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="w-4 h-4" />
                    <span>Industry-standard TLS 1.2/1.3 encryption</span>
                  </div>
                </div>
                <Button 
                  onClick={handleRequestSSL} 
                  disabled={requestingSSL}
                  className="w-full"
                >
                  {requestingSSL ? (
                    <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Requesting Certificate...</>
                  ) : (
                    <><ShieldCheck className="w-4 h-4 mr-2" />Enable SSL Certificate</>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Nginx Config Dialog */}
      <Dialog open={nginxConfigOpen} onOpenChange={setNginxConfigOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Nginx SSL Configuration</DialogTitle>
            <DialogDescription>
              Use this configuration for your nginx server to enable SSL for {domainConfig?.custom_domain}
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <pre className="p-4 bg-muted rounded-lg overflow-auto max-h-[400px] text-xs">
              {nginxConfig}
            </pre>
            <Button 
              size="sm" 
              variant="outline" 
              className="absolute top-2 right-2"
              onClick={() => copyToClipboard(nginxConfig)}
            >
              <Copy className="w-4 h-4 mr-1" />
              Copy
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
