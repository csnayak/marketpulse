import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type { Product } from "./api";

type ProductForm = { name: string; coinbase_product_id: string; is_active: boolean };
type ProductFilter = "all" | "active" | "inactive";
const emptyForm: ProductForm = { name: "", coinbase_product_id: "", is_active: true };

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ProductFilter>("all");

  const loadProducts = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      setProducts(await api.list());
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load products.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts();
    const timer = window.setInterval(() => {
      if (!document.hidden) void loadProducts(false);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [loadProducts]);

  function openAddForm() {
    setEditing(null);
    setForm(emptyForm);
    setError("");
    setFormOpen(true);
  }

  function openEditForm(product: Product) {
    setEditing(product);
    setForm({ name: product.name, coinbase_product_id: product.coinbase_product_id, is_active: product.is_active });
    setError("");
    setFormOpen(true);
  }

  async function saveProduct(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editing) await api.update(editing.id, form);
      else await api.create(form);
      setFormOpen(false);
      await loadProducts(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save product.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteProduct(product: Product) {
    if (!window.confirm(`Remove ${product.coinbase_product_id} from your tracked products?`)) return;
    setError("");
    try {
      await api.delete(product.id);
      await loadProducts(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not delete product.");
    }
  }

  const visibleProducts = products.filter((product) => {
    const matchesSearch = `${product.name} ${product.coinbase_product_id}`.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === "all" || (filter === "active" ? product.is_active : !product.is_active);
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <a className="brand" href="#market-overview">
          <span className="brand-mark" aria-hidden="true">◐</span>
          <span>MarketPulse</span>
        </a>

        <nav className="side-nav" aria-label="Main navigation">
          <p className="nav-label">GENERAL</p>
          <a href="#market-overview"><span aria-hidden="true">⌂</span> Overview</a>
          <a className="selected" href="#products-list"><span aria-hidden="true">▣</span> Market</a>
        </nav>

        <section className="watchlist" aria-labelledby="watchlist-heading">
          <p className="nav-label" id="watchlist-heading">WATCHLIST</p>
          {products.slice(0, 6).map((product) => (
            <a className="watch-item" href="#products-list" key={product.id}>
              <span className="coin-mark">{product.coinbase_product_id.split("-")[0].slice(0, 1)}</span>
              <span className="watch-copy">
                <span>{product.name} ({product.coinbase_product_id.split("-")[0]})</span>
                <strong>{product.price ? `${product.price} ${product.quote_currency}` : "Price unavailable"}</strong>
              </span>
            </a>
          ))}
          {!loading && products.length === 0 && <p className="sidebar-empty">No saved products</p>}
        </section>
        <p className="sidebar-source">Prices provided by Coinbase</p>
      </aside>

      <main className="main-content">
        <div className="searchbar">
          <span aria-hidden="true">⌕</span>
          <input aria-label="Search products" placeholder="Search products…" value={search}
            onChange={(event) => setSearch(event.target.value)} />
        </div>

        <section className="overview" id="market-overview">
          <div className="page-heading">
            <div><p className="breadcrumb">Market / Overview</p><h1>Market Overview</h1></div>
            <button className="primary" onClick={openAddForm}>＋ Add product</button>
          </div>

          <div className="featured-grid">
            {visibleProducts.slice(0, 3).map((product) => (
              <article className="featured-card" key={product.id}>
                <div className="featured-title">
                  <span className="coin-mark">{product.coinbase_product_id.split("-")[0].slice(0, 1)}</span>
                  <div><strong>{product.name}</strong><span>{product.coinbase_product_id}</span></div>
                  <span className={`status ${product.price_status}`}>{product.price_status.replace("_", " ")}</span>
                </div>
                <div className="featured-price">
                  {product.price ? `${product.price} ${product.quote_currency}` : "—"}
                </div>
                <p className="last-updated">
                  {product.price_as_of ? `Updated ${new Date(product.price_as_of).toLocaleString()}` : "Waiting for first price"}
                </p>
              </article>
            ))}
            {!loading && products.length === 0 && (
              <p className="empty-featured">Add a product to see its latest Coinbase price here.</p>
            )}
          </div>
        </section>

        <section className="market-panel" id="products-list" aria-labelledby="products-heading">
          <div className="market-heading">
            <div><h2 id="products-heading">Tracked assets</h2><p>{visibleProducts.length} products</p></div>
            <button onClick={() => void loadProducts()}>Refresh list</button>
          </div>
          <div className="table-toolbar">
            <div className="filter-tabs" aria-label="Product filter">
              {(["all", "active", "inactive"] as const).map((value) => (
                <button className={filter === value ? "filter-selected" : ""} key={value}
                  onClick={() => setFilter(value)}>{value[0].toUpperCase() + value.slice(1)}</button>
              ))}
            </div>
            <span className="source-label">Coinbase · Last price</span>
          </div>

          {error && <p className="notice error" role="alert">{error}</p>}
          {loading ? <p className="notice">Loading products…</p> : visibleProducts.length === 0 ? (
            <p className="notice">No matching products. Add a product or change the filter.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>#</th><th>Asset</th><th>Price</th><th>State</th><th>Updated</th><th><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>{visibleProducts.map((product, index) => (
                  <tr key={product.id}>
                    <td className="row-number">{index + 1}</td>
                    <td><span className="asset-cell"><span className="coin-mark">{product.coinbase_product_id.split("-")[0].slice(0, 1)}</span><span><strong>{product.name}</strong><small>{product.coinbase_product_id}</small></span></span></td>
                    <td className="price-cell">{product.price ? `${product.price} ${product.quote_currency}` : "—"}</td>
                    <td><span className={`status ${product.price_status}`}>{product.price_status.replace("_", " ")}</span>{!product.is_active && <span className="inactive-label">Inactive</span>}</td>
                    <td>{product.price_as_of ? new Date(product.price_as_of).toLocaleString() : "—"}</td>
                    <td className="actions">
                      <button aria-label={`Edit ${product.coinbase_product_id}`} onClick={() => openEditForm(product)}>Edit</button>
                      <button aria-label={`Delete ${product.coinbase_product_id}`} className="danger-text" onClick={() => void deleteProduct(product)}>Delete</button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {formOpen && <div className="modal-backdrop" role="presentation">
        <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="form-title">
          <h2 id="form-title">{editing ? "Edit product" : "Add product"}</h2>
          {error && <p className="notice error" role="alert">{error}</p>}
          <form onSubmit={saveProduct}>
            <label>
              Display name
              <input required maxLength={80} value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </label>
            <label>
              Coinbase product ID
              <input required maxLength={32} placeholder="BTC-USD" value={form.coinbase_product_id}
                onChange={(event) => setForm({ ...form, coinbase_product_id: event.target.value.toUpperCase() })} />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={form.is_active}
                onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
              Active
            </label>
            <div className="form-actions">
              <button type="button" onClick={() => setFormOpen(false)}>Cancel</button>
              <button className="primary" disabled={saving}>
                {saving ? "Saving…" : "Save product"}
              </button>
            </div>
          </form>
        </section>
      </div>}
    </div>
  );
}
