/**
 * TeamSettings - Team member management component
 */
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
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
  Plus,
  Mail,
  MoreHorizontal,
  UserX,
  KeyRound,
  Ban,
  CheckCircle,
  Trash2,
  RefreshCw,
  Clock,
  UserCog,
} from "lucide-react";

const getInitials = (name) => {
  if (!name) return "U";
  return name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
};

export function TeamSettings({
  members = [],
  pendingInvitations = [],
  customRoles = [],
  myRole,
  canInvite,
  canRemove,
  canChangeRole,
  canSuspend,
  onInvite,
  onRemove,
  onSuspend,
  onUnsuspend,
  onResetPassword,
  onChangeRole,
  onResendInvitation,
  onCancelInvitation,
}) {
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("team_member");
  const [inviting, setInviting] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, type: null, member: null });
  const [roleDialog, setRoleDialog] = useState({ open: false, member: null });
  const [newRole, setNewRole] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const handleInvite = async () => {
    if (!inviteEmail.trim()) {
      toast.error("Please enter an email address");
      return;
    }

    setInviting(true);
    try {
      await onInvite?.({ email: inviteEmail, role: inviteRole });
      toast.success("Invitation sent successfully");
      setInviteDialogOpen(false);
      setInviteEmail("");
    } catch (error) {
      toast.error(error.message || "Failed to send invitation");
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = async () => {
    if (!confirmDialog.member) return;
    setActionLoading(true);
    try {
      await onRemove?.(confirmDialog.member.user_id);
      toast.success("Member removed successfully");
    } catch (error) {
      toast.error(error.message || "Failed to remove member");
    } finally {
      setActionLoading(false);
      setConfirmDialog({ open: false, type: null, member: null });
    }
  };

  const handleSuspendMember = async (member) => {
    setActionLoading(true);
    try {
      if (member.suspended) {
        await onUnsuspend?.(member.user_id);
        toast.success("Member unsuspended successfully");
      } else {
        await onSuspend?.(member.user_id);
        toast.success("Member suspended successfully");
      }
    } catch (error) {
      toast.error(error.message || "Failed to update member status");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetPassword = async (member) => {
    setActionLoading(true);
    try {
      await onResetPassword?.(member.user_id);
      toast.success("Password reset email sent");
    } catch (error) {
      toast.error(error.message || "Failed to send reset email");
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangeRole = async () => {
    if (!roleDialog.member || !newRole) return;
    setActionLoading(true);
    try {
      if (newRole.startsWith("custom:")) {
        const customRoleId = newRole.replace("custom:", "");
        await onChangeRole?.(roleDialog.member.user_id, null, customRoleId);
      } else {
        await onChangeRole?.(roleDialog.member.user_id, newRole);
      }
      toast.success("Role updated successfully");
      setRoleDialog({ open: false, member: null });
      setNewRole("");
    } catch (error) {
      toast.error(error.message || "Failed to change role");
    } finally {
      setActionLoading(false);
    }
  };

  const getRoleBadge = (member) => {
    if (member.custom_role_name) {
      const customRole = customRoles.find(r => r.role_id === member.custom_role_id);
      const color = customRole?.color || "#6366f1";
      return (
        <Badge style={{ backgroundColor: color + "20", color: color, borderColor: color }}>
          {member.custom_role_name}
        </Badge>
      );
    }
    
    const role = member.org_role;
    const variants = {
      super_admin: "destructive",
      org_admin: "default",
      project_manager: "secondary",
      team_member: "outline",
      viewer: "secondary",
    };
    const labels = {
      super_admin: "Super Admin",
      org_admin: "Admin",
      project_manager: "PM",
      team_member: "Member",
      viewer: "Viewer",
    };
    return <Badge variant={variants[role] || "outline"}>{labels[role] || role}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Team Members Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Team Members</CardTitle>
            <CardDescription>Manage your organization&apos;s team</CardDescription>
          </div>
          {canInvite && (
            <Button onClick={() => setInviteDialogOpen(true)} data-testid="invite-member-btn">
              <Plus className="w-4 h-4 mr-2" />
              Invite Member
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {members.map((member) => (
              <div key={member.user_id} className="flex items-center justify-between py-3 border-b last:border-0">
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarImage src={member.picture} />
                    <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{member.name}</span>
                      {getRoleBadge(member)}
                      {member.suspended && <Badge variant="destructive">Suspended</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground">{member.email}</p>
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {canChangeRole && (
                      <DropdownMenuItem onClick={() => {
                        setRoleDialog({ open: true, member });
                        setNewRole(member.custom_role_id ? `custom:${member.custom_role_id}` : member.org_role);
                      }}>
                        <UserCog className="w-4 h-4 mr-2" />
                        Change Role
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => handleResetPassword(member)}>
                      <KeyRound className="w-4 h-4 mr-2" />
                      Reset Password
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {canSuspend && (
                      <DropdownMenuItem onClick={() => handleSuspendMember(member)}>
                        {member.suspended ? (
                          <>
                            <CheckCircle className="w-4 h-4 mr-2" />
                            Unsuspend
                          </>
                        ) : (
                          <>
                            <Ban className="w-4 h-4 mr-2" />
                            Suspend
                          </>
                        )}
                      </DropdownMenuItem>
                    )}
                    {canRemove && (
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setConfirmDialog({ open: true, type: "remove", member })}
                      >
                        <UserX className="w-4 h-4 mr-2" />
                        Remove
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
            {members.length === 0 && (
              <p className="text-center text-muted-foreground py-4">No members yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pending Invitations Card */}
      {pendingInvitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Pending Invitations
            </CardTitle>
            <CardDescription>Invitations waiting to be accepted</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingInvitations.map((invite) => (
                <div key={invite.invite_id || invite.email} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                      <Mail className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{invite.email}</p>
                      <p className="text-xs text-muted-foreground">
                        Invited as {invite.role?.replace("_", " ")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => onResendInvitation?.(invite.email)}>
                      <RefreshCw className="w-4 h-4 mr-1" />
                      Resend
                    </Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => onCancelInvitation?.(invite.invite_id)}>
                      <Trash2 className="w-4 h-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invite Member Dialog */}
      <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              Send an invitation email to add a new member to your organization.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email Address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                data-testid="invite-email-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger data-testid="invite-role-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="org_admin">Admin</SelectItem>
                  <SelectItem value="project_manager">Project Manager</SelectItem>
                  <SelectItem value="finance">Finance</SelectItem>
                  <SelectItem value="team_member">Team Member</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleInvite} disabled={inviting} data-testid="send-invite-btn">
                {inviting ? <LoadingSpinner size="sm" className="mr-2" /> : <Mail className="w-4 h-4 mr-2" />}
                Send Invitation
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Role Dialog */}
      <Dialog open={roleDialog.open} onOpenChange={(open) => setRoleDialog({ open, member: roleDialog.member })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Member Role</DialogTitle>
            <DialogDescription>
              Update the role for {roleDialog.member?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <Select value={newRole} onValueChange={setNewRole}>
              <SelectTrigger>
                <SelectValue placeholder="Select new role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="super_admin">Super Admin</SelectItem>
                <SelectItem value="org_admin">Org Admin</SelectItem>
                <SelectItem value="project_manager">Project Manager</SelectItem>
                <SelectItem value="team_member">Team Member</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
                {customRoles.length > 0 && (
                  <>
                    <SelectItem value="__custom_roles_header__" disabled className="font-semibold text-xs">
                      ── Custom Roles ──
                    </SelectItem>
                    {customRoles.map((role) => (
                      <SelectItem key={role.role_id} value={`custom:${role.role_id}`}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </>
                )}
              </SelectContent>
            </Select>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRoleDialog({ open: false, member: null })}>Cancel</Button>
              <Button onClick={handleChangeRole} disabled={actionLoading}>
                {actionLoading ? <LoadingSpinner size="sm" /> : "Save"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Remove Confirmation Dialog */}
      <AlertDialog open={confirmDialog.open} onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Team Member?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove {confirmDialog.member?.name} from the organization?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemoveMember} disabled={actionLoading}>
              {actionLoading ? <LoadingSpinner size="sm" /> : "Remove"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
