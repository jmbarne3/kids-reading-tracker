import { type FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    username: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) navigate('/library', { replace: true });
  }, [user, navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.password2) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await register(form);
      navigate('/library', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container py-5">
      <div className="row justify-content-center">
        <div className="col-sm-10 col-md-8 col-lg-6">
          <div className="card shadow-sm border-0">
            <div className="card-body p-4 p-md-5">
              <h1 className="h3 fw-bold text-center mb-1">Create an account</h1>
              <p className="text-center text-muted mb-4 small">
                Already have one?{' '}
                <Link to="/login" className="fw-semibold">
                  Sign in
                </Link>
              </p>

              <form onSubmit={handleSubmit} noValidate>
                {error && (
                  <div className="alert alert-danger py-2" role="alert">
                    {error}
                  </div>
                )}

                <div className="row g-3 mb-3">
                  <div className="col-sm-6">
                    <label htmlFor="first_name" className="form-label">
                      First name
                    </label>
                    <input
                      id="first_name"
                      name="first_name"
                      type="text"
                      className="form-control"
                      autoComplete="given-name"
                      required
                      value={form.first_name}
                      onChange={handleChange}
                    />
                  </div>
                  <div className="col-sm-6">
                    <label htmlFor="last_name" className="form-label">
                      Last name
                    </label>
                    <input
                      id="last_name"
                      name="last_name"
                      type="text"
                      className="form-control"
                      autoComplete="family-name"
                      required
                      value={form.last_name}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="email" className="form-label">
                    Email address
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    className="form-control"
                    autoComplete="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="username" className="form-label">
                    Username
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    className="form-control"
                    autoComplete="username"
                    required
                    value={form.username}
                    onChange={handleChange}
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="password" className="form-label">
                    Password
                  </label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    className="form-control"
                    autoComplete="new-password"
                    required
                    value={form.password}
                    onChange={handleChange}
                  />
                </div>

                <div className="mb-4">
                  <label htmlFor="password2" className="form-label">
                    Confirm password
                  </label>
                  <input
                    id="password2"
                    name="password2"
                    type="password"
                    className="form-control"
                    autoComplete="new-password"
                    required
                    value={form.password2}
                    onChange={handleChange}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
                      Creating account…
                    </>
                  ) : (
                    'Create Account'
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
