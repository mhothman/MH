/**
 * DocumentDetailDialog - View document details with approval status, history, and actions
 * Shows document info, approval workflow status, attachments, versions, and allows status changes
 */
import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import { Input } from "../ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
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
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  User,
  Calendar,
  Tag,
  FolderOpen,
  History,
  Shield,
  Play,
  Send,
  ThumbsUp,
  ThumbsDown,
  Zap,
  Info,
  Paperclip,
  Upload,
  Download,
  Trash2,
  GitBranch,
  Eye,
  FileIcon,
  Image,
  Film,
  Music,
  Archive,
} from "lucide-react";
import { format } from "date-fns";
import {
  getDocument,
  changeDocumentStatus,
  checkDocumentApprovalRequired,
  getDocumentApprovalSummary,
  approveDocumentRequest,
  rejectDocumentRequest,
  getDocumentAttachments,
  uploadDocumentFile,
  deleteDocumentAttachment,
  getDocumentVersions,
  createDocumentVersion,
  getStatusColor,
  getStatusLabel,
  getTypeLabel,
} from "../../api/documents";

const DOCUMENT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "in_review", label: "In Review" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "approved", label: "Approved" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

export function DocumentDetailDialog({
  document: initialDocument,
  open,
  onOpenChange,
  onDocumentUpdated,
  canChangeStatus = false,
  canApprove = false,
}) {
  const [document, setDocument] = useState(initialDocument);
  const [approvalSummary, setApprovalSummary] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [changingStatus, setChangingStatus] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [statusComment, setStatusComment] = useState("");
  const [approvalCheck, setApprovalCheck] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [approvalActionDialog, setApprovalActionDialog] = useState({ open: false, action: null, approvalId: null });
  const [actionComment, setActionComment] = useState("");
  const [processingAction, setProcessingAction] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [versionSummary, setVersionSummary] = useState("");
  const [deleteAttachmentDialog, setDeleteAttachmentDialog] = useState({ open: false, attachment: null });
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (open && initialDocument?.document_id) {
      loadDocumentData();
    }
  }, [open, initialDocument?.document_id]);

  const loadDocumentData = async () => {
    if (!initialDocument?.document_id) return;
    
    setLoading(true);
    try {
      const [docData, summaryData, attachData, versionData] = await Promise.all([
        getDocument(initialDocument.document_id),
        getDocumentApprovalSummary(initialDocument.document_id).catch(() => null),
        getDocumentAttachments(initialDocument.document_id).catch(() => []),
        getDocumentVersions(initialDocument.document_id).catch(() => []),
      ]);
      setDocument(docData);
      setApprovalSummary(summaryData);
      setAttachments(attachData || []);
      setVersions(versionData || []);
    } catch (error) {
      console.error("Failed to load document data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    try {
      const attachment = await uploadDocumentFile(document.document_id, file);
      setAttachments([attachment, ...attachments]);
      toast.success("File uploaded successfully");
    } catch (error) {
      toast.error(error.message || "Failed to upload file");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDeleteAttachment = async () => {
    if (!deleteAttachmentDialog.attachment) return;
    
    try {
      await deleteDocumentAttachment(deleteAttachmentDialog.attachment.attachment_id);
      setAttachments(attachments.filter(a => a.attachment_id !== deleteAttachmentDialog.attachment.attachment_id));
      setDeleteAttachmentDialog({ open: false, attachment: null });
      toast.success("Attachment deleted");
    } catch (error) {
      toast.error(error.message || "Failed to delete attachment");
    }
  };

  const handleCreateVersion = async () => {
    setCreatingVersion(true);
    try {
      const version = await createDocumentVersion(document.document_id, versionSummary || null);
      setVersions([version, ...versions]);
      setVersionSummary("");
      toast.success(`Version ${version.version_number} created`);
    } catch (error) {
      toast.error(error.message || "Failed to create version");
    } finally {
      setCreatingVersion(false);
    }
  };

  const getFileIcon = (mimeType) => {
    if (mimeType?.startsWith('image/')) return <Image className="w-4 h-4" />;
    if (mimeType?.startsWith('video/')) return <Film className="w-4 h-4" />;
    if (mimeType?.startsWith('audio/')) return <Music className="w-4 h-4" />;
    if (mimeType?.includes('zip') || mimeType?.includes('archive')) return <Archive className="w-4 h-4" />;
    return <FileIcon className="w-4 h-4" />;
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleStatusSelect = async (status) => {
    if (!document || status === document.status) return;
    
    setTargetStatus(status);
    setStatusComment("");
    
    try {
      const check = await checkDocumentApprovalRequired(document.document_id, status);
      setApprovalCheck(check);
      setConfirmDialogOpen(true);
    } catch (error) {
      toast.error("Failed to check approval requirements");
    }
  };

  const handleConfirmStatusChange = async () => {
    if (!document || !targetStatus) return;
    
    setChangingStatus(true);
    try {
      const result = await changeDocumentStatus(document.document_id, targetStatus, statusComment || null);
      
      if (result.status === "approval_required") {
        toast.success("Approval request created");
        // Reload to get updated state
        await loadDocumentData();
      } else if (result.status === "changed") {
        toast.success(`Status changed to ${getStatusLabel(targetStatus)}`);
        if (result.document) {
          setDocument(result.document);
          onDocumentUpdated?.(result.document);
        }
      }
      
      setConfirmDialogOpen(false);
      setTargetStatus("");
      setStatusComment("");
      setApprovalCheck(null);
    } catch (error) {
      toast.error(error.message || "Failed to change status");
    } finally {
      setChangingStatus(false);
    }
  };

  const handleApprovalAction = async () => {
    const { action, approvalId } = approvalActionDialog;
    if (!approvalId || !action) return;
    
    setProcessingAction(true);
    try {
      if (action === "approve" || action === "force_approve") {
        await approveDocumentRequest(approvalId, actionComment || null, action === "force_approve");
        toast.success("Document approved successfully");
      } else {
        await rejectDocumentRequest(approvalId, actionComment || null, action === "force_reject");
        toast.success("Document rejected");
      }
      
      setApprovalActionDialog({ open: false, action: null, approvalId: null });
      setActionComment("");
      await loadDocumentData();
    } catch (error) {
      toast.error(error.message || "Failed to process approval action");
    } finally {
      setProcessingAction(false);
    }
  };

  const getAvailableTransitions = () => {
    if (!document) return [];
    
    const currentStatus = document.status;
    const transitions = {
      draft: ["in_review", "published"],
      in_review: ["draft", "approved", "rejected"],
      pending_approval: [], // Locked
      approved: ["published", "archived"],
      published: ["archived", "draft"],
      archived: ["draft"],
      rejected: ["draft"],
    };
    
    return transitions[currentStatus] || [];
  };

  if (!document) return null;

  const pendingApproval = approvalSummary?.pending_approval;
  const canAct = pendingApproval && (canApprove || approvalSummary?.can_approve);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-start gap-4">
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${getStatusColor(document.status)}20` }}
              >
                <FileText className="w-6 h-6" style={{ color: getStatusColor(document.status) }} />
              </div>
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-xl">{document.title}</DialogTitle>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline">{getTypeLabel(document.document_type)}</Badge>
                  <Badge
                    style={{
                      backgroundColor: `${getStatusColor(document.status)}20`,
                      color: getStatusColor(document.status),
                    }}
                  >
                    {getStatusLabel(document.status)}
                  </Badge>
                  {document.approval_locked && (
                    <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                      <Clock className="w-3 h-3 mr-1" />
                      Pending Approval
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </DialogHeader>

          {loading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : (
            <Tabs defaultValue="details" className="mt-4">
              <TabsList>
                <TabsTrigger value="details" data-testid="doc-details-tab">
                  <Info className="w-4 h-4 mr-2" />
                  Details
                </TabsTrigger>
                <TabsTrigger value="approval" data-testid="doc-approval-tab">
                  <Shield className="w-4 h-4 mr-2" />
                  Approval
                </TabsTrigger>
                <TabsTrigger value="attachments" data-testid="doc-attachments-tab">
                  <Paperclip className="w-4 h-4 mr-2" />
                  Files
                  {attachments.length > 0 && (
                    <Badge variant="secondary" className="ml-1 text-xs">{attachments.length}</Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="versions" data-testid="doc-versions-tab">
                  <GitBranch className="w-4 h-4 mr-2" />
                  Versions
                  {versions.length > 0 && (
                    <Badge variant="secondary" className="ml-1 text-xs">{versions.length}</Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="history" data-testid="doc-history-tab">
                  <History className="w-4 h-4 mr-2" />
                  History
                </TabsTrigger>
              </TabsList>

              {/* Details Tab */}
              <TabsContent value="details" className="space-y-4 mt-4">
                {document.description && (
                  <div>
                    <Label className="text-muted-foreground">Description</Label>
                    <p className="mt-1">{document.description}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground flex items-center gap-1">
                      <User className="w-4 h-4" />
                      Owner
                    </Label>
                    <p className="mt-1 font-medium">{document.owner_name || "Unknown"}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground flex items-center gap-1">
                      <FolderOpen className="w-4 h-4" />
                      Project
                    </Label>
                    <p className="mt-1 font-medium">{document.project_name || "None"}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Created
                    </Label>
                    <p className="mt-1">{document.created_at ? format(new Date(document.created_at), "PPP") : "-"}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Last Updated
                    </Label>
                    <p className="mt-1">{document.updated_at ? format(new Date(document.updated_at), "PPP") : "-"}</p>
                  </div>
                </div>

                {document.tags?.length > 0 && (
                  <div>
                    <Label className="text-muted-foreground flex items-center gap-1">
                      <Tag className="w-4 h-4" />
                      Tags
                    </Label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {document.tags.map((tag) => (
                        <Badge key={tag} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {document.last_approved_at && (
                  <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-900">
                    <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="font-medium">Last Approved</span>
                    </div>
                    <p className="text-sm text-green-600 dark:text-green-500 mt-1">
                      {format(new Date(document.last_approved_at), "PPP")}
                    </p>
                  </div>
                )}

                {/* Status Change Section */}
                {canChangeStatus && !document.approval_locked && (
                  <Card className="mt-4">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Play className="w-4 h-4" />
                        Change Status
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {getAvailableTransitions().map((status) => (
                          <Button
                            key={status}
                            variant="outline"
                            size="sm"
                            onClick={() => handleStatusSelect(status)}
                            className="flex items-center gap-2"
                          >
                            <ArrowRight className="w-3 h-3" />
                            {getStatusLabel(status)}
                          </Button>
                        ))}
                        {getAvailableTransitions().length === 0 && (
                          <p className="text-sm text-muted-foreground">
                            No status transitions available from current state.
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Approval Tab */}
              <TabsContent value="approval" className="space-y-4 mt-4">
                {/* Pending Approval Card */}
                {pendingApproval && (
                  <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center gap-2 text-amber-700 dark:text-amber-400">
                        <Clock className="w-4 h-4" />
                        Pending Approval
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Requested transition:</span>
                        <Badge variant="outline">{getStatusLabel(pendingApproval.original_status)}</Badge>
                        <ArrowRight className="w-4 h-4 text-muted-foreground" />
                        <Badge style={{ backgroundColor: `${getStatusColor(pendingApproval.target_status)}20`, color: getStatusColor(pendingApproval.target_status) }}>
                          {getStatusLabel(pendingApproval.target_status)}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Requested {pendingApproval.created_at ? format(new Date(pendingApproval.created_at), "PPp") : ""}
                      </p>

                      {canAct && (
                        <div className="flex gap-2 pt-2">
                          <Button
                            size="sm"
                            onClick={() => setApprovalActionDialog({ open: true, action: "approve", approvalId: pendingApproval.approval_id })}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <ThumbsUp className="w-4 h-4 mr-2" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => setApprovalActionDialog({ open: true, action: "reject", approvalId: pendingApproval.approval_id })}
                          >
                            <ThumbsDown className="w-4 h-4 mr-2" />
                            Reject
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setApprovalActionDialog({ open: true, action: "force_approve", approvalId: pendingApproval.approval_id })}
                          >
                            <Zap className="w-4 h-4 mr-2" />
                            Force Approve
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Applicable Workflow Info */}
                {approvalSummary?.applicable_workflow && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        Active Workflow
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <p className="font-medium">{approvalSummary.applicable_workflow.name}</p>
                        <Badge variant="outline" className="text-xs">
                          {approvalSummary.applicable_workflow.scope === "global" ? "Global" : "Selective"}
                        </Badge>
                        {approvalSummary.applicable_workflow.description && (
                          <p className="text-sm text-muted-foreground">{approvalSummary.applicable_workflow.description}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {!pendingApproval && !approvalSummary?.applicable_workflow && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No approval workflow is configured for this document.</p>
                    <p className="text-sm mt-1">Status changes will be applied directly.</p>
                  </div>
                )}
              </TabsContent>

              {/* Attachments Tab */}
              <TabsContent value="attachments" className="mt-4 space-y-4">
                {/* Upload Section */}
                {canChangeStatus && (
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-4">
                        <input
                          ref={fileInputRef}
                          type="file"
                          onChange={handleFileUpload}
                          className="hidden"
                          id="file-upload"
                        />
                        <Button
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploading}
                        >
                          {uploading ? (
                            <LoadingSpinner size="sm" className="mr-2" />
                          ) : (
                            <Upload className="w-4 h-4 mr-2" />
                          )}
                          {uploading ? "Uploading..." : "Upload File"}
                        </Button>
                        <p className="text-sm text-muted-foreground">
                          Max file size: 50MB
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Attachments List */}
                {attachments.length > 0 ? (
                  <div className="space-y-2">
                    {attachments.map((att) => (
                      <div
                        key={att.attachment_id}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent/50"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                            {getFileIcon(att.mime_type)}
                          </div>
                          <div>
                            <p className="font-medium">{att.filename}</p>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <span>{formatFileSize(att.file_size)}</span>
                              <span>•</span>
                              <span>{att.uploaded_by_name}</span>
                              <span>•</span>
                              <span>{att.uploaded_at ? format(new Date(att.uploaded_at), "MMM d, yyyy") : "-"}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            asChild
                          >
                            <a href={`${process.env.REACT_APP_BACKEND_URL}${att.file_url}`} target="_blank" rel="noopener noreferrer">
                              <Download className="w-4 h-4" />
                            </a>
                          </Button>
                          {canChangeStatus && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive"
                              onClick={() => setDeleteAttachmentDialog({ open: true, attachment: att })}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Paperclip className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No attachments yet.</p>
                    {canChangeStatus && (
                      <p className="text-sm mt-1">Upload files to attach to this document.</p>
                    )}
                  </div>
                )}
              </TabsContent>

              {/* Versions Tab */}
              <TabsContent value="versions" className="mt-4 space-y-4">
                {/* Create Version */}
                {canChangeStatus && (
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-end gap-3">
                        <div className="flex-1">
                          <Label htmlFor="version-summary">Change Summary (optional)</Label>
                          <Input
                            id="version-summary"
                            placeholder="Describe changes in this version..."
                            value={versionSummary}
                            onChange={(e) => setVersionSummary(e.target.value)}
                            className="mt-1"
                          />
                        </div>
                        <Button
                          onClick={handleCreateVersion}
                          disabled={creatingVersion}
                        >
                          {creatingVersion ? (
                            <LoadingSpinner size="sm" className="mr-2" />
                          ) : (
                            <GitBranch className="w-4 h-4 mr-2" />
                          )}
                          Create Version
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Versions List */}
                {versions.length > 0 ? (
                  <div className="space-y-2">
                    {versions.map((ver, idx) => (
                      <div
                        key={ver.version_id}
                        className={`flex items-start gap-3 p-3 border rounded-lg ${idx === 0 ? 'border-primary bg-primary/5' : ''}`}
                      >
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${idx === 0 ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                          <span className="text-sm font-medium">{ver.version_number}</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{ver.title}</p>
                            {idx === 0 && <Badge variant="secondary">Current</Badge>}
                            <Badge
                              variant="outline"
                              style={{ borderColor: getStatusColor(ver.status), color: getStatusColor(ver.status) }}
                            >
                              {getStatusLabel(ver.status)}
                            </Badge>
                          </div>
                          {ver.change_summary && (
                            <p className="text-sm text-muted-foreground mt-1">{ver.change_summary}</p>
                          )}
                          <p className="text-xs text-muted-foreground mt-2">
                            {ver.changed_by_name} • {ver.created_at ? format(new Date(ver.created_at), "PPp") : "-"}
                          </p>
                        </div>
                        <Button variant="ghost" size="icon">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No version history yet.</p>
                    {canChangeStatus && (
                      <p className="text-sm mt-1">Create a version snapshot to track changes.</p>
                    )}
                  </div>
                )}
              </TabsContent>

              {/* History Tab */}
              <TabsContent value="history" className="mt-4">
                {approvalSummary?.approval_history?.length > 0 ? (
                  <div className="space-y-4">
                    {approvalSummary.approval_history.map((record, idx) => (
                      <div
                        key={record.approval_id || idx}
                        className="flex items-start gap-3 p-3 border rounded-lg"
                      >
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                            record.status === "approved"
                              ? "bg-green-100 text-green-600"
                              : record.status === "rejected"
                              ? "bg-red-100 text-red-600"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {record.status === "approved" ? (
                            <CheckCircle2 className="w-4 h-4" />
                          ) : record.status === "rejected" ? (
                            <XCircle className="w-4 h-4" />
                          ) : (
                            <Clock className="w-4 h-4" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{getStatusLabel(record.original_status)}</Badge>
                            <ArrowRight className="w-4 h-4 text-muted-foreground" />
                            <Badge variant="outline">{getStatusLabel(record.target_status)}</Badge>
                            <Badge
                              variant="secondary"
                              className={
                                record.status === "approved"
                                  ? "bg-green-100 text-green-700"
                                  : record.status === "rejected"
                                  ? "bg-red-100 text-red-700"
                                  : ""
                              }
                            >
                              {record.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {record.resolved_at
                              ? format(new Date(record.resolved_at), "PPp")
                              : record.created_at
                              ? format(new Date(record.created_at), "PPp")
                              : "-"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No approval history yet.</p>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>

      {/* Status Change Confirmation Dialog */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {approvalCheck?.requires_approval ? "Approval Required" : "Confirm Status Change"}
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <div className="flex items-center gap-2 justify-center py-2">
                <Badge variant="outline">{getStatusLabel(document?.status)}</Badge>
                <ArrowRight className="w-4 h-4" />
                <Badge style={{ backgroundColor: `${getStatusColor(targetStatus)}20`, color: getStatusColor(targetStatus) }}>
                  {getStatusLabel(targetStatus)}
                </Badge>
              </div>
              {approvalCheck?.requires_approval ? (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-900">
                  <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="font-medium">This transition requires approval</span>
                  </div>
                  {approvalCheck.workflow && (
                    <p className="text-sm text-amber-600 dark:text-amber-500 mt-1">
                      Workflow: {approvalCheck.workflow.name}
                    </p>
                  )}
                </div>
              ) : (
                <p>The status will be changed immediately.</p>
              )}
              <div className="pt-2">
                <Label>Comment (optional)</Label>
                <Textarea
                  placeholder="Add a comment about this status change..."
                  value={statusComment}
                  onChange={(e) => setStatusComment(e.target.value)}
                  rows={2}
                  className="mt-1"
                />
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setTargetStatus(""); setApprovalCheck(null); }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmStatusChange} disabled={changingStatus}>
              {changingStatus ? (
                <LoadingSpinner size="sm" />
              ) : approvalCheck?.requires_approval ? (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Request Approval
                </>
              ) : (
                "Change Status"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Approval Action Dialog */}
      <AlertDialog
        open={approvalActionDialog.open}
        onOpenChange={(open) => !open && setApprovalActionDialog({ open: false, action: null, approvalId: null })}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {approvalActionDialog.action === "approve"
                ? "Approve Document"
                : approvalActionDialog.action === "force_approve"
                ? "Force Approve Document"
                : approvalActionDialog.action === "force_reject"
                ? "Force Reject Document"
                : "Reject Document"}
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              {approvalActionDialog.action?.includes("force") && (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-900">
                  <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                    <Zap className="w-4 h-4" />
                    <span className="font-medium">Admin Override</span>
                  </div>
                  <p className="text-sm text-amber-600 dark:text-amber-500 mt-1">
                    This action will bypass normal approval requirements.
                  </p>
                </div>
              )}
              <div>
                <Label>{approvalActionDialog.action?.includes("reject") ? "Reason (recommended)" : "Comment (optional)"}</Label>
                <Textarea
                  placeholder={
                    approvalActionDialog.action?.includes("reject")
                      ? "Explain why this is being rejected..."
                      : "Add a comment..."
                  }
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  rows={3}
                  className="mt-1"
                />
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setActionComment("")}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleApprovalAction}
              disabled={processingAction}
              className={
                approvalActionDialog.action?.includes("reject")
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : "bg-green-600 hover:bg-green-700"
              }
            >
              {processingAction ? (
                <LoadingSpinner size="sm" />
              ) : approvalActionDialog.action?.includes("reject") ? (
                <>
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Approve
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Attachment Confirmation */}
      <AlertDialog
        open={deleteAttachmentDialog.open}
        onOpenChange={(open) => !open && setDeleteAttachmentDialog({ open: false, attachment: null })}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Attachment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteAttachmentDialog.attachment?.filename}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteAttachment}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default DocumentDetailDialog;
