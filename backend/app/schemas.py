"""Pydantic request models. Validation here is the first line of defence:
type checks, length limits and RegEx patterns run before any route code."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from . import validators as v


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    skills: list[str] = Field(default_factory=list, max_length=15)
    school_or_dept: str | None = Field(default=None, max_length=100)
    contact_number: str | None = None
    region_code: str | None = None
    region_name: str | None = Field(default=None, max_length=120)
    province_code: str | None = None
    province_name: str | None = Field(default=None, max_length=120)
    city_code: str | None = None
    city_name: str | None = Field(default=None, max_length=120)
    barangay_code: str | None = None
    barangay_name: str | None = Field(default=None, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _name(cls, x):
        if x is None:
            return x
        x = v.clean_text(x)
        if not v.NAME_RE.match(x):
            raise ValueError("Name may only contain letters, numbers, spaces and . , ' -")
        return x

    @field_validator("headline", "bio", "school_or_dept", "region_name", "province_name",
                     "city_name", "barangay_name")
    @classmethod
    def _text(cls, x):
        return v.assert_safe_text(x) if x else x

    @field_validator("skills")
    @classmethod
    def _skills(cls, items):
        out = []
        for s in items:
            s = v.clean_text(s)
            if not v.SKILL_RE.match(s):
                raise ValueError(f"Invalid skill: {s!r}")
            out.append(s)
        return out

    @field_validator("contact_number")
    @classmethod
    def _phone(cls, x):
        if not x:
            return None
        x = x.replace(" ", "").replace("-", "")
        if not v.PH_PHONE_RE.match(x):
            raise ValueError("Use a Philippine mobile number like 09123456789 or +639123456789")
        return x

    @field_validator("region_code", "province_code", "city_code", "barangay_code")
    @classmethod
    def _psgc(cls, x):
        if x and not v.PSGC_CODE_RE.match(x):
            raise ValueError("Invalid PSGC code")
        return x


class PortfolioUpdate(BaseModel):
    title: str
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def _title(cls, x):
        x = v.assert_safe_text(x, "title")
        if not 3 <= len(x) <= 120:
            raise ValueError("Title must be 3-120 characters")
        return x

    @field_validator("description")
    @classmethod
    def _desc(cls, x):
        return v.assert_safe_text(x) if x else x


class GigIn(BaseModel):
    title: str
    description: str = Field(min_length=20, max_length=4000)
    category: str
    budget_min: Decimal = Field(ge=50, le=100000, decimal_places=2)
    budget_max: Decimal = Field(ge=50, le=100000, decimal_places=2)
    deadline: date

    @field_validator("title")
    @classmethod
    def _title(cls, x):
        x = v.clean_text(x)
        if not v.TITLE_RE.match(x) or len(x) < 5:
            raise ValueError("Title must be 5-150 characters using letters, numbers and common punctuation")
        return v.assert_safe_text(x, "title")

    @field_validator("description")
    @classmethod
    def _desc(cls, x):
        x = v.assert_safe_text(x, "description")
        if len(x) < 20:
            raise ValueError("Description must be at least 20 characters")
        return x

    @field_validator("category")
    @classmethod
    def _cat(cls, x):
        if x not in v.CATEGORIES:
            raise ValueError("Unknown category")
        return x

    @field_validator("deadline")
    @classmethod
    def _deadline(cls, d):
        if d < date.today() + timedelta(days=1):
            raise ValueError("Deadline must be at least tomorrow")
        return d

    @model_validator(mode="after")
    def _range(self):
        if self.budget_max < self.budget_min:
            raise ValueError("Maximum budget must be greater than or equal to minimum budget")
        return self


class BidIn(BaseModel):
    amount: Decimal = Field(ge=50, le=100000, decimal_places=2)
    delivery_days: int = Field(ge=1, le=90)
    proposal: str = Field(min_length=20, max_length=2000)

    @field_validator("proposal")
    @classmethod
    def _p(cls, x):
        x = v.assert_safe_text(x, "proposal")
        if len(x) < 20:
            raise ValueError("Proposal must be at least 20 characters")
        return x


class SubmissionIn(BaseModel):
    link_url: str
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("link_url")
    @classmethod
    def _url(cls, x):
        return v.validate_deliverable_url(x)

    @field_validator("notes")
    @classmethod
    def _notes(cls, x):
        return v.assert_safe_text(x) if x else x


class ThreadMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def _b(cls, x):
        x = v.assert_safe_text(x, "message")
        if not x:
            raise ValueError("Message cannot be empty")
        return x


class RejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def _r(cls, x):
        return v.assert_safe_text(x, "reason")


class PayoutUpdate(BaseModel):
    status: Literal["pending", "processing", "paid", "failed"]
    method: str | None = Field(default=None, max_length=40)
    reference_no: str | None = None
    admin_note: str | None = Field(default=None, max_length=500)

    @field_validator("method", "admin_note")
    @classmethod
    def _t(cls, x):
        return v.assert_safe_text(x) if x else x

    @field_validator("reference_no")
    @classmethod
    def _ref(cls, x):
        if x and not v.REFERENCE_RE.match(x):
            raise ValueError("Reference may only contain letters, numbers, - _ / and spaces")
        return x

    @model_validator(mode="after")
    def _paid_needs_ref(self):
        if self.status == "paid" and not (self.method and self.reference_no):
            raise ValueError("Marking a payout as paid requires the payment method and reference number")
        return self


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: Literal["client", "freelancer", "admin"] | None = None
