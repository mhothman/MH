import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getOrgBudgets } from "../../api/budgets";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";
import { LoadingSpinner } from "../ui/loading-spinner";
import { DollarSign, AlertCircle, TrendingDown, ArrowRight } from "lucide-react";

export const BudgetDashboardWidget = ({ orgId }) => {
  const navigate = useNavigate();
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!orgId) return;

    const loadBudgets = async () => {
      try {
        const data = await getOrgBudgets(orgId);
        setBudgets(data || []);
      } catch (error) {
        console.error("Failed to load budgets:", error);
        setBudgets([]);
      } finally {
        setLoading(false);
      }
    };

    loadBudgets();
  }, [orgId]);

  const getBudgetStatus = (budget) => {
    const percentUsed = budget.total_budget > 0 
      ? (budget.spent / budget.total_budget) * 100 
      : 0;

    if (budget.status === 'locked') {
      return { label: 'Locked', color: 'bg-red-700', variant: 'destructive' };
    } else if (percentUsed >= 100) {
      return { label: 'Exceeded', color: 'bg-red-500', variant: 'destructive' };
    } else if (percentUsed >= (budget.warning_threshold_percent || 80)) {
      return { label: 'Warning', color: 'bg-yellow-500', variant: 'default' };
    }
    return { label: 'Active', color: 'bg-green-500', variant: 'secondary' };
  };

  const getCurrencySymbol = (currency) => {
    const symbols = {
      'EGP': 'E£',
      'USD': '$',
      'EUR': '€',
      'GBP': '£',
    };
    return symbols[currency] || currency;
  };

  const formatAmount = (amount, currency) => {
    const symbol = getCurrencySymbol(currency);
    const safeAmount = amount ?? 0;
    return `${symbol}${safeAmount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  // Calculate summary stats
  const totalBudget = budgets.reduce((sum, b) => sum + (b.total_budget || 0), 0);
  const totalSpent = budgets.reduce((sum, b) => sum + (b.spent_amount || 0), 0);
  const atRiskCount = budgets.filter(b => {
    const percentUsed = b.total_budget > 0 ? ((b.spent_amount || 0) / b.total_budget) * 100 : 0;
    return percentUsed >= (b.warning_threshold_percent || 80);
  }).length;

  if (loading) {
    return (
      <Card data-testid="budget-widget">
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Don't show widget if no budgets exist
  if (budgets.length === 0) {
    return null;
  }

  return (
    <Card data-testid="budget-widget" className="border-emerald-200 bg-emerald-50/30 dark:bg-emerald-950/20 dark:border-emerald-800">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-600" />
          <CardTitle className="font-heading text-lg text-emerald-800 dark:text-emerald-200">
            Project Budgets Overview
          </CardTitle>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate("/projects")}>
          View All
          <ArrowRight className="w-4 h-4 ml-1" />
        </Button>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-white dark:bg-gray-800 rounded-lg">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Total Budget</p>
            <p className="text-lg font-bold">E£{totalBudget.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Total Spent</p>
            <p className="text-lg font-bold">E£{totalSpent.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">At Risk</p>
            <p className="text-lg font-bold flex items-center gap-1">
              {atRiskCount}
              {atRiskCount > 0 && <AlertCircle className="w-4 h-4 text-yellow-500" />}
            </p>
          </div>
        </div>

        {/* Project Budget List */}
        <div className="space-y-3 max-h-[300px] overflow-y-auto">
          {budgets.map((budget) => {
            const status = getBudgetStatus(budget);
            const spent = budget.spent ?? 0;
            const totalBudget = budget.total_budget ?? 0;
            const percentUsed = totalBudget > 0 
              ? (spent / totalBudget) * 100 
              : 0;

            return (
              <div
                key={budget.budget_id}
                className="flex items-center gap-4 p-3 rounded-lg bg-white dark:bg-gray-800 border cursor-pointer hover:shadow-sm transition-shadow"
                onClick={() => navigate(`/projects/${budget.project_id}`)}
                data-testid={`budget-item-${budget.project_id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium truncate">{budget.project_name}</p>
                    <Badge variant={status.variant} className="text-xs">
                      {status.label}
                    </Badge>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {formatAmount(budget.spent, budget.currency)} / {formatAmount(budget.total_budget, budget.currency)}
                      </span>
                      <span className="font-mono text-xs font-medium">
                        {percentUsed.toFixed(0)}%
                      </span>
                    </div>
                    <Progress 
                      value={Math.min(percentUsed, 100)} 
                      className={`h-2 ${percentUsed >= 100 ? '[&>div]:bg-red-500' : percentUsed >= (budget.warning_threshold_percent || 80) ? '[&>div]:bg-yellow-500' : '[&>div]:bg-green-500'}`}
                    />
                  </div>
                  
                  {budget.remaining < 0 && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-red-600">
                      <TrendingDown className="w-3 h-3" />
                      <span>Over budget by {formatAmount(Math.abs(budget.remaining), budget.currency)}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
