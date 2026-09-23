import enum


class Role(str, enum.Enum):
    REQUESTER = "REQUESTER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ChangeStage(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ENGINEERING_REVIEW = "ENGINEERING_REVIEW"
    MANUFACTURING_REVIEW = "MANUFACTURING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Decision(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
