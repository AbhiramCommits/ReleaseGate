import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearToken } from "../auth";
import styles from "./AppShell.module.css";

const navItems = [
  { to: "/requests", label: "Requests", end: true },
  { to: "/requests/new", label: "New Request", end: false },
  { to: "/analytics", label: "Analytics", end: false },
];

export default function AppShell() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearToken();
    navigate("/login", { replace: true });
  };

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.brand}>ReleaseGate</span>
        <nav className={styles.nav}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? `${styles.link} ${styles.active}` : styles.link)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className={styles.logout} onClick={handleLogout} type="button">
          Log out
        </button>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
