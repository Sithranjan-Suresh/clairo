import { useState, useRef } from "react";
import { uploadDenial } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";

export default function UploadPanel({ onResult }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file || file.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }
    setFileName(file.name);
    setError(null);
    setLoading(true);
    try {
      const data = await uploadDenial(file);
      onResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  return (
    <div className="panel">
      <SectionHeader icon="📄" title="Upload Denial Document" subtitle="PDF denial letters, ERA files, or EOB documents" />

      <div
        className={`drop-zone ${dragging ? "drop-zone--active" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {loading ? (
          <div className="drop-inner">
            <Spinner size={28} />
            <span>Processing denial document…</span>
          </div>
        ) : (
          <div className="drop-inner">
            <span className="drop-icon">⬆</span>
            <span className="drop-text">
              {fileName ? fileName : "Drag & drop a PDF, or click to browse"}
            </span>
            <span className="drop-sub">CLAIRO will extract all claim fields automatically</span>
          </div>
        )}
      </div>

      <ErrorBox message={error} />
    </div>
  );
}
