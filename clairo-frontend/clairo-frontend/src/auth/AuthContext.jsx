import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  UNAUTHORIZED_EVENT, clearToken, getMe, getToken, login as apiLogin,
  register as apiRegister, setToken,
} from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" only while we validate a token left over from a previous visit.
  const [checking, setChecking] = useState(() => Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) return undefined;
    let cancelled = false;
    getMe()
      .then((me) => { if (!cancelled) setUser(me); })
      .catch(() => { clearToken(); })
      .finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const finish = useCallback((payload) => {
    setToken(payload.access_token);
    setUser(payload.user);
    return payload.user;
  }, []);

  const value = useMemo(() => ({
    user,
    checking,
    isAdmin: user?.role === "admin",
    login: async (email, password) => finish(await apiLogin(email, password)),
    register: async (email, password) => finish(await apiRegister(email, password)),
    logout: () => { clearToken(); setUser(null); },
  }), [user, checking, finish]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
