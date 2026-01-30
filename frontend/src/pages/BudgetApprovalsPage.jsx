import { useAuth } from "../context/AuthContext";
import { useAppData } from "../context/AppDataContext";
import { BudgetApprovalsManager } from "../components/budget/BudgetApprovalsManager";
import { Card, CardContent } from "../components/ui/card";
import { Shield } from "lucide-react";

export default function BudgetApprovalsPage() {
  const { user } = useAuth();
  const { currentOrgId } = useAppData();

  if (!currentOrgId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">No organization selected</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield className="w-8 h-8 text-emerald-600" />
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
            Budget Approvals
          </h1>
          <p className="text-muted-foreground mt-1">
            Review and approve budget change requests
          </p>
        </div>
      </div>

      {/* Approvals Manager */}
      <BudgetApprovalsManager orgId={currentOrgId} />
    </div>
  );
}
