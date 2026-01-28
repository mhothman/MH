/**
 * ApprovalStatusIndicator - Shows approval status badge on task cards
 */
import { Badge } from "../ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { Clock, Lock, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export function ApprovalStatusIndicator({ task }) {
  const isLocked = task?.approval_locked;
  const hasPendingApproval = task?.pending_approval_id;

  if (!isLocked && !hasPendingApproval) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="gap-1 text-xs py-0 h-5 cursor-help border-amber-400 text-amber-600 bg-amber-50 dark:bg-amber-950/30"
            data-testid="approval-status-indicator"
          >
            {isLocked ? (
              <>
                <Lock className="w-3 h-3" />
                <span className="hidden sm:inline">Locked</span>
              </>
            ) : (
              <>
                <Clock className="w-3 h-3" />
                <span className="hidden sm:inline">Pending</span>
              </>
            )}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>Task is pending approval</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * RequestApprovalButton - Button to request approval for a status change
 */
export function RequestApprovalButton({ onClick, disabled, targetStatus }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50 disabled:cursor-not-allowed"
      data-testid="request-approval-btn"
    >
      <Clock className="w-3 h-3" />
      Request Approval
    </button>
  );
}
