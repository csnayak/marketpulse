export type Product = {
  id: number;
  name: string;
  coinbase_product_id: string;
  quote_currency: string;
  is_active: boolean;
  price: string | null;
  price_as_of: string | null;
  price_status: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  list: () => request<Product[]>("/products"),
  create: (data: Pick<Product, "name" | "coinbase_product_id" | "is_active">) =>
    request<Product>("/products", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Pick<Product, "name" | "coinbase_product_id" | "is_active">>) =>
    request<Product>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/products/${id}`, { method: "DELETE" }),
};
