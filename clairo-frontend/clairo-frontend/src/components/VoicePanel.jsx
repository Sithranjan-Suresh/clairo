import { useState, useRef } from "react";
import { processVoice } from "../api";
import { Spinner, ErrorBox, SectionHeader } from "./ui";

export default function VoicePanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await processVoice(file);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <SectionHeader
        icon="🎙"
        title="Voice AI"
        subtitle="Speak a command — CLAIRO transcribes, parses intent, and routes it"
      />
      <input
        ref={inputRef}
        type="file"
        accept="audio/*"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <button className="btn-primary" onClick={() => inputRef.current?.click()} disabled={loading}>
        {loading ? <><Spinner size={16} /> Processing…</> : "Upload Audio File"}
      </button>
      <ErrorBox message={error} />
      {result && (
        <div className="appeal-meta" style={{ marginTop: "1rem" }}>
          <div className="field-row">
            <span className="field-label">Transcript</span>
            <span className="field-value">{result.transcript}</span>
          </div>
          <div className="field-row">
            <span className="field-label">Intent Detected</span>
            <span className="field-value tag">{result.intent}</span>
          </div>
          {result.voice_response && (
            <div className="field-row">
              <span className="field-label">Response</span>
              <span className="field-value">{result.voice_response}</span>
            </div>
          )}
          {result.result && (
            <pre className="letter-box" style={{ marginTop: "0.5rem" }}>
              {JSON.stringify(result.result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}