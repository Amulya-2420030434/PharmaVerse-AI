import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { Camera, CameraOff } from "lucide-react";

import { parseQrPayload } from "../../utils/qrPayload";

export default function QrScanner({ onScan }) {
  const videoRef = useRef(null);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const toggleScanner = () => {
    if (scanning) {
      setScanning(false);
      setMessage("");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera scanning is unavailable in this browser. Enter an ID manually.");
      return;
    }
    setError("");
    setMessage("Requesting camera access…");
    setScanning(true);
  };

  useEffect(() => {
    if (!scanning) return undefined;
    let mounted = true;
    let controls;
    const reader = new BrowserMultiFormatReader();

    reader
      .decodeFromVideoDevice(undefined, videoRef.current, (result) => {
        if (!mounted || !result) return;
        const text = result.getText();
        const parsed = parseQrPayload(text);
        if (!parsed) {
          setError("This QR code is not a supported PharmaVerse verification payload.");
          setMessage("");
          return;
        }
        onScan(parsed);
        setError("");
        setMessage("QR payload recognized. Review the populated identifier and verify.");
        setScanning(false);
      })
      .then((cameraControls) => {
        controls = cameraControls;
        if (mounted) setMessage("Camera active. Hold a QR code inside the frame.");
        else cameraControls.stop();
      })
      .catch((scanError) => {
        if (!mounted) return;
        // ZXing NotFoundException is a normal unsuccessful frame scan, not a
        // fatal scanner error — keep scanning and do not surface it to the user.
        if (scanError?.name === "NotFoundException") {
          return;
        }
        const denied = scanError?.name === "NotAllowedError" || scanError?.name === "SecurityError";
        setError(
          denied
            ? "Camera permission was denied. Allow camera access or enter an ID manually."
            : "No usable camera was found. Enter an ID manually.",
        );
        setMessage("");
        setScanning(false);
      });

    return () => {
      mounted = false;
      controls?.stop();
    };
  }, [scanning, onScan]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-[#102a43]">Scan a medicine QR</h2>
          <p className="mt-1 text-sm text-slate-600">
            Camera frames are decoded in-browser and are not uploaded or stored.
          </p>
        </div>
        <button
          type="button"
          onClick={toggleScanner}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-[#5a1725]"
        >
          {scanning ? <CameraOff size={16} /> : <Camera size={16} />}
          {scanning ? "Stop camera" : "Start camera"}
        </button>
      </div>
      {scanning && (
        <div className="mt-4 max-w-md overflow-hidden rounded-xl bg-slate-950">
          <video ref={videoRef} className="aspect-square w-full object-cover" muted playsInline />
        </div>
      )}
      {message && <p className="mt-3 text-sm text-slate-600">{message}</p>}
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    </section>
  );
}
