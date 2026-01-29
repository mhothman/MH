/**
 * ProjectBudgetTab - Budget management tab for project detail page
 */
import { useState, useEffect } from "react";
import { format } from "date-fns";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";
import { Switch } from "../ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../ui/tabs";
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
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  DollarSign,
  Wallet,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lock,
  Unlock,
  Plus,
  Edit,
  Trash2,
  History,
  Receipt,
  Clock,
  Calculator,
  Settings,
  FileText,
  PiggyBank,
} from "lucide-react";
import {
  getBudgetByProject,
  getBudgetSummary,
  createBudget,
  updateBudget,
  deleteBudget,
  getTransactions,
  createTransaction,
  deleteTransaction,
  getBudgetRevisions,
  getProjectExpenses,
  createExpense,
  updateExpense,
  deleteExpense,
  overrideBudgetLock,
  CURRENCIES,
  EXPENSE_CATEGORIES,
  BUDGET_STATUS,
  formatCurrency,
  getCurrencySymbol,
} from "../../api/budgets";

export function ProjectBudgetTab({ project, permissions, documents = [] }) {
  const [loading, setLoading] = useState(true);
  const [budget, setBudget] = useState(null);
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [revisions, setRevisions] = useState([]);
  const [activeSubTab, setActiveSubTab] = useState("overview");
  
  // Dialog states
  const [budgetDialogOpen, setBudgetDialogOpen] = useState(false);
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false);
  const [transactionDialogOpen, setTransactionDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  
  // Form states
  const [editingBudget, setEditingBudget] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [saving, setSaving] = useState(false);
  
  const [budgetForm, setBudgetForm] = useState({
    total_budget: "",
    currency: "USD",
    warning_threshold_percent: 80,
    hard_limit: false,
    notes: "",
  });
  
  const [expenseForm, setExpenseForm] = useState({
    title: "",
    amount: "",
    currency: "USD",
    category: "general",
    date: format(new Date(), "yyyy-MM-dd"),
    description: "",
    document_id: "",
  });
  
  const [transactionForm, setTransactionForm] = useState({
    amount: "",
    description: "",
    source: "manual",
  });

  // Permission helpers
  const canEdit = permissions?.includes("budget:edit") || permissions?.includes("budget:create");
  const canDelete = permissions?.includes("budget:delete");
  const canOverride = permissions?.includes("budget:override");
  const canCreateExpense = permissions?.includes("expense:create");
  const canEditExpense = permissions?.includes("expense:edit");
  const canDeleteExpense = permissions?.includes("expense:delete");

  useEffect(() => {
    loadBudgetData();
  }, [project.project_id]);

  const loadBudgetData = async () => {
    setLoading(true);
    try {
      // Try to get existing budget
      try {
        const budgetData = await getBudgetByProject(project.project_id);
        setBudget(budgetData);
        
        // Load summary, transactions, expenses, revisions
        const [summaryData, txnData, expData, revData] = await Promise.all([
          getBudgetSummary(budgetData.budget_id),
          getTransactions(budgetData.budget_id),
          getProjectExpenses(project.project_id),
          getBudgetRevisions(budgetData.budget_id),
        ]);
        
        setSummary(summaryData);
        setTransactions(txnData);
        setExpenses(expData);
        setRevisions(revData);
      } catch (e) {
        // No budget yet
        setBudget(null);
        setSummary(null);
        // Still try to load expenses
        try {
          const expData = await getProjectExpenses(project.project_id);
          setExpenses(expData);
        } catch {
          setExpenses([]);
        }
      }
    } catch (error) {
      console.error("Failed to load budget data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBudget = async () => {
    if (!budgetForm.total_budget || parseFloat(budgetForm.total_budget) <= 0) {
      toast.error("Please enter a valid budget amount");
      return;
    }
    
    setSaving(true);
    try {
      const created = await createBudget(project.org_id, {
        project_id: project.project_id,
        total_budget: parseFloat(budgetForm.total_budget),
        currency: budgetForm.currency,
        warning_threshold_percent: budgetForm.warning_threshold_percent,
        hard_limit: budgetForm.hard_limit,
        notes: budgetForm.notes || null,
      });
      
      setBudget(created);
      setBudgetDialogOpen(false);
      toast.success("Budget created successfully");
      loadBudgetData();
    } catch (error) {
      toast.error(error.message || "Failed to create budget");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateBudget = async () => {
    if (!budgetForm.total_budget || parseFloat(budgetForm.total_budget) <= 0) {
      toast.error("Please enter a valid budget amount");
      return;
    }
    
    setSaving(true);
    try {
      const updated = await updateBudget(budget.budget_id, {
        total_budget: parseFloat(budgetForm.total_budget),
        currency: budgetForm.currency,
        warning_threshold_percent: budgetForm.warning_threshold_percent,
        hard_limit: budgetForm.hard_limit,
        notes: budgetForm.notes || null,
      }, "Budget updated");
      
      setBudget(updated);
      setBudgetDialogOpen(false);
      setEditingBudget(false);
      toast.success("Budget updated successfully");
      loadBudgetData();
    } catch (error) {
      toast.error(error.message || "Failed to update budget");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBudget = async () => {
    try {
      await deleteBudget(budget.budget_id);
      setBudget(null);
      setSummary(null);
      setTransactions([]);
      setRevisions([]);
      setDeleteDialogOpen(false);
      setItemToDelete(null);
      toast.success("Budget deleted successfully");
    } catch (error) {
      toast.error(error.message || "Failed to delete budget");
    }
  };

  const handleCreateExpense = async () => {
    if (!expenseForm.title.trim()) {
      toast.error("Please enter an expense title");
      return;
    }
    if (!expenseForm.amount || parseFloat(expenseForm.amount) <= 0) {
      toast.error("Please enter a valid amount");
      return;
    }
    
    setSaving(true);
    try {
      await createExpense(project.org_id, {
        project_id: project.project_id,
        title: expenseForm.title,
        amount: parseFloat(expenseForm.amount),
        currency: expenseForm.currency,
        category: expenseForm.category,
        date: expenseForm.date,
        description: expenseForm.description || null,
        document_id: expenseForm.document_id && expenseForm.document_id !== "" ? expenseForm.document_id : null,
      });
      
      toast.success("Expense created successfully");
      setExpenseDialogOpen(false);
      resetExpenseForm();
      
      // Reload data in background - don't fail the whole operation if this fails
      loadBudgetData().catch((err) => {
        console.error("Failed to reload budget data after expense creation:", err);
      });
    } catch (error) {
      toast.error(error.message || "Failed to create expense");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateExpense = async () => {
    if (!expenseForm.title.trim()) {
      toast.error("Please enter an expense title");
      return;
    }
    
    setSaving(true);
    try {
      await updateExpense(editingExpense.expense_id, {
        title: expenseForm.title,
        amount: parseFloat(expenseForm.amount),
        currency: expenseForm.currency,
        category: expenseForm.category,
        date: expenseForm.date,
        description: expenseForm.description || null,
        document_id: expenseForm.document_id && expenseForm.document_id !== "" ? expenseForm.document_id : null,
      });
      
      toast.success("Expense updated successfully");
      setExpenseDialogOpen(false);
      setEditingExpense(null);
      resetExpenseForm();
      
      // Reload data in background
      loadBudgetData().catch((err) => {
        console.error("Failed to reload budget data after expense update:", err);
      });
    } catch (error) {
      toast.error(error.message || "Failed to update expense");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExpense = async () => {
    try {
      await deleteExpense(itemToDelete.expense_id);
      toast.success("Expense deleted successfully");
      setDeleteDialogOpen(false);
      setItemToDelete(null);
      
      // Reload data in background
      loadBudgetData().catch((err) => {
        console.error("Failed to reload budget data after expense deletion:", err);
      });
    } catch (error) {
      toast.error(error.message || "Failed to delete expense");
    }
  };

  const handleCreateTransaction = async () => {
    if (!transactionForm.amount || parseFloat(transactionForm.amount) === 0) {
      toast.error("Please enter a valid amount");
      return;
    }
    
    setSaving(true);
    try {
      await createTransaction(budget.budget_id, {
        source: transactionForm.source,
        amount: parseFloat(transactionForm.amount),
        description: transactionForm.description || null,
      });
      
      toast.success("Transaction created successfully");
      setTransactionDialogOpen(false);
      setTransactionForm({ amount: "", description: "", source: "manual" });
      
      // Reload data in background
      loadBudgetData().catch((err) => {
        console.error("Failed to reload budget data after transaction creation:", err);
      });
    } catch (error) {
      toast.error(error.message || "Failed to create transaction");
    } finally {
      setSaving(false);
    }
  };

  const handleOverrideLock = async () => {
    try {
      await overrideBudgetLock(budget.budget_id);
      toast.success("Budget lock overridden");
      loadBudgetData();
    } catch (error) {
      toast.error(error.message || "Failed to override lock");
    }
  };

  const resetExpenseForm = () => {
    setExpenseForm({
      title: "",
      amount: "",
      currency: "USD",
      category: "general",
      date: format(new Date(), "yyyy-MM-dd"),
      description: "",
      document_id: "",
    });
  };

  const openEditExpense = (expense) => {
    setEditingExpense(expense);
    setExpenseForm({
      title: expense.title,
      amount: expense.amount.toString(),
      currency: expense.currency,
      category: expense.category,
      date: expense.date,
      description: expense.description || "",
      document_id: expense.document_id || "",
    });
    setExpenseDialogOpen(true);
  };

  const openEditBudget = () => {
    setEditingBudget(true);
    setBudgetForm({
      total_budget: budget.total_budget.toString(),
      currency: budget.currency,
      warning_threshold_percent: budget.warning_threshold_percent,
      hard_limit: budget.hard_limit,
      notes: budget.notes || "",
    });
    setBudgetDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const config = BUDGET_STATUS[status] || BUDGET_STATUS.active;
    return (
      <Badge variant="outline" className={`${config.textColor} border-current`}>
        {status === "locked" && <Lock className="w-3 h-3 mr-1" />}
        {status === "warning" && <AlertTriangle className="w-3 h-3 mr-1" />}
        {config.label}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  // No budget yet - show create option
  if (!budget) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <PiggyBank className="w-16 h-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Budget Defined</h3>
            <p className="text-muted-foreground text-center mb-6 max-w-md">
              Set up a budget for this project to track spending, receive alerts when thresholds are reached, and optionally enforce spending limits.
            </p>
            {canEdit && (
              <Dialog open={budgetDialogOpen} onOpenChange={setBudgetDialogOpen}>
                <DialogTrigger asChild>
                  <Button data-testid="create-budget-btn">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Budget
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Project Budget</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Total Budget <span className="text-destructive">*</span></Label>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="50000"
                          value={budgetForm.total_budget}
                          onChange={(e) => setBudgetForm({ ...budgetForm, total_budget: e.target.value })}
                          data-testid="budget-amount-input"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Currency</Label>
                        <Select
                          value={budgetForm.currency}
                          onValueChange={(value) => setBudgetForm({ ...budgetForm, currency: value })}
                        >
                          <SelectTrigger data-testid="budget-currency-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {CURRENCIES.map((c) => (
                              <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Warning Threshold (%)</Label>
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        value={budgetForm.warning_threshold_percent}
                        onChange={(e) => setBudgetForm({ ...budgetForm, warning_threshold_percent: parseFloat(e.target.value) || 80 })}
                      />
                      <p className="text-xs text-muted-foreground">Alert when budget usage exceeds this percentage</p>
                    </div>
                    
                    <div className="flex items-center justify-between rounded-lg border p-3">
                      <div className="space-y-0.5">
                        <Label className="text-base">Hard Limit</Label>
                        <p className="text-sm text-muted-foreground">Block operations when budget is exceeded</p>
                      </div>
                      <Switch
                        checked={budgetForm.hard_limit}
                        onCheckedChange={(checked) => setBudgetForm({ ...budgetForm, hard_limit: checked })}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Notes</Label>
                      <Textarea
                        placeholder="Budget notes (optional)"
                        value={budgetForm.notes}
                        onChange={(e) => setBudgetForm({ ...budgetForm, notes: e.target.value })}
                      />
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-4">
                      <Button variant="outline" onClick={() => setBudgetDialogOpen(false)}>Cancel</Button>
                      <Button onClick={handleCreateBudget} disabled={saving}>
                        {saving ? <LoadingSpinner className="w-4 h-4 mr-2" /> : null}
                        Create Budget
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </CardContent>
        </Card>
        
        {/* Still show expenses even without budget */}
        {expenses.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Receipt className="w-5 h-5" />
                Expenses
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ExpenseTable
                expenses={expenses}
                currency="USD"
                canEdit={canEditExpense}
                canDelete={canDeleteExpense}
                onEdit={openEditExpense}
                onDelete={(exp) => { setItemToDelete(exp); setDeleteDialogOpen(true); }}
              />
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // Budget exists - show full UI
  return (
    <div className="space-y-6">
      {/* Budget Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Budget</p>
                <p className="text-2xl font-bold">{formatCurrency(budget.total_budget, budget.currency)}</p>
              </div>
              <Wallet className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Spent</p>
                <p className="text-2xl font-bold">{formatCurrency(budget.spent_amount, budget.currency)}</p>
              </div>
              <TrendingUp className={`w-8 h-8 ${budget.spent_percent > 80 ? "text-red-500" : "text-muted-foreground"}`} />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Remaining</p>
                <p className={`text-2xl font-bold ${budget.remaining_amount < 0 ? "text-red-500" : ""}`}>
                  {formatCurrency(budget.remaining_amount, budget.currency)}
                </p>
              </div>
              <PiggyBank className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <div className="mt-1">{getStatusBadge(budget.status)}</div>
              </div>
              {budget.status === "locked" && canOverride && (
                <Button variant="outline" size="sm" onClick={handleOverrideLock}>
                  <Unlock className="w-4 h-4 mr-1" />
                  Override
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Budget Usage</span>
              <span className={budget.spent_percent > 100 ? "text-red-500 font-medium" : ""}>
                {budget.spent_percent.toFixed(1)}%
              </span>
            </div>
            <Progress
              value={Math.min(budget.spent_percent, 100)}
              className={`h-3 ${budget.spent_percent > 100 ? "[&>div]:bg-red-500" : budget.spent_percent > budget.warning_threshold_percent ? "[&>div]:bg-yellow-500" : ""}`}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Warning at {budget.warning_threshold_percent}%</span>
              {summary?.burn_rate_daily && (
                <span>Burn rate: {formatCurrency(summary.burn_rate_daily, budget.currency)}/day</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sub-tabs */}
      <Tabs value={activeSubTab} onValueChange={setActiveSubTab}>
        <div className="flex justify-between items-center">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="expenses">Expenses</TabsTrigger>
            <TabsTrigger value="transactions">Transactions</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          
          <div className="flex gap-2">
            {canCreateExpense && (
              <Button variant="outline" size="sm" onClick={() => { resetExpenseForm(); setEditingExpense(null); setExpenseDialogOpen(true); }}>
                <Plus className="w-4 h-4 mr-1" />
                Add Expense
              </Button>
            )}
            {canEdit && (
              <Button variant="outline" size="sm" onClick={openEditBudget}>
                <Settings className="w-4 h-4 mr-1" />
                Settings
              </Button>
            )}
          </div>
        </div>

        <TabsContent value="overview" className="space-y-4 mt-4">
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Time Costs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{formatCurrency(summary.time_cost, budget.currency)}</p>
                  <p className="text-xs text-muted-foreground">From time tracking</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Receipt className="w-4 h-4" />
                    Expenses
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{formatCurrency(summary.expense_cost, budget.currency)}</p>
                  <p className="text-xs text-muted-foreground">{expenses.length} expense entries</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Calculator className="w-4 h-4" />
                    Manual Adjustments
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{formatCurrency(summary.manual_adjustments, budget.currency)}</p>
                  <p className="text-xs text-muted-foreground">Direct entries</p>
                </CardContent>
              </Card>
            </div>
          )}
          
          {summary?.days_remaining && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <TrendingDown className="w-8 h-8 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Budget Projection</p>
                    <p className="text-sm text-muted-foreground">
                      At current spend rate, budget will be exhausted in approximately <span className="font-medium">{summary.days_remaining} days</span>
                      {summary.projected_end_date && ` (around ${summary.projected_end_date})`}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="expenses" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {expenses.length === 0 ? (
                <div className="text-center py-8">
                  <Receipt className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No expenses recorded yet</p>
                </div>
              ) : (
                <ExpenseTable
                  expenses={expenses}
                  currency={budget.currency}
                  canEdit={canEditExpense}
                  canDelete={canDeleteExpense}
                  onEdit={openEditExpense}
                  onDelete={(exp) => { setItemToDelete(exp); setDeleteDialogOpen(true); }}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="transactions" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Budget Transactions</CardTitle>
              {canEdit && (
                <Button variant="outline" size="sm" onClick={() => setTransactionDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-1" />
                  Manual Entry
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {transactions.length === 0 ? (
                <div className="text-center py-8">
                  <History className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No transactions yet</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Created By</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transactions.map((txn) => (
                      <TableRow key={txn.transaction_id}>
                        <TableCell className="text-sm">
                          {format(new Date(txn.created_at), "MMM d, yyyy")}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">{txn.source.replace("_", " ")}</Badge>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">{txn.description || "-"}</TableCell>
                        <TableCell className={`text-right font-medium ${txn.amount < 0 ? "text-green-500" : ""}`}>
                          {txn.amount < 0 ? "-" : "+"}{formatCurrency(Math.abs(txn.amount), budget.currency)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{txn.created_by_name || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Budget Revision History</CardTitle>
            </CardHeader>
            <CardContent>
              {revisions.length === 0 ? (
                <div className="text-center py-8">
                  <History className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No revisions yet</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Previous</TableHead>
                      <TableHead>New</TableHead>
                      <TableHead>Change</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>By</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revisions.map((rev) => (
                      <TableRow key={rev.revision_id}>
                        <TableCell className="text-sm">
                          {format(new Date(rev.created_at), "MMM d, yyyy")}
                        </TableCell>
                        <TableCell>{formatCurrency(rev.previous_budget, budget.currency)}</TableCell>
                        <TableCell>{formatCurrency(rev.new_budget, budget.currency)}</TableCell>
                        <TableCell className={rev.change_amount > 0 ? "text-green-500" : "text-red-500"}>
                          {rev.change_amount > 0 ? "+" : ""}{formatCurrency(rev.change_amount, budget.currency)}
                        </TableCell>
                        <TableCell className="max-w-[150px] truncate">{rev.reason || "-"}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{rev.created_by_name || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Budget Dialog */}
      <Dialog open={budgetDialogOpen && editingBudget} onOpenChange={(open) => { setBudgetDialogOpen(open); if (!open) setEditingBudget(false); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Budget Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Total Budget <span className="text-destructive">*</span></Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={budgetForm.total_budget}
                  onChange={(e) => setBudgetForm({ ...budgetForm, total_budget: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Select value={budgetForm.currency} onValueChange={(value) => setBudgetForm({ ...budgetForm, currency: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Warning Threshold (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={budgetForm.warning_threshold_percent}
                onChange={(e) => setBudgetForm({ ...budgetForm, warning_threshold_percent: parseFloat(e.target.value) || 80 })}
              />
            </div>
            
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label className="text-base">Hard Limit</Label>
                <p className="text-sm text-muted-foreground">Block operations when budget is exceeded</p>
              </div>
              <Switch
                checked={budgetForm.hard_limit}
                onCheckedChange={(checked) => setBudgetForm({ ...budgetForm, hard_limit: checked })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={budgetForm.notes}
                onChange={(e) => setBudgetForm({ ...budgetForm, notes: e.target.value })}
              />
            </div>
            
            <div className="flex justify-between pt-4">
              {canDelete && (
                <Button variant="destructive" onClick={() => { setItemToDelete({ type: "budget" }); setDeleteDialogOpen(true); }}>
                  <Trash2 className="w-4 h-4 mr-1" />
                  Delete Budget
                </Button>
              )}
              <div className="flex gap-2 ml-auto">
                <Button variant="outline" onClick={() => { setBudgetDialogOpen(false); setEditingBudget(false); }}>Cancel</Button>
                <Button onClick={handleUpdateBudget} disabled={saving}>
                  {saving && <LoadingSpinner className="w-4 h-4 mr-2" />}
                  Save Changes
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Expense Dialog */}
      <Dialog open={expenseDialogOpen} onOpenChange={(open) => { setExpenseDialogOpen(open); if (!open) { setEditingExpense(null); resetExpenseForm(); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingExpense ? "Edit Expense" : "Add Expense"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label>Title <span className="text-destructive">*</span></Label>
              <Input
                placeholder="Expense title"
                value={expenseForm.title}
                onChange={(e) => setExpenseForm({ ...expenseForm, title: e.target.value })}
                data-testid="expense-title-input"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Amount <span className="text-destructive">*</span></Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  value={expenseForm.amount}
                  onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                  data-testid="expense-amount-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Select value={expenseForm.currency} onValueChange={(value) => setExpenseForm({ ...expenseForm, currency: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category</Label>
                <Select value={expenseForm.category} onValueChange={(value) => setExpenseForm({ ...expenseForm, category: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXPENSE_CATEGORIES.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Date <span className="text-destructive">*</span></Label>
                <Input
                  type="date"
                  value={expenseForm.date}
                  onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                />
              </div>
            </div>
            
            {documents.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Attach Document (Receipt/Invoice)
                </Label>
                <Select value={expenseForm.document_id || "none"} onValueChange={(value) => setExpenseForm({ ...expenseForm, document_id: value === "none" ? "" : value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select document (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {documents.map((doc) => (
                      <SelectItem key={doc.document_id} value={doc.document_id}>{doc.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Expense description (optional)"
                value={expenseForm.description}
                onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
              />
            </div>
            
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => { setExpenseDialogOpen(false); setEditingExpense(null); resetExpenseForm(); }}>Cancel</Button>
              <Button onClick={editingExpense ? handleUpdateExpense : handleCreateExpense} disabled={saving}>
                {saving && <LoadingSpinner className="w-4 h-4 mr-2" />}
                {editingExpense ? "Update" : "Add"} Expense
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Transaction Dialog */}
      <Dialog open={transactionDialogOpen} onOpenChange={setTransactionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Manual Transaction</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label>Amount <span className="text-destructive">*</span></Label>
              <Input
                type="number"
                step="0.01"
                placeholder="Enter positive for expense, negative for credit"
                value={transactionForm.amount}
                onChange={(e) => setTransactionForm({ ...transactionForm, amount: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">Use positive values for costs, negative for credits/refunds</p>
            </div>
            
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={transactionForm.source} onValueChange={(value) => setTransactionForm({ ...transactionForm, source: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manual Entry</SelectItem>
                  <SelectItem value="adjustment">Adjustment</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Transaction description"
                value={transactionForm.description}
                onChange={(e) => setTransactionForm({ ...transactionForm, description: e.target.value })}
              />
            </div>
            
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setTransactionDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateTransaction} disabled={saving}>
                {saving && <LoadingSpinner className="w-4 h-4 mr-2" />}
                Add Transaction
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Delete</AlertDialogTitle>
            <AlertDialogDescription>
              {itemToDelete?.type === "budget" 
                ? "Are you sure you want to delete this budget? This will remove all transaction history and cannot be undone."
                : `Are you sure you want to delete "${itemToDelete?.title}"? This action cannot be undone.`
              }
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={itemToDelete?.type === "budget" ? handleDeleteBudget : handleDeleteExpense}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// Expense Table Component
function ExpenseTable({ expenses, currency, canEdit, canDelete, onEdit, onDelete }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Title</TableHead>
          <TableHead>Category</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead>Document</TableHead>
          <TableHead>Created By</TableHead>
          {(canEdit || canDelete) && <TableHead className="w-[80px]">Actions</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {expenses.map((exp) => (
          <TableRow key={exp.expense_id}>
            <TableCell className="text-sm">{exp.date}</TableCell>
            <TableCell className="font-medium">{exp.title}</TableCell>
            <TableCell>
              <Badge variant="outline" className="capitalize">{exp.category}</Badge>
            </TableCell>
            <TableCell className="text-right font-medium">
              {formatCurrency(exp.amount, exp.currency)}
            </TableCell>
            <TableCell className="text-sm">
              {exp.document_title ? (
                <span className="flex items-center gap-1 text-blue-500">
                  <FileText className="w-3 h-3" />
                  {exp.document_title}
                </span>
              ) : "-"}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">{exp.created_by_name || "-"}</TableCell>
            {(canEdit || canDelete) && (
              <TableCell>
                <div className="flex gap-1">
                  {canEdit && (
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(exp)}>
                      <Edit className="w-4 h-4" />
                    </Button>
                  )}
                  {canDelete && (
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => onDelete(exp)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default ProjectBudgetTab;
