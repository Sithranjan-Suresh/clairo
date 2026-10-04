import { Brain, FileText, ClipboardList, BarChart3, Database, Table2, Library, ShieldCheck } from "lucide-react";
import { BrandMark } from "./BrandMark";
import { useAuth } from "../auth/AuthContext";

const DOCK_ITEMS = [
  { id: "Clairo.AI",           icon: Brain,         label: "CLΔIRO" },
  { id: "Claims",              icon: Table2,        label: "Claims" },
  { id: "Appeal Letter",       icon: FileText,      label: "Appeal Letter" },
  { id: "Prior Authorization", icon: ClipboardList, label: "Prior Auth" },
  { id: "Analytics",           icon: BarChart3,     label: "Analytics" },
  { id: "Policies",            icon: Library,       label: "Policies" },
  { id: "InsForge",            icon: Database,      label: "InsForge DB" },
  { id: "Audit Log",           icon: ShieldCheck,   label: "Audit Log", adminOnly: true },
];

export default function TopDockNav({ activeTab, setActiveTab, hasClaim }) {
  const { isAdmin } = useAuth();
  const items = DOCK_ITEMS.filter((item) => !item.adminOnly || isAdmin);
  return (
    <nav className="top-dock font-ui" aria-label="Main navigation">
      <div className="top-dock__inner glass-panel">
        {items.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={`top-dock__item ${isActive ? "top-dock__item--active" : ""}`}
              onClick={() => setActiveTab(item.id)}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={14} aria-hidden="true" className="top-dock__icon" />
              <span className="top-dock__label">
                {item.id === "Clairo.AI" ? (
                  <BrandMark className="top-dock__brand" />
                ) : (
                  item.label
                )}
              </span>
              {item.id === "Clairo.AI" && hasClaim && (
                <span className="top-dock__dot" title="Claim loaded" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
