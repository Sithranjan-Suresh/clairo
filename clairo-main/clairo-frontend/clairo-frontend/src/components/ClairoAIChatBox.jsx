import { useRef, useState, useCallback, useEffect } from "react";
import { Paperclip, Send, X } from "lucide-react";
import { BrandMark } from "./BrandMark";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/csv",
  "application/csv",
];

const ACCEPT_ATTR =
  ".pdf,.png,.jpg,.jpeg,.txt,.docx,.csv,application/pdf,image/png,image/jpeg,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/csv";

function isAccepted(file) {
  if (ACCEPTED_TYPES.includes(file.type)) return true;
  const ext = file.name.split(".").pop()?.toLowerCase();
  return ["pdf", "png", "jpg", "jpeg", "txt", "docx", "csv"].includes(ext ?? "");
}

export default function ClairoAIChatBox({
  onSubmit,
  loading = false,
  messages = [],
}) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [text, resizeTextarea]);

  function addFiles(fileList) {
    const incoming = Array.from(fileList).filter(isAccepted);
    if (!incoming.length) return;
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      const merged = [...prev];
      incoming.forEach((f) => {
        if (!names.has(f.name)) merged.push(f);
      });
      return merged;
    });
  }

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e) {
    e?.preventDefault();
    if (loading) return;
    const trimmed = text.trim();
    if (!trimmed && files.length === 0) return;

    onSubmit?.({ text: trimmed, files: [...files] });
    setText("");
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <div className="clairo-chat glass-panel">
      <p className="clairo-chat__heading">
        Ask <BrandMark /> about your denial
      </p>

      {messages.length > 0 && (
        <ul className="clairo-chat__messages">
          {messages.map((msg, i) => (
            <li key={i} className={`clairo-chat__msg clairo-chat__msg--${msg.role}`}>
              {msg.content}
            </li>
          ))}
        </ul>
      )}

      <form className="clairo-chat__form" onSubmit={handleSubmit}>
        <div className="clairo-chat__input-wrap">
          <textarea
            ref={textareaRef}
            className="clairo-chat__textarea"
            placeholder="Upload a denial file or ask CLΔIRO what to extract..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <div className="clairo-chat__actions">
            <button
              type="button"
              className="clairo-chat__icon-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              aria-label="Attach file"
            >
              <Paperclip size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPT_ATTR}
              multiple
              className="clairo-chat__file-input"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = "";
              }}
            />
            <button
              type="submit"
              className="clairo-chat__send"
              disabled={loading || (!text.trim() && files.length === 0)}
              aria-label="Send"
            >
              <Send size={18} />
            </button>
          </div>
        </div>

        {files.length > 0 && (
          <ul className="clairo-chat__files">
            {files.map((file, index) => (
              <li key={`${file.name}-${index}`} className="clairo-chat__file">
                <span className="clairo-chat__file-name">{file.name}</span>
                <button
                  type="button"
                  className="clairo-chat__file-remove"
                  onClick={() => removeFile(index)}
                  aria-label={`Remove ${file.name}`}
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </form>
    </div>
  );
}
