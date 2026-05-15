import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  addBookByISBN,
  getShelf,
  moveToShelf,
  removeFromShelf,
  SHELF_LABELS,
  type ShelfEntry,
  type ShelfType,
} from '../api/library';

const SHELF_TABS: ShelfType[] = ['currently_reading', 'want_to_read', 'read', 'did_not_finish'];

// ---------------------------------------------------------------------------
// Add Book modal
// ---------------------------------------------------------------------------

interface AddBookModalProps {
  onAdded: (entry: ShelfEntry) => void;
}

function AddBookModal({ onAdded }: AddBookModalProps) {
  const [isbn, setIsbn] = useState('');
  const [shelf, setShelf] = useState<ShelfType>('want_to_read');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const result = await addBookByISBN(isbn.trim(), shelf);
      const label = SHELF_LABELS[result.shelf_entry.shelf];
      const verb = result.imported ? 'Imported and added' : 'Added';
      setSuccess(`${verb} "${result.shelf_entry.book.title}" to ${label}.`);
      setIsbn('');
      onAdded(result.shelf_entry);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-focus the ISBN input when the modal opens.
  const handleShow = () => {
    setError(null);
    setSuccess(null);
    setIsbn('');
    setTimeout(() => inputRef.current?.focus(), 150);
  };

  return (
    <>
      <button
        className="btn btn-primary"
        data-bs-toggle="modal"
        data-bs-target="#addBookModal"
        onClick={handleShow}
      >
        + Add Book
      </button>

      <div
        className="modal fade"
        id="addBookModal"
        tabIndex={-1}
        aria-labelledby="addBookModalLabel"
        aria-hidden="true"
      >
        <div className="modal-dialog">
          <div className="modal-content">
            <form onSubmit={handleSubmit}>
              <div className="modal-header">
                <h5 className="modal-title" id="addBookModalLabel">
                  Add Book by ISBN
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  data-bs-dismiss="modal"
                  aria-label="Close"
                />
              </div>

              <div className="modal-body">
                {error && <div className="alert alert-danger py-2">{error}</div>}
                {success && <div className="alert alert-success py-2">{success}</div>}

                <div className="mb-3">
                  <label htmlFor="isbnInput" className="form-label fw-semibold">
                    ISBN
                  </label>
                  <input
                    id="isbnInput"
                    ref={inputRef}
                    type="text"
                    className="form-control"
                    placeholder="e.g. 9780747532699"
                    value={isbn}
                    onChange={(e) => setIsbn(e.target.value)}
                    required
                    disabled={loading}
                  />
                  <div className="form-text">ISBN-10 or ISBN-13 (dashes optional).</div>
                </div>

                <div className="mb-1">
                  <label htmlFor="shelfSelect" className="form-label fw-semibold">
                    Add to shelf
                  </label>
                  <select
                    id="shelfSelect"
                    className="form-select"
                    value={shelf}
                    onChange={(e) => setShelf(e.target.value as ShelfType)}
                    disabled={loading}
                  >
                    {SHELF_TABS.map((s) => (
                      <option key={s} value={s}>
                        {SHELF_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  data-bs-dismiss="modal"
                  disabled={loading}
                >
                  Close
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading || !isbn.trim()}>
                  {loading ? (
                    <>
                      <span
                        className="spinner-border spinner-border-sm me-2"
                        role="status"
                        aria-hidden="true"
                      />
                      Looking up…
                    </>
                  ) : (
                    'Add to Library'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Shelf card
// ---------------------------------------------------------------------------

interface ShelfCardProps {
  entry: ShelfEntry;
  onRemove: (id: number) => void;
  onMove: (id: number, shelf: ShelfType) => void;
}

function ShelfCard({ entry, onRemove, onMove }: ShelfCardProps) {
  const { book } = entry;
  const otherShelves = SHELF_TABS.filter((s) => s !== entry.shelf);

  return (
    <div className="col-sm-6 col-lg-4 col-xl-3">
      <div className="card h-100 shadow-sm">
        {book.cover_image_url ? (
          <img
            src={book.cover_image_url}
            alt={`Cover of ${book.title}`}
            className="card-img-top"
            style={{ objectFit: 'cover', maxHeight: 200 }}
          />
        ) : (
          <div
            className="d-flex align-items-center justify-content-center bg-light text-muted"
            style={{ height: 160 }}
          >
            <span style={{ fontSize: '3rem' }}>📖</span>
          </div>
        )}
        <div className="card-body d-flex flex-column">
          <h6 className="card-title fw-semibold mb-1">{book.title}</h6>
          {book.author_names.length > 0 && (
            <p className="card-text text-muted small mb-2">{book.author_names.join(', ')}</p>
          )}
          {book.page_count && (
            <p className="card-text text-muted small mb-0">{book.page_count} pages</p>
          )}

          <div className="mt-auto pt-3 d-flex gap-2 flex-wrap">
            <div className="dropdown">
              <button
                className="btn btn-sm btn-outline-secondary dropdown-toggle"
                type="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                Move
              </button>
              <ul className="dropdown-menu">
                {otherShelves.map((s) => (
                  <li key={s}>
                    <button
                      className="dropdown-item"
                      onClick={() => onMove(entry.id, s)}
                    >
                      {SHELF_LABELS[s]}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
            <button
              className="btn btn-sm btn-outline-danger"
              onClick={() => onRemove(entry.id)}
            >
              Remove
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function LibraryPage() {
  const { user } = useAuth();
  const [activeShelf, setActiveShelf] = useState<ShelfType>('currently_reading');
  const [entries, setEntries] = useState<ShelfEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getShelf(activeShelf)
      .then(setEntries)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [activeShelf]);

  const handleAdded = (entry: ShelfEntry) => {
    if (entry.shelf === activeShelf) {
      setEntries((prev) => {
        // Update in-place if already present (moved), otherwise prepend.
        const idx = prev.findIndex((e) => e.id === entry.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = entry;
          return next;
        }
        return [entry, ...prev];
      });
    } else {
      // The book landed on a different shelf — switch to it so the user sees it.
      setActiveShelf(entry.shelf);
    }
  };

  const handleRemove = async (id: number) => {
    await removeFromShelf(id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const handleMove = async (id: number, shelf: ShelfType) => {
    const updated = await moveToShelf(id, shelf);
    setEntries((prev) => prev.filter((e) => e.id !== updated.id));
    if (shelf === activeShelf) {
      setEntries((prev) => [updated, ...prev]);
    }
  };

  return (
    <div className="container py-5">
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="fw-bold mb-1">My Library</h1>
          {user && (
            <p className="text-muted mb-0">
              Welcome back, {user.first_name || user.username}!
            </p>
          )}
        </div>
        <AddBookModal onAdded={handleAdded} />
      </div>

      {/* Shelf tabs */}
      <ul className="nav nav-tabs mb-4">
        {SHELF_TABS.map((s) => (
          <li className="nav-item" key={s}>
            <button
              className={`nav-link${activeShelf === s ? ' active' : ''}`}
              onClick={() => setActiveShelf(s)}
            >
              {SHELF_LABELS[s]}
            </button>
          </li>
        ))}
      </ul>

      {/* Shelf content */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading…</span>
          </div>
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <div className="fs-1 mb-3" aria-hidden="true">📚</div>
          <h5 className="fw-semibold">No books here yet</h5>
          <p className="mb-0">Click <strong>+ Add Book</strong> and enter an ISBN to get started.</p>
        </div>
      ) : (
        <div className="row g-4">
          {entries.map((entry) => (
            <ShelfCard
              key={entry.id}
              entry={entry}
              onRemove={handleRemove}
              onMove={handleMove}
            />
          ))}
        </div>
      )}
    </div>
  );
}

