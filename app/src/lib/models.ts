// App-side shapes, and their mapping from the API's snake_case JSON (backend/app/schemas.py).

export type AccountKind = 'checking' | 'savings' | 'credit';

export type Account = {
  id: number;
  kind: AccountKind;
  name: string;
  iban: string;
  /** Negative on a credit account: the amount owed. */
  balanceKurus: number;
  goalKurus: number | null;
  creditLimitKurus: number | null;
  /** Frozen by the bank: no money can leave it. */
  frozen: boolean;
};

export type Customer = {
  customerNo: string;
  fullName: string;
  isAdmin: boolean;
  accounts: Account[];
};

export type Movement = {
  id: number;
  amountKurus: number;
  balanceAfterKurus: number | null;
  description: string;
  counterparty: string | null;
  createdAt: string;
};

export type MovementPage = { items: Movement[]; nextBeforeId: number | null };

/** IBAN, or masked (TR12…0003) when looked up by customer number. */
export type Recipient = { iban: string; maskedName: string };

/** Who a transfer goes to: an IBAN, or a customer number (paid into their checking account). */
export type RecipientTarget = { iban: string } | { customerNo: string };

export type TransferResult = {
  id: number;
  fromAccountId: number;
  toIban: string;
  recipient: string;
  amountKurus: number;
  description: string;
  fromBalanceAfterKurus: number;
  createdAt: string;
};

export type ApiCustomer = { customer_no: string; full_name: string; is_admin: boolean };

export type ApiAccount = {
  id: number;
  kind: AccountKind;
  name: string;
  iban: string;
  balance_kurus: number;
  goal_kurus: number | null;
  credit_limit_kurus: number | null;
  frozen: boolean;
};

export type ApiTransaction = {
  id: number;
  amount_kurus: number;
  balance_after_kurus: number | null;
  description: string;
  counterparty: string | null;
  created_at: string;
};

export type ApiTransfer = {
  id: number;
  from_account_id: number;
  to_iban: string;
  recipient: string;
  amount_kurus: number;
  description: string;
  from_balance_after_kurus: number;
  created_at: string;
};

export function toAccount(a: ApiAccount): Account {
  return {
    id: a.id,
    kind: a.kind,
    name: a.name,
    iban: a.iban,
    balanceKurus: a.balance_kurus,
    goalKurus: a.goal_kurus,
    creditLimitKurus: a.credit_limit_kurus,
    frozen: a.frozen,
  };
}

export function toCustomer(me: ApiCustomer, accounts: ApiAccount[]): Customer {
  return {
    customerNo: me.customer_no,
    fullName: me.full_name,
    isAdmin: me.is_admin,
    accounts: accounts.map(toAccount),
  };
}

export function toMovement(t: ApiTransaction): Movement {
  return {
    id: t.id,
    amountKurus: t.amount_kurus,
    balanceAfterKurus: t.balance_after_kurus,
    description: t.description,
    counterparty: t.counterparty,
    createdAt: t.created_at,
  };
}

export function toTransferResult(t: ApiTransfer): TransferResult {
  return {
    id: t.id,
    fromAccountId: t.from_account_id,
    toIban: t.to_iban,
    recipient: t.recipient,
    amountKurus: t.amount_kurus,
    description: t.description,
    fromBalanceAfterKurus: t.from_balance_after_kurus,
    createdAt: t.created_at,
  };
}

/** What the customer owns: credit accounts are borrowed money, so they don't count. */
export function totalBalance(customer: Customer): number {
  return customer.accounts.reduce((sum, a) => (a.kind === 'credit' ? sum : sum + a.balanceKurus), 0);
}

/** What can be sent from the account: the balance, plus the limit for a credit account. */
export function availableKurus(account: Account): number {
  return account.balanceKurus + (account.creditLimitKurus ?? 0);
}

/** The account money sent to this customer's number lands in: their first checking account. */
export function paymentAccount(customer: Customer): Account | undefined {
  return customer.accounts
    .filter((a) => a.kind === 'checking')
    .reduce<Account | undefined>((first, a) => (first && first.id < a.id ? first : a), undefined);
}

/** Amount owed on a credit account; 0 for other accounts. */
export function debtKurus(account: Account): number {
  return account.kind === 'credit' ? -account.balanceKurus : 0;
}
