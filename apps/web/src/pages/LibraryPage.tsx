import { useAuth } from '../context/AuthContext';

export default function LibraryPage() {
  const { user } = useAuth();

  return (
    <div className="container py-5">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="fw-bold mb-1">My Library</h1>
          {user && (
            <p className="text-muted mb-0">
              Welcome back, {user.first_name || user.username}!
            </p>
          )}
        </div>
        <button className="btn btn-primary" disabled>
          + New Bookshelf
        </button>
      </div>

      <div className="text-center py-5 text-muted">
        <div className="fs-1 mb-3" aria-hidden="true">📚</div>
        <h5 className="fw-semibold">Your bookshelves will appear here</h5>
        <p className="mb-0">This section is coming soon.</p>
      </div>
    </div>
  );
}
