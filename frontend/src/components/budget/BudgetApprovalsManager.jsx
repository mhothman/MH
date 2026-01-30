import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  getPendingApprovals,
  approveBudgetChange,
  rejectBudgetChange,
} from "../../api/budget-approvals";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lock,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const CHANGE_TYPE_CONFIG = {
  amount_increase: { label: "Budget Increase", icon: TrendingUp, color: "text-green-500" },
  amount_decrease: { label: "Budget Decrease", icon: TrendingDown, color: "text-red-500" },
  threshold_change: { label: "Threshold Change", icon: AlertTriangle, color: "text-yellow-500" },
  hard_limit_change: { label: "Hard Limit Change", icon: Lock, color: "text-orange-500" },
};

export const BudgetApprovalsManager = ({ orgId }) => {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [action, setAction] = useState(null); // 'approve' or 'reject'
  const [notes, setNotes] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadApprovals();
  }, [orgId]);

  const loadApprovals = async () => {
    try {
      const data = await getPendingApprovals(orgId);
      setApprovals(data || []);
    } catch (error) {
      console.error("Failed to load approvals:", error);
      toast.error("Failed to load pending approvals");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;

    setProcessing(true);
    try {
      await approveBudgetChange(selectedApproval.approval_id, orgId, notes.trim() || null);
      toast.success("Budget change approved successfully");
      setSelectedApproval(null);
      setAction(null);
      setNotes("");
      loadApprovals();
    } catch (error) {
      toast.error(error.message || "Failed to approve budget change");
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval || !notes.trim()) {
      toast.error("Please provide a reason for rejection");
      return;
    }

    setProcessing(true);
    try {
      await rejectBudgetChange(selectedApproval.approval_id, orgId, notes.trim());
      toast.success("Budget change rejected");
      setSelectedApproval(null);
      setAction(null);
      setNotes("");
      loadApprovals();
    } catch (error) {
      toast.error(error.message || "Failed to reject budget change");
    } finally {
      setProcessing(false);
    }
  };

  const formatValue = (value, changeType, currency = "EGP") => {
    if (changeType === "threshold_change") {
      return `${value}%`;
    } else if (changeType === "hard_limit_change") {
      return value === 1 ? "Enabled" : "Disabled";
    } else {
      return `${currency} ${value.toLocaleString()}`;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (approvals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Budget Approval Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No pending approval requests</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Budget Approval Requests</CardTitle>
            <Badge variant="secondary">{approvals.length} pending</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {approvals.map((approval) => {
              const config = CHANGE_TYPE_CONFIG[approval.change_type] || {};
              const Icon = config.icon || TrendingUp;

              return (
                <div
                  key={approval.approval_id}
                  className="p-4 border rounded-lg bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      {/* Header */}
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${config.color}`} />
                        <span className="font-medium">{approval.project_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {config.label}
                        </Badge>
                      </div>

                      {/* Change Details */}
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                        <div>
                          <span className="text-muted-foreground">Current: </span>
                          <span className="font-mono">
                            {formatValue(approval.current_value, approval.change_type)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Proposed: </span>
                          <span className="font-mono font-medium">
                            {formatValue(approval.proposed_value, approval.change_type)}
                          </span>
                        </div>
                      </div>

                      {/* Reason */}
                      {approval.reason && (
                        <p className="text-sm text-muted-foreground italic">
                          "{approval.reason}"
                        </p>
                      )}

                      {/* Requester & Time */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Requested by {approval.requester_name}</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => {
                          setSelectedApproval(approval);
                          setAction("approve");
                        }}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          setSelectedApproval(approval);
                          setAction("reject");
                        }}
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Approval/Rejection Dialog */}
      <Dialog
        open={!!selectedApproval && !!action}
        onOpenChange={() => {
          setSelectedApproval(null);
          setAction(null);
          setNotes("");
        }}
      >
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {action === "approve" ? "Approve Budget Change" : "Reject Budget Change"}
            </DialogTitle>
            <DialogDescription>
              {selectedApproval?.project_name} -{" "}
              {CHANGE_TYPE_CONFIG[selectedApproval?.change_type]?.label}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Change Summary */}
            <div className="p-3 bg-muted rounded-lg space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Value:</span>
                <span className="font-mono">
                  {formatValue(selectedApproval?.current_value, selectedApproval?.change_type)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Proposed Value:</span>
                <span className="font-mono font-medium">
                  {formatValue(selectedApproval?.proposed_value, selectedApproval?.change_type)}
                </span>
              </div>
              {selectedApproval?.reason && (
                <div className="pt-2 border-t">
                  <span className="text-muted-foreground">Reason:</span>
                  <p className="italic mt-1">{selectedApproval.reason}</p>
                </div>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">
                {action === "approve" ? "Notes (Optional)" : "Rejection Reason *"}
              </Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={
                  action === "approve"
                    ? "Add any notes or conditions..."
                    : "Explain why this request is being rejected..."
                }
                rows={3}
                required={action === "reject"}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setSelectedApproval(null);
                setAction(null);
                setNotes("");
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant={action === "approve" ? "default" : "destructive"}
              onClick={action === "approve" ? handleApprove : handleReject}
              disabled={processing || (action === "reject" && !notes.trim())}
            >
              {processing
                ? "Processing..."
                : action === "approve"
                ? "Approve Change"
                : "Reject Change"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
