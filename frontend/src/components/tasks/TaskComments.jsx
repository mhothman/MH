/**
 * TaskComments - Comments section for task detail
 */
import { useState } from "react";
import { Button } from "../ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { MessageSquare, Send } from "lucide-react";
import { MentionInput, RenderMentions } from "../MentionInput";
import { format, isValid, parseISO, formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

const safeFormatDistanceToNow = (dateStr) => {
  if (!dateStr) return null;
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
    return isValid(date) ? formatDistanceToNow(date, { addSuffix: true }) : null;
  } catch {
    return null;
  }
};

export function TaskComments({
  taskId,
  projectId,
  comments = [],
  members = [],
  currentUser,
  canComment = true,
  onAddComment,
  onRefresh,
}) {
  const [newComment, setNewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!newComment.trim()) return;
    
    setSubmitting(true);
    try {
      await onAddComment?.(newComment.trim());
      setNewComment("");
      onRefresh?.();
    } catch (error) {
      toast.error("Failed to add comment");
    } finally {
      setSubmitting(false);
    }
  };

  const getMemberById = (userId) => members.find(m => m.user_id === userId);

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium flex items-center gap-2">
        <MessageSquare className="w-4 h-4" />
        Comments
        {comments.length > 0 && (
          <span className="text-muted-foreground">({comments.length})</span>
        )}
      </h4>

      {/* Comments List */}
      <div className="space-y-4 max-h-[300px] overflow-y-auto">
        {comments.map((comment) => {
          const author = getMemberById(comment.author_id);
          return (
            <div key={comment.comment_id} className="flex gap-3">
              <Avatar className="w-8 h-8 shrink-0">
                <AvatarImage src={author?.picture} />
                <AvatarFallback className="text-xs">
                  {author?.name?.charAt(0) || '?'}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {author?.name || 'Unknown'}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {safeFormatDistanceToNow(comment.created_at)}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  <RenderMentions 
                    text={comment.content} 
                    members={members} 
                  />
                </div>
              </div>
            </div>
          );
        })}

        {comments.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No comments yet
          </p>
        )}
      </div>

      {/* Add Comment Form */}
      {canComment && (
        <div className="flex gap-2 pt-2 border-t">
          <Avatar className="w-8 h-8 shrink-0">
            <AvatarImage src={currentUser?.picture} />
            <AvatarFallback className="text-xs">
              {currentUser?.name?.charAt(0) || '?'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <MentionInput
              value={newComment}
              onChange={setNewComment}
              onSubmit={handleSubmit}
              placeholder="Add a comment... Use @ to mention"
              projectId={projectId}
              members={members}
              data-testid="comment-input"
            />
          </div>
          <Button
            size="icon"
            onClick={handleSubmit}
            disabled={submitting || !newComment.trim()}
            data-testid="comment-submit-btn"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
