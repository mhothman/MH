/**
 * ApprovalBanner - Shows pending approval status and actions on a task
 */
import { useState } from "react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Textarea } from "../ui/textarea";
import { LoadingSpinner } from "../ui/loading-spinner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../ui/collapsible";
import { toast } from "sonner";
import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  User,
  MessageSquare,
  Shield,
  Info,
} from "lucide-react";
import { approveRequest, rejectRequest } from "../../api/workflows";
import { formatDistanceToNow } from "date-fns";

export function ApprovalBanner({
  approvalSummary,
  taskId,
  currentUserId,
  canApprove = false,
  canForceApprove = false,
  onApprovalComplete,
}) {
  const [actionDialog, setActionDialog] = useState({ open: false, action: null, isForce: false });
  const [comment, setComment] = useState("");
  const [processing, setProcessing] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  if (!approvalSummary) return null;

  const { has_pending_approval, pending_approval, approval_history, is_locked, can_user_approve } = approvalSummary;
  
  // Check if current user is the requester (they shouldn't see approve/reject buttons)
  const isRequester = pending_approval?.requested_by === currentUserId;
  // User can only approve if they're not the requester and have permission
  const showApproveButtons = (canApprove || can_user_approve) && !isRequester;

  const handleAction = async () => {
    if (!pending_approval) return;

    setProcessing(true);
    try {
      if (actionDialog.action === "approve") {
        await approveRequest(pending_approval.approval_id, comment || null, actionDialog.isForce);
        toast.success("Approval completed successfully");
      } else {
        await rejectRequest(pending_approval.approval_id, comment || null, actionDialog.isForce);
        toast.success("Request rejected");
      }
      setActionDialog({ open: false, action: null, isForce: false });
      setComment("");
      onApprovalComplete?.();
    } catch (error) {
      toast.error(error.message || `Failed to ${actionDialog.action}`);
    } finally {
      setProcessing(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "pending": return <Clock className="w-4 h-4 text-amber-500" />;
      case "approved": return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "rejected": return <XCircle className="w-4 h-4 text-red-500" />;
      case "expired": return <AlertTriangle className="w-4 h-4 text-gray-500" />;
      default: return null;
    }
  };

  const getActionIcon = (action) => {
    switch (action) {
      case "approve":
      case "force_approve": return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case "reject":
      case "force_reject": return <XCircle className="w-3 h-3 text-red-500" />;
      case "requested": return <Clock className="w-3 h-3 text-amber-500" />;
      case "expired": return <AlertTriangle className="w-3 h-3 text-gray-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-3">
      {/* Pending Approval Banner */}
      {has_pending_approval && pending_approval && (
        <div
          className="border rounded-lg p-4 bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800"
          data-testid="pending-approval-banner"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-amber-100 dark:bg-amber-900/50">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h4 className="font-medium text-amber-800 dark:text-amber-200">
                  Approval Pending
                </h4>
                <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                  Waiting for approval to change status to{" "}
                  <Badge variant="outline" className="text-xs capitalize">
                    {pending_approval.target_status.replace(/_/g, " ")}
                  </Badge>
                </p>
                <div className="flex items-center gap-4 mt-2 text-xs text-amber-600 dark:text-amber-400">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {pending_approval.approval_type === "single" ? "Single" : "Multi"} approval
                  </span>
                  <span className="capitalize">
                    {pending_approval.approver_role?.replace(/_/g, " ")} required
                  </span>
                  {pending_approval.expires_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Expires {formatDistanceToNow(new Date(pending_approval.expires_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
                {pending_approval.approval_type === "multi" && (
                  <div className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                    Progress: {pending_approval.approved_by?.length || 0} / {pending_approval.required_approvers?.length || 0} approvers
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2">
              {showApproveButtons && (
                <>
                  <Button
                    size="sm"
                    variant="default"
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => setActionDialog({ open: true, action: "approve", isForce: false })}
                    data-testid="approve-btn"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-1" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 border-red-300 hover:bg-red-50"
                    onClick={() => setActionDialog({ open: true, action: "reject", isForce: false })}
                    data-testid="reject-btn"
                  >
                    <XCircle className="w-4 h-4 mr-1" />
                    Reject
                  </Button>
                </>
              )}
              {isRequester && (
                <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                  <Info className="w-3 h-3 inline mr-1" />
                  Waiting for approver action
                </div>
              )}
              {canForceApprove && !can_user_approve && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-amber-600 border-amber-300"
                    onClick={() => setActionDialog({ open: true, action: "approve", isForce: true })}
                    data-testid="force-approve-btn"
                  >
                    <Shield className="w-4 h-4 mr-1" />
                    Force Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-600"
                    onClick={() => setActionDialog({ open: true, action: "reject", isForce: true })}
                    data-testid="force-reject-btn"
                  >
                    <Shield className="w-4 h-4 mr-1" />
                    Force Reject
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Locked Banner */}
      {is_locked && !has_pending_approval && (
        <div className="border rounded-lg p-3 bg-gray-50 border-gray-200 dark:bg-gray-900/50 dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <AlertTriangle className="w-4 h-4" />
            Task is locked. Please wait for approval process to complete.
          </div>
        </div>
      )}

      {/* Approval History */}
      {approval_history && approval_history.length > 0 && (
        <Collapsible open={historyOpen} onOpenChange={setHistoryOpen}>
          <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground w-full justify-between p-2 rounded hover:bg-muted/50">
            <span className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Approval History ({approval_history.length})
            </span>
            {historyOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 space-y-2 pl-2 border-l-2 border-muted ml-2">
              {approval_history.map((action, idx) => (
                <div key={action.action_id || idx} className="flex items-start gap-3 text-sm py-2">
                  <div className="mt-0.5">{getActionIcon(action.action)}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{action.actor_name || "Unknown"}</span>
                      <span className="text-muted-foreground capitalize">
                        {action.action.replace(/_/g, " ")}
                      </span>
                    </div>
                    {action.comment && (
                      <p className="text-muted-foreground mt-1 text-xs italic">
                        &ldquo;{action.comment}&rdquo;
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(action.acted_at), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Action Dialog */}
      <AlertDialog open={actionDialog.open} onOpenChange={(open) => setActionDialog({ ...actionDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {actionDialog.isForce && <Shield className="w-4 h-4 inline mr-2 text-amber-500" />}
              {actionDialog.action === "approve" ? "Approve" : "Reject"} Request
              {actionDialog.isForce && " (Admin Override)"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {actionDialog.action === "approve"
                ? "This will approve the status change and update the task."
                : "This will reject the request and keep the task at its current status."
              }
              {actionDialog.isForce && (
                <span className="block mt-2 text-amber-600">
                  You are using admin override to {actionDialog.action} this request.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Add a comment (optional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              data-testid="approval-comment-input"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setComment("")}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleAction}
              disabled={processing}
              className={actionDialog.action === "approve" 
                ? "bg-green-600 hover:bg-green-700" 
                : "bg-red-600 hover:bg-red-700"
              }
            >
              {processing ? (
                <LoadingSpinner size="sm" />
              ) : (
                <>
                  {actionDialog.action === "approve" ? (
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                  ) : (
                    <XCircle className="w-4 h-4 mr-2" />
                  )}
                  {actionDialog.action === "approve" ? "Approve" : "Reject"}
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
