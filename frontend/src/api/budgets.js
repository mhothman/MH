/**
 * Budget API client functions
 */
import { get, post, put, del } from './client';

// ==================== Budget Operations ====================

export const createBudget = async (orgId, budgetData) => {
  return post(`/api/budgets/?org_id=${orgId}`, budgetData);
};

export const getBudgetByProject = async (projectId) => {
  return get(`/api/budgets/project/${projectId}`);
};

export const getOrgBudgets = async (orgId) => {
  return get(`/api/budgets/org/${orgId}`);
};

export const getBudget = async (budgetId) => {
  return get(`/api/budgets/${budgetId}`);
};

export const updateBudget = async (budgetId, data, reason = null) => {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return put(`/api/budgets/${budgetId}${query}`, data);
};

export const deleteBudget = async (budgetId) => {
  return del(`/api/budgets/${budgetId}`);
};

export const getBudgetSummary = async (budgetId) => {
  return get(`/api/budgets/${budgetId}/summary`);
};

export const overrideBudgetLock = async (budgetId) => {
  return post(`/api/budgets/${budgetId}/override-lock`, {});
};

// ==================== Transaction Operations ====================

export const createTransaction = async (budgetId, transactionData) => {
  return post(`/api/budgets/${budgetId}/transactions`, transactionData);
};

export const getTransactions = async (budgetId, { source, limit = 100, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  if (source) params.append('source', source);
  params.append('limit', limit);
  params.append('offset', offset);
  return get(`/api/budgets/${budgetId}/transactions?${params.toString()}`);
};

export const deleteTransaction = async (transactionId) => {
  return del(`/api/budgets/transactions/${transactionId}`);
};

// ==================== Revision History ====================

export const getBudgetRevisions = async (budgetId) => {
  return get(`/api/budgets/${budgetId}/revisions`);
};

// ==================== Expense Operations ====================

export const createExpense = async (orgId, expenseData) => {
  return post(`/api/budgets/expenses/?org_id=${orgId}`, expenseData);
};

export const getProjectExpenses = async (projectId, { category, limit = 100, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  params.append('limit', limit);
  params.append('offset', offset);
  return get(`/api/budgets/expenses/project/${projectId}?${params.toString()}`);
};

export const getExpense = async (expenseId) => {
  return get(`/api/budgets/expenses/${expenseId}`);
};

export const updateExpense = async (expenseId, data) => {
  return put(`/api/budgets/expenses/${expenseId}`, data);
};

export const deleteExpense = async (expenseId) => {
  return del(`/api/budgets/expenses/${expenseId}`);
};

export const getExpenseCategories = async () => {
  return get(`/api/budgets/expenses/categories/list`);
};

// ==================== Billable Rate Operations ====================

export const setBillableRate = async (orgId, rateData) => {
  return post(`/api/budgets/rates/?org_id=${orgId}`, rateData);
};

export const getOrgBillableRates = async (orgId) => {
  return get(`/api/budgets/rates/org/${orgId}`);
};

export const getEffectiveRate = async (orgId, { userId, projectId } = {}) => {
  const params = new URLSearchParams();
  params.append('org_id', orgId);
  if (userId) params.append('user_id', userId);
  if (projectId) params.append('project_id', projectId);
  return get(`/api/budgets/rates/effective?${params.toString()}`);
};

// ==================== Budget Lock Check ====================

export const checkBudgetLock = async (projectId) => {
  return get(`/api/budgets/check-lock/${projectId}`);
};

// ==================== Constants ====================

export const CURRENCIES = [
  { id: 'EGP', label: 'EGP - Egyptian Pound', symbol: 'E£' },
  { id: 'USD', label: 'USD - US Dollar', symbol: '$' },
];

export const EXPENSE_CATEGORIES = [
  { id: 'general', label: 'General', icon: 'receipt' },
  { id: 'travel', label: 'Travel', icon: 'plane' },
  { id: 'equipment', label: 'Equipment', icon: 'monitor' },
  { id: 'software', label: 'Software', icon: 'code' },
  { id: 'services', label: 'Services', icon: 'users' },
  { id: 'materials', label: 'Materials', icon: 'package' },
  { id: 'other', label: 'Other', icon: 'more-horizontal' },
];

export const BUDGET_STATUS = {
  active: { label: 'Active', color: 'bg-green-500', textColor: 'text-green-500' },
  warning: { label: 'Warning', color: 'bg-yellow-500', textColor: 'text-yellow-500' },
  exceeded: { label: 'Exceeded', color: 'bg-red-500', textColor: 'text-red-500' },
  locked: { label: 'Locked', color: 'bg-red-700', textColor: 'text-red-700' },
};

export const getCurrencySymbol = (currency) => {
  const found = CURRENCIES.find(c => c.id === currency);
  return found ? found.symbol : currency;
};

export const formatCurrency = (amount, currency = 'USD') => {
  const symbol = getCurrencySymbol(currency);
  return `${symbol}${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};
