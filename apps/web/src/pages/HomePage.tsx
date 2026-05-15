import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function HomePage() {
  const { user } = useAuth();

  return (
    <>
      {/* Hero */}
      <section className="bg-primary text-white py-5">
        <div className="container py-4">
          <div className="row align-items-center g-5">
            <div className="col-lg-6">
              <h1 className="display-4 fw-bold mb-3">Help your kids fall in love with reading</h1>
              <p className="lead mb-4">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque vehicula felis vel
                libero facilisis, eu tincidunt purus fermentum. Fusce scelerisque lorem vel mauris
                pharetra, vel hendrerit orci dapibus.
              </p>
              {user ? (
                <Link to="/library" className="btn btn-light btn-lg fw-semibold px-4">
                  Go to My Library
                </Link>
              ) : (
                <Link to="/login" className="btn btn-light btn-lg fw-semibold px-4">
                  Get Started
                </Link>
              )}
            </div>
            <div className="col-lg-6 text-center">
              <span style={{ fontSize: '10rem', lineHeight: 1 }} aria-hidden="true">📖</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-5">
        <div className="container">
          <h2 className="text-center fw-bold mb-5">Everything you need to track reading progress</h2>
          <div className="row g-4">
            <div className="col-md-4">
              <div className="card h-100 border-0 shadow-sm">
                <div className="card-body p-4">
                  <div className="fs-1 mb-3">📚</div>
                  <h5 className="card-title fw-bold">Build Bookshelves</h5>
                  <p className="card-text text-muted">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
                    incididunt ut labore et dolore magna aliqua.
                  </p>
                </div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="card h-100 border-0 shadow-sm">
                <div className="card-body p-4">
                  <div className="fs-1 mb-3">📊</div>
                  <h5 className="card-title fw-bold">Track Progress</h5>
                  <p className="card-text text-muted">
                    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
                    aliquip ex ea commodo consequat.
                  </p>
                </div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="card h-100 border-0 shadow-sm">
                <div className="card-body p-4">
                  <div className="fs-1 mb-3">👨‍👩‍👧‍👦</div>
                  <h5 className="card-title fw-bold">Manage Profiles</h5>
                  <p className="card-text text-muted">
                    Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
                    eu fugiat nulla pariatur.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-light py-5">
        <div className="container text-center py-3">
          <h2 className="fw-bold mb-3">Ready to get started?</h2>
          <p className="text-muted mb-4 col-md-6 mx-auto">
            Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt
            mollit anim id est laborum.
          </p>
          {user ? (
            <Link to="/library" className="btn btn-primary btn-lg px-5">
              Open My Library
            </Link>
          ) : (
            <div className="d-flex justify-content-center gap-3 flex-wrap">
              <Link to="/register" className="btn btn-primary btn-lg px-5">
                Create an Account
              </Link>
              <Link to="/login" className="btn btn-outline-primary btn-lg px-5">
                Log In
              </Link>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
