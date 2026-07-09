import React from 'react';
import { Outlet } from 'react-router-dom';
import ToastContainer from './ui/ToastContainer';

const Layout: React.FC = () => (
  <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>

    {/* ── Header — Linear-style: clean, minimal, sticky ── */}
    <header style={{
      position: 'sticky', top: 0, zIndex: 50,
      background: 'rgba(255,255,255,0.92)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      height: 48,
    }}>
      <div style={{
        maxWidth: 1536, margin: '0 auto',
        padding: '0 20px', height: '100%',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>

        {/* Logo — simple, geometric */}
        <div style={{
          width: 24, height: 24, borderRadius: 6, flexShrink: 0,
          background: 'var(--brand)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 6h8M6 2v8" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </div>

        {/* Brand name */}
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', letterSpacing: '-0.01em' }}>
          HCP CRM
        </span>

        {/* Divider */}
        <div style={{ width: 1, height: 16, background: 'var(--border)', flexShrink: 0 }} />

        {/* Subtitle */}
        <span className="hidden sm:block" style={{ fontSize: 12, color: 'var(--t4)', fontWeight: 400 }}>
          AI Sales Intelligence
        </span>

      </div>
    </header>

    {/* ── Main ── */}
    <main
      style={{
        flex: '1 1 0',
        height: 0,
        minHeight: 0,
        overflow: 'hidden',
        maxWidth: 1536, width: '100%', margin: '0 auto',
        padding: '16px 20px',
        boxSizing: 'border-box',
      }}
    >
      <Outlet />
    </main>

    <ToastContainer />
  </div>
);

export default Layout;
