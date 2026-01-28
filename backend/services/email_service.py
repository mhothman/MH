"""Email service for transactional emails"""
import resend
import logging
from typing import Optional, Dict, List
import asyncio

from core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending transactional emails"""
    
    def __init__(self):
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
            logger.info("Email service initialized with Resend")
        else:
            logger.warning("Email service: No API key configured")
    
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Send an email using Resend.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML body content
            from_email: Sender email (defaults to settings.SENDER_EMAIL)
            
        Returns:
            Response dict with email ID on success, None on failure
        """
        if not settings.RESEND_API_KEY:
            logger.warning("Email not sent - no API key configured")
            return None
        
        try:
            params = {
                "from": from_email or settings.SENDER_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html_content
            }
            
            response = await asyncio.to_thread(resend.Emails.send, params)
            logger.info(f"Email sent to {to}, ID: {response.get('id', 'N/A')}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return None
    
    async def send_password_reset(self, to: str, reset_link: str, user_name: str) -> Optional[Dict]:
        """Send password reset email"""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a1a;">Password Reset Request</h2>
            <p style="color: #4a4a4a;">Hi {user_name},</p>
            <p style="color: #4a4a4a;">You requested to reset your password for your ProFlow account.</p>
            <p style="margin: 24px 0;">
                <a href="{reset_link}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #6a6a6a; font-size: 14px;">Or copy this link: {reset_link}</p>
            <p style="color: #6a6a6a; font-size: 14px;">This link expires in 24 hours.</p>
            <p style="color: #6a6a6a; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
        </div>
        """
        return await self.send(to, "Password Reset - ProFlow", html)
    
    async def send_invitation(
        self,
        to: str,
        org_name: str,
        inviter_name: str,
        role: str,
        signup_link: str
    ) -> Optional[Dict]:
        """Send organization invitation email"""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a1a;">You've been invited to join {org_name} on ProFlow</h2>
            <p style="color: #4a4a4a;">{inviter_name} has invited you to join their organization as a <strong>{role}</strong>.</p>
            <p style="margin: 24px 0;">
                <a href="{signup_link}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    Accept Invitation & Sign Up
                </a>
            </p>
            <p style="color: #6a6a6a; font-size: 14px;">Or copy this link: {signup_link}</p>
            <p style="color: #6a6a6a; font-size: 14px;">This invitation expires in 7 days.</p>
        </div>
        """
        return await self.send(to, f"Invitation to join {org_name} - ProFlow", html)
    
    async def send_task_assigned(
        self,
        to: str,
        user_name: str,
        task_title: str,
        project_name: str,
        assigner_name: str,
        task_link: str
    ) -> Optional[Dict]:
        """Send task assignment notification email"""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a1a;">New Task Assigned</h2>
            <p style="color: #4a4a4a;">Hi {user_name},</p>
            <p style="color: #4a4a4a;">{assigner_name} has assigned you a task in <strong>{project_name}</strong>:</p>
            <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <strong>{task_title}</strong>
            </div>
            <p style="margin: 24px 0;">
                <a href="{task_link}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Task
                </a>
            </p>
        </div>
        """
        return await self.send(to, f"Task Assigned: {task_title} - ProFlow", html)
    
    async def send_scheduled_report(
        self,
        to: str,
        user_name: str,
        report_name: str,
        report_link: str,
        attachment: Optional[bytes] = None
    ) -> Optional[Dict]:
        """Send scheduled report email"""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a1a;">Your Scheduled Report is Ready</h2>
            <p style="color: #4a4a4a;">Hi {user_name},</p>
            <p style="color: #4a4a4a;">Your scheduled report <strong>{report_name}</strong> is now available.</p>
            <p style="margin: 24px 0;">
                <a href="{report_link}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Report
                </a>
            </p>
        </div>
        """
        return await self.send(to, f"Report Ready: {report_name} - ProFlow", html)
    
    # ==================== Approval Workflow Emails ====================
    
    async def send_approval_requested(
        self,
        to: str,
        approver_name: str,
        requester_name: str,
        task_title: str,
        project_name: str,
        from_status: str,
        to_status: str,
        task_link: str,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when approval is requested"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #f5f5f5; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #0070f3;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Comment from requester:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0070f3 0%, #00c6ff 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">⏳ Approval Required</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {approver_name},</p>
                <p style="color: #4a4a4a;"><strong>{requester_name}</strong> is requesting your approval for a task status change in <strong>{project_name}</strong>.</p>
                
                <div style="background: #fafafa; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">{task_title}</p>
                    <p style="margin: 0; color: #6a6a6a;">
                        Status change: <span style="background: #e5e5e5; padding: 2px 8px; border-radius: 4px;">{from_status}</span>
                        → <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px;">{to_status}</span>
                    </p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{task_link}" style="background-color: #0070f3; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        Review & Approve
                    </a>
                </p>
                
                <p style="color: #9a9a9a; font-size: 12px; text-align: center; margin-top: 24px;">
                    You're receiving this because you're designated as an approver for this workflow.
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"🔔 Approval Needed: {task_title}", html)
    
    async def send_approval_approved(
        self,
        to: str,
        user_name: str,
        approver_name: str,
        task_title: str,
        project_name: str,
        new_status: str,
        task_link: str,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when approval request is approved"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #f5f5f5; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #22c55e;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Comment from approver:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">✅ Approval Approved!</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {user_name},</p>
                <p style="color: #4a4a4a;">Great news! Your approval request has been <strong style="color: #22c55e;">approved</strong> by <strong>{approver_name}</strong>.</p>
                
                <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 20px 0; border: 1px solid #22c55e;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">{task_title}</p>
                    <p style="margin: 0; color: #166534;">
                        Project: {project_name}<br/>
                        New status: <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px;">{new_status}</span>
                    </p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{task_link}" style="background-color: #22c55e; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        View Task
                    </a>
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"✅ Approved: {task_title}", html)
    
    async def send_approval_rejected(
        self,
        to: str,
        user_name: str,
        rejector_name: str,
        task_title: str,
        project_name: str,
        task_link: str,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when approval request is rejected"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #fef2f2; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #ef4444;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Reason for rejection:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        else:
            comment_section = """
            <p style="color: #6a6a6a; font-style: italic;">No reason provided.</p>
            """
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">❌ Approval Rejected</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {user_name},</p>
                <p style="color: #4a4a4a;">Unfortunately, your approval request has been <strong style="color: #ef4444;">rejected</strong> by <strong>{rejector_name}</strong>.</p>
                
                <div style="background: #fef2f2; padding: 16px; border-radius: 8px; margin: 20px 0; border: 1px solid #fecaca;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">{task_title}</p>
                    <p style="margin: 0; color: #991b1b;">Project: {project_name}</p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{task_link}" style="background-color: #6b7280; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        View Task
                    </a>
                </p>
                
                <p style="color: #9a9a9a; font-size: 12px; text-align: center; margin-top: 24px;">
                    You can modify the task and request approval again if needed.
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"❌ Rejected: {task_title}", html)
    
    # ==================== Document Approval Workflow Emails ====================
    
    async def send_document_approval_requested(
        self,
        to: str,
        approver_name: str,
        requester_name: str,
        document_title: str,
        document_type: str,
        from_status: str,
        to_status: str,
        document_link: str,
        project_name: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when document approval is requested"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #f5f5f5; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #8b5cf6;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Comment from requester:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        
        project_section = f"<br/>Project: {project_name}" if project_name else ""
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">📄 Document Approval Required</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {approver_name},</p>
                <p style="color: #4a4a4a;"><strong>{requester_name}</strong> is requesting your approval for a document status change.</p>
                
                <div style="background: #fafafa; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">📋 {document_title}</p>
                    <p style="margin: 0 0 8px 0; color: #6a6a6a;">
                        Type: <span style="background: #e5e5e5; padding: 2px 8px; border-radius: 4px;">{document_type.replace('_', ' ').title()}</span>
                        {project_section}
                    </p>
                    <p style="margin: 0; color: #6a6a6a;">
                        Status change: <span style="background: #e5e5e5; padding: 2px 8px; border-radius: 4px;">{from_status.replace('_', ' ').title()}</span>
                        → <span style="background: #8b5cf6; color: white; padding: 2px 8px; border-radius: 4px;">{to_status.replace('_', ' ').title()}</span>
                    </p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{document_link}" style="background-color: #8b5cf6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        Review Document
                    </a>
                </p>
                
                <p style="color: #9a9a9a; font-size: 12px; text-align: center; margin-top: 24px;">
                    You're receiving this because you're designated as an approver for document workflows.
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"📄 Document Approval Needed: {document_title}", html)
    
    async def send_document_approval_approved(
        self,
        to: str,
        user_name: str,
        approver_name: str,
        document_title: str,
        document_type: str,
        new_status: str,
        document_link: str,
        project_name: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when document approval request is approved"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #f5f5f5; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #22c55e;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Comment from approver:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        
        project_section = f"<br/>Project: {project_name}" if project_name else ""
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">✅ Document Approved!</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {user_name},</p>
                <p style="color: #4a4a4a;">Great news! Your document approval request has been <strong style="color: #22c55e;">approved</strong> by <strong>{approver_name}</strong>.</p>
                
                <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 20px 0; border: 1px solid #22c55e;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">📋 {document_title}</p>
                    <p style="margin: 0; color: #166534;">
                        Type: {document_type.replace('_', ' ').title()}
                        {project_section}<br/>
                        New status: <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px;">{new_status.replace('_', ' ').title()}</span>
                    </p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{document_link}" style="background-color: #22c55e; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        View Document
                    </a>
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"✅ Document Approved: {document_title}", html)
    
    async def send_document_approval_rejected(
        self,
        to: str,
        user_name: str,
        rejector_name: str,
        document_title: str,
        document_type: str,
        document_link: str,
        project_name: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """Send email when document approval request is rejected"""
        comment_section = ""
        if comment:
            comment_section = f"""
            <div style="background: #fef2f2; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #ef4444;">
                <p style="color: #6a6a6a; margin: 0 0 4px 0; font-size: 12px;">Reason for rejection:</p>
                <p style="color: #4a4a4a; margin: 0;">{comment}</p>
            </div>
            """
        else:
            comment_section = """
            <p style="color: #6a6a6a; font-style: italic;">No reason provided.</p>
            """
        
        project_section = f"<br/>Project: {project_name}" if project_name else ""
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">❌ Document Rejected</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {user_name},</p>
                <p style="color: #4a4a4a;">Unfortunately, your document approval request has been <strong style="color: #ef4444;">rejected</strong> by <strong>{rejector_name}</strong>.</p>
                
                <div style="background: #fef2f2; padding: 16px; border-radius: 8px; margin: 20px 0; border: 1px solid #fecaca;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 16px;">📋 {document_title}</p>
                    <p style="margin: 0; color: #991b1b;">
                        Type: {document_type.replace('_', ' ').title()}
                        {project_section}
                    </p>
                </div>
                
                {comment_section}
                
                <p style="margin: 24px 0; text-align: center;">
                    <a href="{document_link}" style="background-color: #6b7280; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                        View Document
                    </a>
                </p>
                
                <p style="color: #9a9a9a; font-size: 12px; text-align: center; margin-top: 24px;">
                    You can modify the document and request approval again if needed.
                </p>
            </div>
        </div>
        """
        return await self.send(to, f"❌ Document Rejected: {document_title}", html)

# Singleton instance
email_service = EmailService()
