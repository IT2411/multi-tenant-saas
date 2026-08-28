import enum


class OrgRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class TaskStatus(enum.StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(enum.StrEnum):
    TASK_ASSIGNED = "task_assigned"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_COMMENTED = "task_commented"
    ORG_INVITATION = "org_invitation"
    ROLE_UPDATED = "role_updated"


class AuditAction(enum.StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SOFT_DELETE = "SOFT_DELETE"
    RESTORE = "RESTORE"
