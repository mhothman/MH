import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Input } from "../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { toast } from "sonner";
import { requestBudgetChange } from "../../api/budget-approvals";
import { TrendingUp, TrendingDown, AlertTriangle, Lock } from "lucide-react";

const CHANGE_TYPES = {
  amount_increase: { label: "Budget Increase", icon: TrendingUp, color: "text-green-500" },
  amount_decrease: { label: "Budget Decrease", icon: TrendingDown, color: "text-red-500" },
  threshold_change: { label: "Warning Threshold Change", icon: AlertTriangle, color: "text-yellow-500" },
  hard_limit_change: { label: "Hard Limit Toggle", icon: Lock, color: "text-orange-500" },
};

export const BudgetApprovalDialog = ({ open, onOpenChange, budget, orgId, onSuccess }) => {
  const [changeType, setChangeType] = useState("amount_increase");
  const [proposedValue, setProposedValue] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  const getCurrentValue = () => {
    switch (changeType) {
      case "amount_increase":
      case "amount_decrease":
        return budget?.total_budget || 0;
      case "threshold_change":
        return budget?.warning_threshold_percent || 80;
      case "hard_limit_change":
        return budget?.hard_limit ? 1 : 0;
      default:
        return 0;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!proposedValue || !reason.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }

    const currentValue = getCurrentValue();
    const proposed = parseFloat(proposedValue);

    if (isNaN(proposed)) {
      toast.error("Please enter a valid number");
      return;
    }

    // Validation based on change type
    if ((changeType === "amount_increase" || changeType === "amount_decrease") && proposed <= 0) {
      toast.error("Budget amount must be positive");
      return;
    }

    if (changeType === "threshold_change" && (proposed < 0 || proposed > 100)) {
      toast.error("Threshold must be between 0 and 100");
      return;
    }

    setLoading(true);
    try {
      await requestBudgetChange(orgId, {
        budget_id: budget.budget_id,
        change_type: changeType,
        current_value: currentValue,
        proposed_value: proposed,
        reason: reason.trim(),
      });

      toast.success("Budget change request submitted for approval");
      onOpenChange(false);
      if (onSuccess) onSuccess();
      
      // Reset form
      setChangeType("amount_increase");
      setProposedValue("");
      setReason("");
    } catch (error) {
      toast.error(error.message || "Failed to submit budget change request");
    } finally {
      setLoading(false);
    }
  };

  const getValueLabel = () => {
    switch (changeType) {
      case "amount_increase":
      case "amount_decrease":
        return `New Budget Amount (${budget?.currency || "EGP"})`;
      case "threshold_change":
        return "New Warning Threshold (%)";
      case "hard_limit_change":
        return "Hard Limit (0 = Off, 1 = On)";
      default:
        return "New Value";
    }
  };

  const ChangeIcon = CHANGE_TYPES[changeType]?.icon || TrendingUp;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ChangeIcon className={`w-5 h-5 ${CHANGE_TYPES[changeType]?.color}`} />
            Request Budget Change
          </DialogTitle>
          <DialogDescription>
            Submit a budget change request for approval by Finance team
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Project Info */}
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm font-medium">{budget?.project_name || "Unknown Project"}</p>
            <p className="text-xs text-muted-foreground">
              Current Budget: {budget?.currency} {budget?.total_budget?.toLocaleString() || 0}
            </p>
          </div>

          {/* Change Type */}
          <div className="space-y-2">
            <Label htmlFor="change_type">Change Type *</Label>
            <Select value={changeType} onValueChange={setChangeType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(CHANGE_TYPES).map(([key, { label, icon: Icon, color }]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${color}`} />
                      <span>{label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Current Value Display */}
          <div className="space-y-2">
            <Label>Current Value</Label>
            <Input value={getCurrentValue()} disabled />
          </div>

          {/* Proposed Value */}
          <div className="space-y-2">
            <Label htmlFor="proposed_value">{getValueLabel()} *</Label>
            <Input
              id="proposed_value"
              type="number"
              step={changeType === "threshold_change" ? "0.1" : "0.01"}
              value={proposedValue}
              onChange={(e) => setProposedValue(e.target.value)}
              placeholder="Enter new value"
              required
            />
          </div>

          {/* Reason */}
          <div className="space-y-2">
            <Label htmlFor="reason">Reason for Change *</Label>
            <Textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this budget change is needed..."
              rows={3}
              required
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Submitting..." : "Submit Request"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
