import { useState, useEffect, useRef } from 'react';
import { getAttachments, uploadAttachment, downloadAttachment, deleteAttachment } from '../api/tasks';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { LoadingSpinner } from './ui/loading-spinner';
import { toast } from 'sonner';
import { Paperclip, Upload, Download, Trash2, File, Image, FileText, FileArchive } from 'lucide-react';

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getFileIcon = (contentType) => {
  if (contentType?.startsWith('image/')) return Image;
  if (contentType?.includes('pdf') || contentType?.includes('document')) return FileText;
  if (contentType?.includes('zip') || contentType?.includes('archive')) return FileArchive;
  return File;
};

export const FileAttachments = ({ taskId }) => {
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadAttachments();
  }, [taskId]);

  const loadAttachments = async () => {
    try {
      const data = await getAttachments(taskId);
      setAttachments(data);
    } catch (error) {
      console.error('Failed to load attachments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large (max 10MB)');
      return;
    }

    setUploading(true);
    try {
      const attachment = await uploadAttachment(taskId, file);
      if (attachment && attachment.attachment_id) {
        setAttachments(prev => [...prev, attachment]);
        toast.success('File uploaded successfully');
      }
    } catch (error) {
      console.error('Upload error:', error);
      // Only show error if it's a genuine failure
      if (error.message && !error.message.includes('Request failed')) {
        toast.error(error.message);
      } else {
        // Reload attachments to check if upload actually succeeded
        try {
          const data = await getAttachments(taskId);
          setAttachments(data);
          // Check if file count increased
          if (data.length > attachments.length) {
            toast.success('File uploaded successfully');
          } else {
            toast.error('Failed to upload file');
          }
        } catch {
          toast.error('Failed to upload file');
        }
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDownload = async (attachment) => {
    try {
      await downloadAttachment(taskId, attachment.attachment_id, attachment.filename);
      toast.success('Download started');
    } catch (error) {
      toast.error('Failed to download file');
    }
  };

  const handleDelete = async (attachmentId) => {
    try {
      await deleteAttachment(taskId, attachmentId);
      setAttachments(attachments.filter(a => a.attachment_id !== attachmentId));
      toast.success('Attachment deleted');
    } catch (error) {
      toast.error('Failed to delete attachment');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <LoadingSpinner size="sm" />
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="file-attachments">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium flex items-center gap-2">
          <Paperclip className="w-4 h-4" />
          Attachments
          {attachments.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {attachments.length}
            </Badge>
          )}
        </h4>
        
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleUpload}
          className="hidden"
          data-testid="file-input"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          data-testid="upload-btn"
        >
          {uploading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <>
              <Upload className="w-3 h-3 mr-1" />
              Upload
            </>
          )}
        </Button>
      </div>

      {attachments.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4">
          No attachments yet
        </p>
      ) : (
        <div className="space-y-2">
          {attachments.map((attachment) => {
            const FileIcon = getFileIcon(attachment.content_type);
            return (
              <div
                key={attachment.attachment_id}
                className="flex items-center gap-3 p-2 rounded-md border border-border hover:bg-accent/50 group"
                data-testid={`attachment-${attachment.attachment_id}`}
              >
                <div className="p-2 bg-muted rounded">
                  <FileIcon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{attachment.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(attachment.size)}
                  </p>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={() => handleDownload(attachment)}
                    data-testid={`download-${attachment.attachment_id}`}
                  >
                    <Download className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7 text-destructive hover:text-destructive"
                    onClick={() => handleDelete(attachment.attachment_id)}
                    data-testid={`delete-${attachment.attachment_id}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default FileAttachments;
