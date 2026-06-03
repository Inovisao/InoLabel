import NavSidebar from "./NavSidebar";
import WizardTopbar from "./WizardTopbar";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
  breadcrumb?: string;
  children: React.ReactNode;
}

export default function PageShell({ activeNav, onNavigate, breadcrumb, children }: Props) {
  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <NavSidebar activeItem={activeNav} onNavigate={onNavigate} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <WizardTopbar breadcrumb={breadcrumb} />
        <main
          style={{
            flex: 1,
            overflow: "auto",
            padding: "32px",
            background: "var(--color-bg)",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
