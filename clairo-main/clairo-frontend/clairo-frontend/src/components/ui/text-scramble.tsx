import { useState, useCallback, useRef, useEffect } from "react";

const CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*";
const PRESERVE = new Set(["Δ", " "]);

interface TextScrambleProps {
  text: string;
  className?: string;
  /** `hero` — Pacifico title on shader page; `default` — mono decode label */
  variant?: "default" | "hero";
}

export function TextScramble({
  text,
  className = "",
  variant = "default",
}: TextScrambleProps) {
  const [displayText, setDisplayText] = useState(text);
  const [isHovering, setIsHovering] = useState(false);
  const [isScrambling, setIsScrambling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const frameRef = useRef(0);

  const scramble = useCallback(() => {
    setIsScrambling(true);
    frameRef.current = 0;
    const duration = text.length * 3;

    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      frameRef.current++;
      const progress = frameRef.current / duration;
      const revealedLength = Math.floor(progress * text.length);

      const newText = text
        .split("")
        .map((char, i) => {
          if (PRESERVE.has(char)) return char;
          if (i < revealedLength) return text[i];
          return CHARS[Math.floor(Math.random() * CHARS.length)];
        })
        .join("");

      setDisplayText(newText);

      if (frameRef.current >= duration) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setDisplayText(text);
        setIsScrambling(false);
      }
    }, 30);
  }, [text]);

  const handleMouseEnter = () => {
    setIsHovering(true);
    scramble();
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const isHero = variant === "hero";

  return (
    <div
      className={`group relative inline-flex flex-col select-none ${
        isHero ? "cursor-pointer" : "cursor-pointer"
      } ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span
        className={
          isHero
            ? "shader-hero__title relative inline-block text-white"
            : "relative font-mono text-lg tracking-widest uppercase"
        }
      >
        {displayText.split("").map((char, i) => {
          const isDelta = char === "Δ";
          const isUnsettled = isScrambling && char !== text[i];

          let charClass = isHero
            ? isDelta
              ? "brand-mark__delta"
              : "text-white"
            : isUnsettled
              ? "text-primary scale-110"
              : "text-foreground";

          if (isHero && isUnsettled && !isDelta) {
            charClass = "text-primary scale-110";
          }

          return (
            <span
              key={`${i}-${char}`}
              className={`inline-block transition-all duration-150 ${charClass}`}
              style={{ transitionDelay: `${i * 10}ms` }}
            >
              {char}
            </span>
          );
        })}
      </span>

      {!isHero && (
        <>
          <span className="relative mt-2 h-px w-full overflow-hidden">
            <span
              className={`absolute inset-0 origin-left bg-foreground transition-transform duration-500 ease-out ${
                isHovering ? "scale-x-100" : "scale-x-0"
              }`}
            />
            <span className="absolute inset-0 bg-border" />
          </span>
          <span
            className={`absolute -inset-4 -z-10 rounded-lg bg-primary/5 transition-opacity duration-300 ${
              isHovering ? "opacity-100" : "opacity-0"
            }`}
          />
        </>
      )}
    </div>
  );
}
