import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../../store/index';
import { removeToast } from '../../store/slices/uiSlice';
import { CheckCircle2, XCircle, X } from 'lucide-react';

const AUTO_DISMISS_MS = 4500;

const ToastContainer: React.FC = () => {
  const toasts = useSelector((state: RootState) => state.ui.toasts);
  const dispatch = useDispatch<AppDispatch>();
  return (
    <div style={{
      position: 'fixed', bottom: 20, right: 20,
      zIndex: 9999,
      display: 'flex', flexDirection: 'column', gap: 8,
      pointerEvents: 'none',
    }}>
      {toasts.map((t) => (
        <ToastItem
          key={t.id}
          type={t.type}
          message={t.message}
          onDismiss={() => dispatch(removeToast(t.id))}
        />
      ))}
    </div>
  );
};

const ToastItem: React.FC<{
  type: 'success' | 'error'; message: string; onDismiss: () => void;
}> = ({ type, message, onDismiss }) => {
  const [visible, setVisible] = useState(false);
  const ok = type === 'success';

  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 180);
    }, AUTO_DISMISS_MS);
    return () => { cancelAnimationFrame(raf); clearTimeout(t); };
  }, [onDismiss]);

  return (
    <div
      style={{
        pointerEvents: 'auto',
        display: 'flex', alignItems: 'flex-start', gap: 10,
        padding: '12px 14px',
        minWidth: 280, maxWidth: 360,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${ok ? '#16a34a' : '#dc2626'}`,
        borderRadius: 8,
        boxShadow: '0 4px 16px rgba(0,0,0,.1), 0 1px 4px rgba(0,0,0,.06)',
        transition: 'opacity .18s ease, transform .18s ease',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        position: 'relative', overflow: 'hidden',
      }}
    >
      {/* Icon */}
      {ok
        ? <CheckCircle2 style={{ width: 15, height: 15, color: '#16a34a', flexShrink: 0, marginTop: 1 }} />
        : <XCircle     style={{ width: 15, height: 15, color: '#dc2626', flexShrink: 0, marginTop: 1 }} />}

      {/* Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--t1)', margin: '0 0 2px' }}>
          {ok ? 'Saved' : 'Error'}
        </p>
        <p style={{ fontSize: 11, color: 'var(--t3)', margin: 0, lineHeight: 1.5 }}>{message}</p>
      </div>

      {/* Dismiss */}
      <button
        onClick={() => { setVisible(false); setTimeout(onDismiss, 180); }}
        style={{
          flexShrink: 0, width: 18, height: 18,
          border: 'none', background: 'transparent',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: 'var(--t4)',
          borderRadius: 4, transition: 'color .1s',
          padding: 0,
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--t2)'; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--t4)'; }}
      >
        <X style={{ width: 11, height: 11 }} />
      </button>

      {/* Progress bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0,
        height: 2,
        background: ok ? '#16a34a' : '#dc2626',
        opacity: .4,
        transformOrigin: 'left',
        animation: `shrink-x ${AUTO_DISMISS_MS}ms linear forwards`,
      }} />
    </div>
  );
};

export default ToastContainer;
