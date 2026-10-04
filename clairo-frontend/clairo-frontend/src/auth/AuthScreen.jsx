import { useState } from "react";
import { useAuth } from "./AuthContext";
import { ErrorBox, Spinner } from "../components/ui";
import { BrandMark } from "../components/BrandMark";
import "../components/dashboard.css";

export default function AuthScreen() {
  const { login, register, checking } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await (mode === "login" ? login(email, password) : register(email, password));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (checking) {
    return (
      <div className="auth-screen">
        <Spinner size={28} />
      </div>
    );
  }

  const isLogin = mode === "login";
  return (
    <div className="auth-screen">
      <form className="auth-card glass-panel" onSubmit={submit} noValidate>
        <div className="auth-card__brand font-display"><BrandMark /></div>
        <p className="auth-card__tagline">Denial intelligence for revenue-cycle teams</p>

        <div className="auth-tabs" role="tablist">
          {["login", "register"].map((m) => (
            <button
              key={m} type="button" role="tab" aria-selected={mode === m}
              className={`auth-tab ${mode === m ? "auth-tab--active" : ""}`}
              onClick={() => { setMode(m); setError(null); }}
            >
              {m === "login" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>

        <label className="auth-field">
          <span>Email</span>
          <input
            type="email" autoComplete="email" value={email} required
            onChange={(e) => setEmail(e.target.value)} placeholder="you@practice.com"
          />
        </label>
        <label className="auth-field">
          <span>Password</span>
          <input
            type="password" required minLength={8}
            autoComplete={isLogin ? "current-password" : "new-password"}
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder={isLogin ? "Your password" : "At least 8 characters"}
          />
        </label>

        <ErrorBox message={error} />

        <button className="btn-primary auth-submit" type="submit" disabled={busy || !email || !password}>
          {busy ? <Spinner size={16} /> : isLogin ? "Sign in" : "Create account"}
        </button>

        <p className="auth-note">
          {isLogin
            ? "New here? Create an account — it takes a few seconds."
            : "Demo data is shared with every account so dashboards are never empty."}
        </p>
      </form>
    </div>
  );
}
