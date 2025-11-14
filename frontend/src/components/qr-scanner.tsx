'use client';

import { Html5QrcodeScanner, Html5QrcodeScanType } from 'html5-qrcode';
import { MutableRefObject, useEffect, useRef, useId, useMemo } from 'react';

interface Props {
  onDecode: (decodedText: string) => void;
}

export default function QrScanner({ onDecode }: Props) {
  const scannerRef: MutableRefObject<Html5QrcodeScanner | null> = useRef(null);
  const reactId = useId();
  const elementId = useMemo(() => `qr-reader-${reactId.replace(/:/g, '')}`, [reactId]);

  useEffect(() => {
    const scanner = new Html5QrcodeScanner(
      elementId,
      {
        fps: 5,
        qrbox: { width: 250, height: 250 },
        rememberLastUsedCamera: true,
        supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
      },
      false,
    );
    scannerRef.current = scanner;
    scanner.render((decodedText) => onDecode(decodedText), () => {});

    return () => {
      scanner.clear().catch(() => null);
      scannerRef.current = null;
    };
  }, [elementId, onDecode]);

  return <div id={elementId} className="w-full" />;
}
