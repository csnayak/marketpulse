# Spec 05 — Dashboard UI

**Status:** Initial product CRUD UI implemented; local verification and refinement remain  
**Priority:** P0  
**Depends on:** Product CRUD API and saved latest quote data

## Goal

Build a small responsive dashboard for viewing Coinbase markets, their saved prices, and their update status. The browser communicates only with the FastAPI backend. It never connects directly to PostgreSQL or Coinbase.

## Dashboard

Show the application name, tracked product count, an `Add product` action, and a `Refresh list` action. Use a table on wide screens and allow horizontal scrolling on narrow screens.

Use the supplied market-dashboard reference for visual direction: cool gray page background, white workspace, left navigation/watchlist, top search, market heading, compact quote cards, then a filtered asset table. Keep the palette restrained with blue selection and clear status colors. The database contains only the latest quote, so do not show trend lines or percentage changes that imply price history.

If the initial Coinbase bootstrap is incomplete, show how many products were added and provide the retry action returned by the backend.

Each product shows:

- Name and Coinbase product ID.
- Latest saved price and quote currency, or a clear message when no price is available.
- Price state: `Current`, `Stale`, `Unavailable`, or `Not fetched`.
- Last successful update time in the viewer’s local timezone.
- Inactive status, when applicable.
- Edit and delete actions.

Show the last successful price after a refresh failure and identify it as stale when it exceeds the configured freshness window. Never display a failed or missing price as zero.

## Product actions

- **Add:** Enter a display name and Coinbase product ID in `BASE-QUOTE` form. Validate the format and reject duplicate markets. This first UI slice does not require a live Coinbase catalog search.
- **Edit:** Change the display name, product ID, or active state. Validate product ID format and uniqueness.
- **Delete:** Ask for confirmation naming the product. Explain that its tracked record and latest quote will be removed.
- **Refresh list:** Reload saved product data from the backend. Price fetching remains the responsibility of the scheduled server worker.

Use inline field validation and preserve entered values after errors. Disable a submitted action while it is pending. Keep CRUD usable if Coinbase is unavailable.

## Data loading and states

- Load products from the backend on page open.
- Poll the backend every 15 seconds while the page is visible; pause polling when hidden.
- Reload after successful create, edit, or delete.
- Provide loading, empty, retryable load-error, and mutation-error states.
- Keep an existing rendered list visible if a background load fails.
- Do not let an older polling response overwrite a newer manual refresh result.

The backend returns price amounts as decimal strings and timestamps as UTC ISO 8601. Preserve price precision in the browser; do not convert amounts to JavaScript `Number` for arithmetic.

## Accessibility and responsive behavior

- Use semantic headings, table headers, labels, buttons, and dialogs.
- All actions work by keyboard and have visible focus.
- State is conveyed with text as well as color.
- Associate field errors with their inputs and focus the first invalid field.
- Announce meaningful action results without announcing every background price update.
- Support narrow screens and 200% zoom without losing core actions.

## Acceptance criteria

1. The dashboard loads saved products and quote states through the backend API.
2. Prices, currency, update time, stale state, and unavailable state are shown correctly.
3. Create, edit, and delete use backend endpoints and report validation/provider errors clearly.
4. Periodic list polling displays the latest prices saved by the server worker without page navigation.
5. Empty, loading, error, and success states are usable on desktop, mobile, keyboard, and screen reader.

## UI verification

Use a mocked API for component and end-to-end checks. Cover product loading, CRUD, polling, duplicate validation, and keyboard operation. Do not call live Coinbase from ordinary UI tests.
