'use client';

import { useState } from 'react';

interface CopyButtonProps {
  value: string;
}

export function CopyButton({ value }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      // ignore
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-xs rounded-full border border-white/20 px-3 py-1 text-slate-200 hover:border-white/40 transition"
    >
      {copied ? 'Zkopírováno ✔' : 'Kopírovat'}
    </button>
  );
}
