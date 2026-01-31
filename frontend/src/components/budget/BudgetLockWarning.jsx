import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { AlertTriangle, Lock, DollarSign } from "lucide-react";

export const BudgetLockWarning = ({ budgetStatus, onOverride, canOverride }) => {
  if (!budgetStatus?.is_locked) return null;

  return (
    <Alert variant="destructive" className="mb-4">
      <Lock className="h-4 w-4" />
      <AlertTitle className="flex items-center justify-between">
        <span>Budget Locked - Operations Restricted</span>
        {canOverride && (
          <Button 
            size="sm" 
            variant="outline" 
            onClick={onOverride}
            className="ml-2"
          >
            <DollarSign className="w-4 h-4 mr-1" />
            Override Lock
          </Button>
        )}
      </AlertTitle>
      <AlertDescription>
        {budgetStatus.message || "This project's budget has been exceeded and hard limit is enabled."}
        {!canOverride && " Contact Finance team to increase budget or remove the hard limit."}
      </AlertDescription>
    </Alert>
  );
};

export const BudgetWarningIndicator = ({ budgetStatus }) => {
  if (!budgetStatus?.is_locked) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800 rounded-md text-sm">
      <AlertTriangle className="w-4 h-4 text-red-600" />
      <span className="text-red-700 dark:text-red-400 font-medium">
        Budget Locked - New tasks and time tracking disabled
      </span>
    </div>
  );
};
