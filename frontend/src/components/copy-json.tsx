import { useState } from 'react';

type Props = {
  value: unknown;
  label?: string;
};

export function CopyJson({ value, label = 'Copy' }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const text = JSON.stringify(value, null, 2);
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (error) {
      console.error('Copy failed', error);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-slate-200 hover:border-white/25 transition"
      title={copied ? 'Zkopírováno' : 'Kopírovat JSON'}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>{copied ? 'Zkopírováno' : label}</span>
    </button>
  );
}
