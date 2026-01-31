import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Alert, AlertDescription } from "../components/ui/alert";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { Shield, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function TenantAdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      
      const response = await fetch(`${API_URL}/api/tenant-admin/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Store tenant admin token separately
      localStorage.setItem('tenant_admin_token', data.access_token);
      localStorage.setItem('tenant_admin_user', JSON.stringify(data.user));
      localStorage.setItem('tenant_info', JSON.stringify(data.tenant));
      
      toast.success(`Welcome back, ${data.user.name}`);
      navigate('/tenant-admin');
    } catch (error) {
      setError(error.message || 'Invalid credentials');
      toast.error(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-full">
              <Shield className="w-10 h-10 text-purple-600" />
            </div>
          </div>
          <CardTitle className="text-2xl">Tenant Administration</CardTitle>
          <CardDescription>
            Sign in with your tenant admin credentials
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Alert className="bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                This is a tenant-level admin portal. All actions are audited.
              </AlertDescription>
            </Alert>
            
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <LoadingSpinner size="sm" className="mr-2" /> : null}
              Sign In to Tenant Portal
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              <a href="/login" className="text-primary hover:underline">
                Organization user? Login here
              </a>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
