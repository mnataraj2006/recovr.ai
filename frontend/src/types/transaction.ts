export interface Transaction {
  id: string;
  checkout_id: string;
  amount: number;
  status: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  created_at: string;
  failure_mode?: string;
  action_proposed?: string;
}
