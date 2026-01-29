/**
 * DocumentsPage - Main page for viewing and managing documents
 * Shows documents list with status, approval info, and management actions
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { hasPermission, Permission } from "../api";
import { useAppData } from "../context/AppDataContext";
import {
  getDocuments,
  createDocument,
  updateDocument,
  deleteDocument,
  changeDocumentStatus,
  checkDocumentApprovalRequired,
  getStatusColor,
  getStatusLabel,
  getTypeLabel,
  DocumentStatus,
  DocumentType,
} from "../api/documents";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  Plus,
  FileText,
  Search,
  LayoutGrid,
  List,
  MoreHorizontal,
  Pencil,
  Trash2,
  Eye,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  FolderOpen,
  User,
  Filter,
} from "lucide-react";
import { format } from "date-fns";
import { DocumentDetailDialog } from "../components/documents/DocumentDetailDialog";

const DOCUMENT_TYPES = [
  { value: "policy", label: "Policy" },
  { value: "procedure", label: "Procedure" },
  { value: "specification", label: "Specification" },
  { value: "contract", label: "Contract" },
  { value: "report", label: "Report" },
  { value: "proposal", label: "Proposal" },
  { value: "template", label: "Template" },
  { value: "other", label: "Other" },
];

const DOCUMENT_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "in_review", label: "In Review" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "approved", label: "Approved" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
  { value: "rejected", label: "Rejected" },
];

export default function DocumentsPage() {
  const navigate = useNavigate();
  const {
    projects: globalProjects,
    organizations,
    permissions: globalPermissions,
    currentOrg,
    currentOrgId,
    loadProjects,
  } = useAppData();
  
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState("list");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editingDocument, setEditingDocument] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [newDocument, setNewDocument] = useState({
    title: "",
    description: "",
    document_type: "other",
    project_id: "none",
    tags: "",
  });

  // Use global data
  const projects = globalProjects.filter((p) => p.org_id === currentOrgId);
  const permissions = globalPermissions;

  const canDo = (permission) => hasPermission(permissions, permission);

  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        // Load projects from global context
        await loadProjects();
        
        // Load documents (page-specific data)
        if (currentOrgId) {
          const docsData = await getDocuments(currentOrgId);
          if (!isMounted) return;
          setDocuments(docsData);
        }
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to load documents:", error);
        toast.error("Failed to load documents");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, [currentOrgId, loadProjects]);

  const handleCreateDocument = async () => {
    if (!newDocument.title.trim()) {
      toast.error("Please enter a document title");
      return;
    }

    if (!currentOrgId) {
      toast.error("No organization selected");
      return;
    }

    setCreating(true);
    try {
      const docData = {
        title: newDocument.title,
        description: newDocument.description || null,
        document_type: newDocument.document_type,
        tags: newDocument.tags ? newDocument.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      };

      if (newDocument.project_id && newDocument.project_id !== "none") {
        docData.project_id = newDocument.project_id;
      }

      const created = await createDocument(currentOrgId, docData);
      setDocuments([created, ...documents]);
      setDialogOpen(false);
      setNewDocument({ title: "", description: "", document_type: "other", project_id: "none", tags: "" });
      toast.success("Document created successfully");
      
      // Open detail view for the new document
      setSelectedDocument(created);
      setDetailDialogOpen(true);
    } catch (error) {
      toast.error(error.message || "Failed to create document");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateDocument = async () => {
    if (!newDocument.title.trim()) {
      toast.error("Please enter a document title");
      return;
    }

    setCreating(true);
    try {
      const docData = {
        title: newDocument.title,
        description: newDocument.description || null,
        document_type: newDocument.document_type,
        tags: newDocument.tags ? newDocument.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      };

      if (newDocument.project_id && newDocument.project_id !== "none") {
        docData.project_id = newDocument.project_id;
      } else {
        docData.project_id = null;
      }

      const updated = await updateDocument(editingDocument.document_id, docData);
      setDocuments(documents.map((d) => (d.document_id === editingDocument.document_id ? { ...d, ...updated } : d)));
      setDialogOpen(false);
      setEditingDocument(null);
      setNewDocument({ title: "", description: "", document_type: "other", project_id: "none", tags: "" });
      toast.success("Document updated successfully");
    } catch (error) {
      toast.error(error.message || "Failed to update document");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!documentToDelete) return;

    try {
      await deleteDocument(documentToDelete.document_id);
      setDocuments(documents.filter((d) => d.document_id !== documentToDelete.document_id));
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
      toast.success("Document deleted successfully");
    } catch (error) {
      toast.error(error.message || "Failed to delete document");
    }
  };

  const handleOpenEditDialog = (doc, e) => {
    e?.stopPropagation();
    setEditingDocument(doc);
    setNewDocument({
      title: doc.title || "",
      description: doc.description || "",
      document_type: doc.document_type || "other",
      project_id: doc.project_id || "none",
      tags: doc.tags?.join(", ") || "",
    });
    setDialogOpen(true);
  };

  const handleOpenDetailDialog = (doc) => {
    setSelectedDocument(doc);
    setDetailDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingDocument(null);
    setNewDocument({ title: "", description: "", document_type: "other", project_id: "none", tags: "" });
  };

  const handleDocumentUpdated = (updatedDoc) => {
    setDocuments(documents.map((d) => (d.document_id === updatedDoc.document_id ? updatedDoc : d)));
    setSelectedDocument(updatedDoc);
  };

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    const matchesType = typeFilter === "all" || doc.document_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const getStatusIcon = (status) => {
    switch (status) {
      case "draft":
        return <FileText className="w-4 h-4" />;
      case "in_review":
        return <Eye className="w-4 h-4" />;
      case "pending_approval":
        return <Clock className="w-4 h-4" />;
      case "approved":
        return <CheckCircle2 className="w-4 h-4" />;
      case "published":
        return <CheckCircle2 className="w-4 h-4" />;
      case "rejected":
        return <XCircle className="w-4 h-4" />;
      case "archived":
        return <FolderOpen className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="documents-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground mt-1">Manage and track document approvals</p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={(open) => (open ? setDialogOpen(true) : handleCloseDialog())}>
          {canDo(Permission.DOCUMENT_CREATE) && (
            <DialogTrigger asChild>
              <Button data-testid="create-document-btn">
                <Plus className="w-4 h-4 mr-2" />
                New Document
              </Button>
            </DialogTrigger>
          )}
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingDocument ? "Edit Document" : "Create New Document"}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="doc-title">Title</Label>
                <Input
                  id="doc-title"
                  placeholder="Enter document title"
                  value={newDocument.title}
                  onChange={(e) => setNewDocument({ ...newDocument, title: e.target.value })}
                  data-testid="document-title-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="doc-description">Description</Label>
                <Textarea
                  id="doc-description"
                  placeholder="Enter document description (optional)"
                  value={newDocument.description}
                  onChange={(e) => setNewDocument({ ...newDocument, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Document Type</Label>
                  <Select
                    value={newDocument.document_type}
                    onValueChange={(value) => setNewDocument({ ...newDocument, document_type: value })}
                  >
                    <SelectTrigger data-testid="document-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DOCUMENT_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Project (Optional)</Label>
                  <Select
                    value={newDocument.project_id}
                    onValueChange={(value) => setNewDocument({ ...newDocument, project_id: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select project" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No project</SelectItem>
                      {projects.map((project) => (
                        <SelectItem key={project.project_id} value={project.project_id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="doc-tags">Tags (comma separated)</Label>
                <Input
                  id="doc-tags"
                  placeholder="e.g., important, Q1, policy"
                  value={newDocument.tags}
                  onChange={(e) => setNewDocument({ ...newDocument, tags: e.target.value })}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={handleCloseDialog}>
                  Cancel
                </Button>
                <Button
                  onClick={editingDocument ? handleUpdateDocument : handleCreateDocument}
                  disabled={creating}
                  data-testid="submit-document-btn"
                >
                  {creating ? <LoadingSpinner size="sm" /> : editingDocument ? "Update" : "Create"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            data-testid="search-documents-input"
          />
        </div>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[150px]" data-testid="type-filter">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {DOCUMENT_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="status-filter">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {DOCUMENT_STATUSES.map((status) => (
              <SelectItem key={status.value} value={status.value}>
                {status.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex border border-border rounded-md">
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setViewMode("list")}
            data-testid="list-view-btn"
          >
            <List className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setViewMode("grid")}
            data-testid="grid-view-btn"
          >
            <LayoutGrid className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Documents List/Grid */}
      {filteredDocuments.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <FileText className="w-12 h-12 mx-auto text-muted-foreground opacity-50" />
              <h3 className="font-medium text-lg mt-4">No documents found</h3>
              <p className="text-muted-foreground mt-1">
                {searchQuery || statusFilter !== "all" || typeFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create your first document to get started"}
              </p>
              {!searchQuery && statusFilter === "all" && typeFilter === "all" && canDo(Permission.DOCUMENT_CREATE) && (
                <Button className="mt-4" onClick={() => setDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Document
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : viewMode === "list" ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40%]">Document</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.map((doc) => (
                  <TableRow
                    key={doc.document_id}
                    className="cursor-pointer"
                    onClick={() => handleOpenDetailDialog(doc)}
                    data-testid={`document-row-${doc.document_id}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div
                          className="w-10 h-10 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${getStatusColor(doc.status)}20` }}
                        >
                          <FileText className="w-5 h-5" style={{ color: getStatusColor(doc.status) }} />
                        </div>
                        <div>
                          <p className="font-medium">{doc.title}</p>
                          {doc.project_name && (
                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                              <FolderOpen className="w-3 h-3" />
                              {doc.project_name}
                            </p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{getTypeLabel(doc.document_type)}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className="flex items-center gap-1 w-fit"
                        style={{
                          backgroundColor: `${getStatusColor(doc.status)}20`,
                          color: getStatusColor(doc.status),
                        }}
                      >
                        {getStatusIcon(doc.status)}
                        {getStatusLabel(doc.status)}
                      </Badge>
                      {doc.approval_locked && (
                        <span className="text-xs text-amber-600 flex items-center gap-1 mt-1">
                          <Clock className="w-3 h-3" />
                          Awaiting approval
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">{doc.owner_name || "Unknown"}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {doc.updated_at ? format(new Date(doc.updated_at), "MMM d, yyyy") : "-"}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                          <DropdownMenuItem onClick={() => handleOpenDetailDialog(doc)}>
                            <Eye className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {canDo(Permission.DOCUMENT_EDIT) && (
                            <DropdownMenuItem onClick={(e) => handleOpenEditDialog(doc, e)}>
                              <Pencil className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                          )}
                          {canDo(Permission.DOCUMENT_DELETE) && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDocumentToDelete(doc);
                                  setDeleteDialogOpen(true);
                                }}
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocuments.map((doc) => (
            <Card
              key={doc.document_id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleOpenDetailDialog(doc)}
              data-testid={`document-card-${doc.document_id}`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${getStatusColor(doc.status)}20` }}
                  >
                    <FileText className="w-6 h-6" style={{ color: getStatusColor(doc.status) }} />
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                      {canDo(Permission.DOCUMENT_EDIT) && (
                        <DropdownMenuItem onClick={(e) => handleOpenEditDialog(doc, e)}>
                          <Pencil className="w-4 h-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                      )}
                      {canDo(Permission.DOCUMENT_DELETE) && (
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDocumentToDelete(doc);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <h3 className="font-semibold truncate">{doc.title}</h3>
                {doc.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">{doc.description}</p>
                )}

                <div className="flex items-center gap-2 mt-3">
                  <Badge variant="outline">{getTypeLabel(doc.document_type)}</Badge>
                  <Badge
                    variant="secondary"
                    style={{
                      backgroundColor: `${getStatusColor(doc.status)}20`,
                      color: getStatusColor(doc.status),
                    }}
                  >
                    {getStatusLabel(doc.status)}
                  </Badge>
                </div>

                {doc.approval_locked && (
                  <div className="flex items-center gap-1 text-xs text-amber-600 mt-2">
                    <Clock className="w-3 h-3" />
                    Awaiting approval
                  </div>
                )}

                <div className="flex items-center justify-between mt-4 pt-3 border-t text-sm text-muted-foreground">
                  <span>{doc.owner_name || "Unknown"}</span>
                  <span>{doc.updated_at ? format(new Date(doc.updated_at), "MMM d") : "-"}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Document Detail Dialog */}
      <DocumentDetailDialog
        document={selectedDocument}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        onDocumentUpdated={handleDocumentUpdated}
        canChangeStatus={canDo(Permission.DOCUMENT_CHANGE_STATUS)}
        canApprove={canDo(Permission.DOCUMENT_APPROVE)}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Document</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{documentToDelete?.title}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDocumentToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteDocument}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
