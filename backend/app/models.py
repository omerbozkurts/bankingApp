"""Database models. Money is stored as integer kuruş (BigInteger) to avoid rounding errors."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Stable constraint names so Alembic migrations are predictable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_no: Mapped[str] = mapped_column(String(9), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    # HMAC of the T.C. identity number (never stored in clear); unique = one customer per person.
    national_id_digest: Mapped[str | None] = mapped_column(String(64), unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    failed_login_count: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    accounts: Mapped[list[Account]] = relationship(
        back_populates="customer", order_by="Account.id"
    )


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        # Only a credit account may go below zero, and never past its limit.
        CheckConstraint(
            "balance_kurus >= -COALESCE(credit_limit_kurus, 0)", name="balance_within_limit"
        ),
        CheckConstraint("goal_kurus IS NULL OR goal_kurus > 0", name="goal_positive"),
        CheckConstraint("kind IN ('checking', 'savings', 'credit')", name="kind_valid"),
        # Credit accounts, and only they, have a limit; their balance is the debt (<= 0).
        CheckConstraint(
            "(kind = 'credit') = (credit_limit_kurus IS NOT NULL)", name="credit_limit_iff_credit"
        ),
        CheckConstraint(
            "credit_limit_kurus IS NULL OR credit_limit_kurus > 0", name="credit_limit_positive"
        ),
        CheckConstraint("kind <> 'credit' OR balance_kurus <= 0", name="credit_not_positive"),
        CheckConstraint("kind = 'savings' OR goal_kurus IS NULL", name="goal_only_savings"),
        Index(
            "uq_accounts_one_credit_per_customer",
            "customer_id",
            unique=True,
            postgresql_where=text("kind = 'credit'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="checking", server_default="checking")
    name: Mapped[str] = mapped_column(String(80))
    # Stored without spaces (TR + 24 digits); formatted for display by the client.
    iban: Mapped[str] = mapped_column(String(34), unique=True)
    balance_kurus: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    goal_kurus: Mapped[int | None] = mapped_column(BigInteger)
    credit_limit_kurus: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped[Customer] = relationship(back_populates="accounts")

    @property
    def available_kurus(self) -> int:
        """What can be sent from this account: the balance, plus the limit for credit accounts."""
        return self.balance_kurus + (self.credit_limit_kurus or 0)


class Transfer(Base):
    """A money movement between two accounts. Creates one debit and one credit Transaction."""

    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount_kurus > 0", name="amount_positive"),
        CheckConstraint("from_account_id <> to_account_id", name="distinct_accounts"),
        # A retried request with the same key returns the original transfer instead of paying twice.
        UniqueConstraint("customer_id", "idempotency_key", name="uq_transfers_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount_kurus: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(140))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Transaction(Base):
    """Account movement. Positive amounts are credits, negative amounts are debits."""

    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("amount_kurus <> 0", name="amount_non_zero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    transfer_id: Mapped[int | None] = mapped_column(ForeignKey("transfers.id"), index=True)
    amount_kurus: Mapped[int] = mapped_column(BigInteger)
    balance_after_kurus: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(140))
    # Masked name of the other party for transfers, e.g. "De*** Yı***".
    counterparty: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
