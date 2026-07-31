import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWebSocketStatus } from '../hooks/useWebSocketStatus';
import {
  LayoutDashboard,
  Network,
  ListFilter,
  ShieldAlert,
  LogOut,
  Wifi,
  WifiOff,
  Activity,
  Bell,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, isAdmin, logout } = useAuth();
  const { connectionStatus } = useWebSocketStatus();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <Activity className="brand-icon" />
          <span className="brand-title">InfraTopology</span>
          <span className="brand-badge">MVP</span>
        </div>

        <div className="navbar-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <LayoutDashboard className="nav-icon" />
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/topology" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <Network className="nav-icon" />
            <span>Topology</span>
          </NavLink>

          <NavLink to="/inventory" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <ListFilter className="nav-icon" />
            <span>Inventory</span>
          </NavLink>

          <NavLink to="/alerts" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            <Bell className="nav-icon" />
            <span>Alerts</span>
          </NavLink>

          {isAdmin && (
            <NavLink to="/admin" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              <ShieldAlert className="nav-icon" />
              <span>Administration</span>
            </NavLink>
          )}
        </div>

        <div className="navbar-status">
          <div className={`ws-badge ${connectionStatus}`}>
            {connectionStatus === 'connected' ? (
              <>
                <Wifi className="ws-icon" />
                <span>Live WS</span>
              </>
            ) : (
              <>
                <WifiOff className="ws-icon" />
                <span>{connectionStatus}</span>
              </>
            )}
          </div>

          {user && (
            <div className="user-profile">
              <div className="user-info">
                <span className="user-name">{user.username}</span>
                <span className={`role-pill ${user.role}`}>{user.role}</span>
              </div>
              <button onClick={handleLogout} className="btn-logout" title="Sign out" aria-label="Sign out">
                <LogOut className="logout-icon" />
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
