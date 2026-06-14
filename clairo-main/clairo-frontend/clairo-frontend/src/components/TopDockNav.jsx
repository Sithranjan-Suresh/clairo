import { Brain, FileText, ClipboardList, BarChart3, Database } from "lucide-react";
import { BrandMark } from "./BrandMark";

const DOCK_ITEMS = [
  { id: "Clairo.AI",           icon: Brain,         label: "CLΔIRO" },
  { id: "Appeal Letter",       icon: FileText,      label: "Appeal Letter" },
  { id: "Prior Authorization", icon: ClipboardList, label: "Prior Auth" },
  { id: "Analytics",           icon: BarChart3,     label: "Analytics" },
  { id: "InsForge",            icon: Database,      label: "InsForge DB" },
];

export default function TopDockNav({ activeTab, setActiveTab, hasClaim }) {
  return (
    <nav className="top-dock font-ui" aria-label="Main navigation">
      <div className="top-dock__inner glass-panel">
        {DOCK_ITEMS.map((item) => {
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
