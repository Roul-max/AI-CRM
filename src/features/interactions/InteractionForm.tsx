import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../../store/index';
import { saveInteraction, clearInteractionData, updateField, InteractionData } from '../../store/interactionSlice';
import { addToast } from '../../store/slices/uiSlice';
import {
  Loader2, Save, Trash2, Sparkles, User, Building2, Stethoscope,
  Calendar, Clock, Users, Package, BookOpen, FlaskConical,
  TrendingUp, AlertTriangle, FileText, CheckSquare, ChevronDown, Target,
} from 'lucide-react';
import { cn } from '../../lib/utils';

/* ─── Input base — Stripe-quality ──────────────────────────────────────── */
const INPUT =
  'w-full rounded-md border bg-white px-3 py-[7px] text-[13px] text-zinc-800 leading-5 ' +
  'placeholder:text-zinc-300 outline-none transition-all duration-100 ' +
  'border-zinc-200 hover:border-zinc-300 ' +
  'focus:border-[var(--brand)] focus:ring-2 focus:ring-[var(--brand-ring)]';

const LABEL = 'block text-[11px] font-medium text-zinc-400 mb-1 tracking-wide uppercase select-none';

/* ─── Semantic badge maps ───────────────────────────────────────────────── */
const SENTIMENT: Record<string, { pill: string; dot: string }> = {
  Positive: { pill: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: '#16a34a' },
  Neutral:  { pill: 'bg-amber-50 text-amber-700 border-amber-200',       dot: '#d97706' },
  Negative: { pill: 'bg-red-50 text-red-700 border-red-200',             dot: '#dc2626' },
};
const RISK: Record<string, { pill: string; dot: string }> = {
  Low:    { pill: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: '#16a34a' },
  Medium: { pill: 'bg-amber-50 text-amber-700 border-amber-200',       dot: '#d97706' },
  High:   { pill: 'bg-red-50 text-red-700 border-red-200',             dot: '#dc2626' },
};

/* ─── Skeleton ──────────────────────────────────────────────────────────── */
const Skel = ({ h = 'h-8', w = 'w-full' }: { h?: string; w?: string }) => (
  <div className={cn('rounded-md shimmer', h, w)} />
);

const FormSkeleton: React.FC = () => (
  <div className="px-5 py-5 space-y-px fade-in">
    {[
      { label: true, fields: 2 },
      { label: true, fields: 3 },
      { label: true, fields: 2 },
      { label: true, fields: 2 },
    ].map((s, i) => (
      <div key={i} style={{ paddingBottom: 20, marginBottom: 20, borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
        <Skel h="h-3" w="w-20" />
        <div className="mt-3 space-y-2.5">
          {i === 0 ? (
            <div className="grid grid-cols-2 gap-3">
              <Skel /><Skel />
            </div>
          ) : null}
          {Array.from({ length: i === 0 ? 1 : s.fields }).map((_, j) => (
            <Skel key={j} h={j === s.fields - 1 && i > 1 ? 'h-16' : 'h-8'} />
          ))}
        </div>
      </div>
    ))}
  </div>
);

/* ─── Field primitives ──────────────────────────────────────────────────── */
const Field = ({
  icon: Icon, label, fieldKey, value, placeholder, type = 'text',
}: {
  icon?: React.ElementType; label: string; fieldKey: keyof InteractionData;
  value?: string | number | null; placeholder?: string; type?: string;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  return (
    <div>
      <label className={LABEL}>
        {Icon && <Icon className="inline w-2.5 h-2.5 mr-1 opacity-60" />}
        {label}
      </label>
      <input
        type={type}
        className={INPUT}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(e) => {
          const raw = e.target.value;
          const val = type === 'number' ? (raw === '' ? null : Number(raw)) : (raw || null);
          dispatch(updateField({ key: fieldKey, value: val as any }));
        }}
      />
    </div>
  );
};

const FieldArea = ({
  icon: Icon, label, fieldKey, value, rows = 3, placeholder,
}: {
  icon?: React.ElementType; label: string; fieldKey: keyof InteractionData;
  value?: string | null; rows?: number; placeholder?: string;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  return (
    <div>
      <label className={LABEL}>
        {Icon && <Icon className="inline w-2.5 h-2.5 mr-1 opacity-60" />}
        {label}
      </label>
      <textarea
        rows={rows}
        className={cn(INPUT, 'resize-none leading-relaxed')}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(e) => dispatch(updateField({ key: fieldKey, value: e.target.value || null }))}
      />
    </div>
  );
};

const FieldList = ({
  icon: Icon, label, fieldKey, items, placeholder,
}: {
  icon?: React.ElementType; label: string; fieldKey: keyof InteractionData;
  items?: string[] | null; placeholder?: string;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  return (
    <div>
      <label className={LABEL}>
        {Icon && <Icon className="inline w-2.5 h-2.5 mr-1 opacity-60" />}
        {label}
      </label>
      <input
        type="text"
        className={INPUT}
        value={items ? items.join(', ') : ''}
        placeholder={placeholder}
        onChange={(e) => {
          const arr = e.target.value
            ? e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
            : [];
          dispatch(updateField({ key: fieldKey, value: arr }));
        }}
      />
      {items && items.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {items.map((tag) => (
            <span
              key={tag}
              className="slide-up inline-flex items-center rounded-md border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[11px] font-medium text-zinc-600"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const FieldSelect = ({
  icon: Icon, label, fieldKey, value, options, colorMap,
}: {
  icon?: React.ElementType; label: string; fieldKey: keyof InteractionData;
  value?: string | null; options: string[];
  colorMap?: Record<string, { pill: string; dot: string }>;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const style = value && colorMap ? colorMap[value] : null;
  return (
    <div>
      <label className={LABEL}>
        {Icon && <Icon className="inline w-2.5 h-2.5 mr-1 opacity-60" />}
        {label}
      </label>
      <div className="relative">
        <select
          className={cn(INPUT, 'appearance-none pr-7 cursor-pointer')}
          value={value ?? ''}
          onChange={(e) => dispatch(updateField({ key: fieldKey, value: e.target.value || null }))}
        >
          <option value="">Select…</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-400" />
      </div>
      {style && value && (
        <span className={cn('inline-flex items-center gap-1.5 mt-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium slide-up', style.pill)}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: style.dot, display: 'inline-block', flexShrink: 0 }} />
          {value}
        </span>
      )}
    </div>
  );
};

const FieldCheck = ({
  label, fieldKey, checked,
}: {
  label: string; fieldKey: keyof InteractionData; checked: boolean;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none group">
      <div
        className={cn(
          'w-[15px] h-[15px] rounded-[4px] border flex items-center justify-center transition-all duration-100 shrink-0',
          checked
            ? 'bg-[var(--brand)] border-[var(--brand)]'
            : 'bg-white border-zinc-300 group-hover:border-zinc-400'
        )}
        onClick={() => dispatch(updateField({ key: fieldKey, value: !checked }))}
      >
        {checked && (
          <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
            <path d="M1.5 4.5l2 2 4-4" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      <input type="checkbox" className="sr-only" checked={checked}
        onChange={(e) => dispatch(updateField({ key: fieldKey, value: e.target.checked }))} />
      <span className="text-[12px] text-zinc-600 group-hover:text-zinc-800 transition-colors">{label}</span>
    </label>
  );
};

/* ─── Section — Linear-style: label + divider, no card chrome ──────────── */
const Section = ({
  title, children,
}: {
  title: string; children: React.ReactNode;
}) => (
  <div style={{ paddingBottom: 20, marginBottom: 4 }}>
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      marginBottom: 12,
    }}>
      <span style={{
        fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
        textTransform: 'uppercase', color: 'var(--t4)',
        whiteSpace: 'nowrap',
      }}>
        {title}
      </span>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
    <div className="space-y-3">{children}</div>
  </div>
);

/* ─── Empty state ───────────────────────────────────────────────────────── */
const EmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center h-full py-16 px-8 text-center select-none fade-in">
    {/* Icon */}
    <div style={{
      width: 40, height: 40, borderRadius: 10,
      background: 'var(--surface-3)',
      border: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      marginBottom: 16,
    }}>
      <Sparkles style={{ width: 18, height: 18, color: 'var(--brand)' }} />
    </div>

    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--t2)', marginBottom: 6 }}>
      No interaction logged yet
    </p>
    <p style={{ fontSize: 12, color: 'var(--t4)', lineHeight: 1.6, maxWidth: 220, marginBottom: 20 }}>
      Describe your HCP meeting in the chat — the form fills automatically.
    </p>

    {/* Hint list */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%', maxWidth: 240 }}>
      {[
        ['Log a new interaction', '→ describe the meeting'],
        ['Search an HCP', '→ "Search Dr. Patel"'],
        ['Get a summary', '→ "Summarise this meeting"'],
      ].map(([action, hint]) => (
        <div key={action} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '6px 10px', borderRadius: 6,
          border: '1px solid var(--border)',
          background: 'var(--surface)',
        }}>
          <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--t3)' }}>{action}</span>
          <span style={{ fontSize: 10, color: 'var(--t4)' }}>{hint}</span>
        </div>
      ))}
    </div>
  </div>
);

/* ─── Main component ────────────────────────────────────────────────────── */
const InteractionForm: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { data, saveStatus, saveError } = useSelector((state: RootState) => state.interaction);
  const isExtracting = useSelector((state: RootState) => state.ui.isExtracting);
  const isEmpty = !data.hcp_name;

  useEffect(() => {
    if (saveStatus === 'succeeded') {
      dispatch(addToast({ type: 'success', message: 'Interaction saved to database.' }));
    } else if (saveStatus === 'failed') {
      dispatch(addToast({ type: 'error', message: typeof saveError === 'string' ? saveError : 'Save failed. Please try again.' }));
    }
  }, [saveStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const filledCount = Object.values(data).filter((v) =>
    v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0)
  ).length;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0,
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      boxShadow: 'var(--shadow-sm)',
      overflow: 'hidden',
    }}>

      {/* ── Header ── */}
      <div style={{
        flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
      }}>
        <div>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', margin: 0, letterSpacing: '-0.01em' }}>
            Interaction Details
          </h2>
          <p style={{ fontSize: 11, color: 'var(--t4)', margin: '2px 0 0', fontWeight: 400 }}>
            AI-populated · editable before saving
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isExtracting && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              padding: '3px 8px', borderRadius: 99,
              border: '1px solid #ddd6fe',
              background: '#f5f3ff',
              fontSize: 11, fontWeight: 500, color: '#7c3aed',
            }}>
              <Loader2 style={{ width: 10, height: 10, animation: 'spin 1s linear infinite' }} />
              Extracting
            </span>
          )}
          {!isEmpty && !isExtracting && (
            <span className="slide-up" style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              padding: '3px 8px', borderRadius: 99,
              border: '1px solid var(--border)',
              background: 'var(--surface-3)',
              fontSize: 11, fontWeight: 500, color: 'var(--t3)',
            }}>
              <Sparkles style={{ width: 10, height: 10, color: 'var(--brand)' }} />
              {filledCount} fields extracted
            </span>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {isExtracting ? (
          <FormSkeleton />
        ) : isEmpty ? (
          <EmptyState />
        ) : (
          <div style={{ padding: '20px 20px 8px' }}>
              <Section title="Healthcare Professional">
                <div className="grid grid-cols-2 gap-3">
                  <Field icon={User}        label="HCP Name"       fieldKey="hcp_name"       value={data.hcp_name}       placeholder="Dr. Sarah Chen" />
                  <Field icon={Stethoscope} label="Specialization" fieldKey="specialization" value={data.specialization} placeholder="Cardiologist" />
                </div>
                <Field icon={Building2} label="Hospital / Clinic" fieldKey="hospital" value={data.hospital} placeholder="City General Hospital" />
              </Section>

              <Section title="Meeting Details">
                <div className="grid grid-cols-2 gap-3">
                  <FieldSelect
                    icon={FileText}
                    label="Type"
                    fieldKey="interaction_type"
                    value={data.interaction_type}
                    options={['In-person', 'Virtual', 'Phone Call', 'Conference', 'Email']}
                  />
                  <Field icon={Calendar} label="Date" fieldKey="interaction_date" value={data.interaction_date} type="date" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field icon={Clock} label="Duration (mins)" fieldKey="duration" value={data.duration} type="number" placeholder="30" />
                  <FieldList icon={Users} label="Attendees" fieldKey="attendees" items={data.attendees} placeholder="Names, comma-separated" />
                </div>
              </Section>

              <Section title="Topics & Materials">
                <FieldList icon={Package}  label="Products Discussed" fieldKey="products_discussed" items={data.products_discussed} placeholder="CardioX, MetaboPlus…" />
                <FieldList icon={BookOpen} label="Materials Shared"   fieldKey="shared_materials"   items={data.shared_materials}   placeholder="Brochure, Clinical study…" />
                <div className="flex items-center gap-5 pt-0.5">
                  <FieldCheck label="Samples distributed" fieldKey="samples_requested" checked={!!data.samples_requested} />
                  <FieldCheck label="Brochure shared"     fieldKey="brochure_shared"   checked={!!data.brochure_shared} />
                </div>
              </Section>

              <Section title="Assessment">
                <div className="grid grid-cols-2 gap-3">
                  <FieldSelect icon={TrendingUp}    label="Sentiment"  fieldKey="sentiment" value={data.sentiment} options={['Positive', 'Neutral', 'Negative']} colorMap={SENTIMENT} />
                  <FieldSelect icon={AlertTriangle} label="Risk Level" fieldKey="risk"      value={data.risk}      options={['Low', 'Medium', 'High']}            colorMap={RISK} />
                </div>
                <Field icon={FlaskConical} label="Competitor Mentioned" fieldKey="competitor_mentioned" value={data.competitor_mentioned} placeholder="e.g. CompetitorX" />
              </Section>

              <Section title="Outcomes & Follow-up">
                <FieldArea icon={CheckSquare} label="Outcomes"          fieldKey="outcomes"       value={data.outcomes}       rows={2} placeholder="Key outcomes from this meeting…" />
                <FieldArea icon={FileText}    label="Summary"           fieldKey="summary"        value={data.summary}        rows={3} placeholder="Meeting summary…" />
                <FieldList icon={Target}      label="Follow-up Actions" fieldKey="action_items"   items={data.action_items}   placeholder="Send report, Schedule demo…" />
                <Field     icon={Calendar}    label="Follow-up Date"    fieldKey="follow_up_date" value={data.follow_up_date} type="date" />
              </Section>
          </div>
        )}
      </div>

      {/* ── Footer — sticky save bar ── */}
      <div style={{
        flexShrink: 0,
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 20px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
      }}>
        <span style={{ flex: 1, fontSize: 11, color: 'var(--t4)' }}>
          {isEmpty
            ? 'Use the AI chat to auto-fill this form'
            : `${filledCount} of ${Object.keys(data).length} fields populated`}
        </span>

        <button
          onClick={() => dispatch(clearInteractionData())}
          disabled={saveStatus === 'loading' || isExtracting}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '5px 12px', borderRadius: 6,
            border: '1px solid var(--border)',
            background: 'var(--surface)',
            fontSize: 12, fontWeight: 500, color: 'var(--t3)',
            cursor: 'pointer', transition: 'all .1s',
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-3)'; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface)'; }}
        >
          <Trash2 style={{ width: 12, height: 12 }} />
          Clear
        </button>

        <button
          onClick={() => dispatch(saveInteraction(data))}
          disabled={!data.hcp_name || saveStatus === 'loading' || isExtracting}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '5px 14px', borderRadius: 6,
            background: data.hcp_name ? 'var(--brand)' : 'var(--surface-4)',
            border: '1px solid transparent',
            fontSize: 12, fontWeight: 600,
            color: data.hcp_name ? '#fff' : 'var(--t4)',
            cursor: data.hcp_name ? 'pointer' : 'not-allowed',
            transition: 'all .1s',
            boxShadow: data.hcp_name ? '0 1px 3px rgba(91,91,214,.3)' : 'none',
          }}
          onMouseEnter={(e) => { if (data.hcp_name) (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-hover)'; }}
          onMouseLeave={(e) => { if (data.hcp_name) (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand)'; }}
        >
          {saveStatus === 'loading'
            ? <Loader2 style={{ width: 12, height: 12, animation: 'spin 1s linear infinite' }} />
            : <Save style={{ width: 12, height: 12 }} />}
          Save Interaction
        </button>
      </div>

    </div>
  );
};

export default InteractionForm;
