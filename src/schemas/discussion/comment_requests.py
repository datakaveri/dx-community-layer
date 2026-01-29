import uuid
from fastapi import Body, Path, Query
from typing import List, Optional, Literal
from pydantic import BaseModel
import uuid
from ...database.discussion.enums import CommentReportReasonEnum

class RetrieveDiscussionCommentsParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(..., description="ID of the discussion"),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of comments per page"),
        sort: Literal["newest", "oldest", "hottest"] = Query(
            "newest", description="Sort order: newest, oldest, or hottest (most upvoted)"
        ),
    ):
        self.discussion_id = discussion_id
        self.page = page
        self.limit = limit
        self.sort = sort


class RetrieveCommentRepliesParams:
    def __init__(
        self,
        comment_id: uuid.UUID = Path(
            ..., description="ID of the comment to retrieve replies for"
        ),
        page: int = Query(1, gt=0, description="The page number for pagination"),
        limit: int = Query(10, gt=0, description="The number of replies per page"),
        sort: Literal["newest", "oldest", "hottest"] = Query(
            "newest", description="Sort order: newest, oldest, or hottest (most upvoted)"
        ),
    ):
        self.comment_id = comment_id
        self.page = page
        self.limit = limit
        self.sort = sort


class CreateCommentParams:
    def __init__(
        self,
        discussion_id: uuid.UUID = Path(..., description="ID of the discussion"),
        comment: str = Body(..., description="Comment to add to the discussion"),
        attachments: Optional[List[str]] = Body(
            default=None,
            description="List of attachments to add to the comment",
        ),
    ):
        self.discussion_id = discussion_id
        self.comment = comment
        self.attachments = attachments


class CreateCommentReplyParams:
    def __init__(
        self,
        comment_id: uuid.UUID = Path(..., description="ID of the comment to reply to"),
        reply: str = Body(..., description="Reply to add to the comment"),
        attachments: Optional[List[str]] = Body(
            default=None,
            description="List of attachments to add to the reply",
        ),
    ):
        self.comment_id = comment_id
        self.reply = reply
        self.attachments = attachments


class AddUpdateCommentReactionParams:
    def __init__(
        self,
        comment_id: uuid.UUID = Path(
            ..., description="ID of the comment to add/update reaction to"
        ),
        emoji_code: Optional[str] = Body(
            default=None,
            description="Emoji code to add/update",
        ),
    ):
        self.comment_id = comment_id
        self.emoji_code = emoji_code

class ReportCommentParams:
    def __init__(
        self,
        comment_id: uuid.UUID = Path(..., description="ID of the comment to report"),
        reason: CommentReportReasonEnum = Body(..., description="Reason for reporting the comment"),
    ):
        self.comment_id = comment_id
        self.reason = reason


class ReviewCommentReportParams:
    def __init__(
        self,
        report_id: uuid.UUID = Path(..., description="ID of the comment report"),
        action: Literal["IGNORE", "ACCEPT"] = Body(
            ..., description="Admin action: IGNORE or ACCEPT"
        ),
    ):
        self.report_id = report_id
        self.action = action
