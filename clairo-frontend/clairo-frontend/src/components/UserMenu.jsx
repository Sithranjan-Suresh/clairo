import { LogOut, Shield } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function UserMenu() {
  const { user, isAdmin, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="user-menu glass-panel font-ui">
      {isAdmin && <Shield size={13} aria-label="Administrator" className="user-menu__admin" />}
      <span className="user-menu__email" title={user.email}>{user.email}</span>
      <button type="button" className="user-menu__logout" onClick={logout} aria-label="Sign out">
        <LogOut size={13} aria-hidden="true" /> Sign out
      </button>
    </div>
  );
}
