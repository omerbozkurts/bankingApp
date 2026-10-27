// App-side shapes, and their mapping from the API's snake_case JSON (backend/app/schemas.py).

export type Account = {
  id: number;
  name: string;
  iban: string;
  balanceKurus: number;
  goalKurus: number | null;
};

export type Customer = {
  customerNo: string;
  fullName: string;
  accounts: Account[];
};

export type ApiCustomer = { customer_no: string; full_name: string };

export type ApiAccount = {
  id: number;
  name: string;
  iban: string;
  balance_kurus: number;
  goal_kurus: number | null;
};

export function toCustomer(me: ApiCustomer, accounts: ApiAccount[]): Customer {
  return {
    customerNo: me.customer_no,
    fullName: me.full_name,
    accounts: accounts.map((a) => ({
      id: a.id,
      name: a.name,
      iban: a.iban,
      balanceKurus: a.balance_kurus,
      goalKurus: a.goal_kurus,
    })),
  };
}

export function totalBalance(customer: Customer): number {
  return customer.accounts.reduce((sum, a) => sum + a.balanceKurus, 0);
}
