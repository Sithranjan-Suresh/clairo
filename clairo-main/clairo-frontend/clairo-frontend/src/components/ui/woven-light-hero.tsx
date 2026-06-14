import { useEffect } from "react";
import { motion, useAnimation } from "framer-motion";
import { BrandMark } from "@/components/BrandMark";
import ClairoLogo from "@/components/ClairoLogo";
import { ParticleWave } from "@/components/ui/particle-wave";

const BRAND_TEXT = "#CBD5E1";

const SUBHEADLINE_PHRASES = [
  "Autonomous AI agent orchestration",
  "for healthcare insurance denials.",
  "Built on InsForge's agent-native cloud database",
  "with Groq LLMs.",
];

export interface WovenLightHeroProps {
  onExplore?: () => void;
}

export function WovenLightHero({ onExplore }: WovenLightHeroProps) {
  const textControls = useAnimation();
  const buttonControls = useAnimation();

  useEffect(() => {
    textControls.start((i) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: (i as number) * 0.1 + 1.5,
        duration: 1.2,
        ease: [0.2, 0.65, 0.3, 0.9],
      },
    }));
    buttonControls.start({
      opacity: 1,
      transition: { delay: 2.5, duration: 1 },
    });
  }, [textControls, buttonControls]);

  return (
    <div className="relative flex h-screen w-full flex-col overflow-hidden bg-black">
      <div className="absolute inset-0 z-0">
        <ParticleWave className="h-full w-full" />
      </div>

      <div className="pointer-events-none absolute left-1/2 top-4 z-20 -translate-x-1/2">
        <div className="font-ui inline-flex items-center rounded-full border border-white/10 bg-white/0 px-3 py-1 backdrop-blur-sm">
          <span className="text-[11px] font-medium tracking-[0.18em] text-slate-300/70">
            INSFORGE HACKATHON SUBMISSION
          </span>
        </div>
      </div>

      <HeroNav />

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex flex-col items-center gap-[2.5rem] text-center md:gap-[3.5rem]">
          <h1
            className="woven-hero__headline font-display translate-y-4 text-6xl italic md:text-8xl"
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontStyle: "italic",
              textShadow: "0 0 50px rgba(203, 213, 225, 0.35)",
            }}
          >
            <span className="brand-mark woven-hero__brand-mark">
              <motion.span
                className="brand-mark__text"
                custom={0}
                initial={{ opacity: 0, y: 50 }}
                animate={textControls}
              >
                CL
              </motion.span>
              <motion.span
                custom={1}
                initial={{ opacity: 0, y: 50 }}
                animate={textControls}
                className="brand-mark__logo-wrap"
              >
                <ClairoLogo inline />
              </motion.span>
              <motion.span
                className="brand-mark__text"
                custom={2}
                initial={{ opacity: 0, y: 50 }}
                animate={textControls}
              >
                IRO
              </motion.span>
            </span>
          </h1>

          <div
            className="relative flex w-full flex-col items-center rounded-3xl bg-[radial-gradient(circle,_rgba(0,0,0,0.75)_0%,_transparent_75%)] px-2 py-2"
          >
            <p className="font-body mx-auto max-w-2xl text-base font-normal leading-relaxed text-slate-300 md:text-lg">
              {SUBHEADLINE_PHRASES.map((phrase, index) => (
                <motion.span
                  key={phrase}
                  custom={3 + index}
                  initial={{ opacity: 0, y: 50 }}
                  animate={textControls}
                  className="inline-block"
                >
                  {phrase}
                  {index < SUBHEADLINE_PHRASES.length - 1 ? " " : ""}
                </motion.span>
              ))}
            </p>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={buttonControls}>
            <div className="mt-0 flex flex-col items-center gap-4">
              <button
                type="button"
                onClick={onExplore}
                className="font-ui inline-flex min-h-[3.75rem] w-full max-w-[360px] items-center justify-center gap-2.5 rounded-full border-2 border-[#CBD5E1]/35 bg-[#CBD5E1]/10 px-14 py-5 text-lg font-semibold backdrop-blur-sm transition-all hover:border-[#CBD5E1]/55 hover:bg-[#CBD5E1]/20 hover:shadow-[0_0_32px_rgba(203,213,225,0.18)] active:scale-[0.99] md:min-h-[4.25rem] md:gap-3 md:px-20 md:py-6 md:text-xl"
                style={{ color: BRAND_TEXT }}

              >
                <span className="flex items-center justify-center gap-2">
                  Explore <BrandMark className="woven-hero__brand-mark" />
                  <span className="inline-flex items-center text-white/80 transition-all group-hover:translate-x-0.5">
                    →
                  </span>
                </span>
              </button>

              <div className="mt-2 flex w-full max-w-4xl flex-wrap items-center justify-center rounded-full border border-white/10 bg-black/40 px-4 py-2 text-center backdrop-blur-sm">
                <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2">
                  {[
                    "⚡ InsForge Persistent DB",
                    "📄 RAG PDF Extraction",
                    "🤖 7 MCP Agent Tools",
                  ].map((label, idx) => (
                    <div
                      key={label}
                      className="flex items-center gap-3 rounded-full border border-white/5 bg-white/0 px-3 py-1 backdrop-blur-sm"
                    >
                      <span className="font-ui text-[11px] font-medium tracking-[0.02em] text-slate-300/80">
                        {label}
                      </span>
                      {idx !== 2 && (
                        <span className="text-[12px] text-slate-500/70">•</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

const HeroNav = () => {
  return (
    <motion.nav
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { delay: 1, duration: 1 } }}
      className="font-ui absolute top-0 right-0 left-0 z-20 p-6"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-2">
          <BrandMark className="woven-hero__brand-mark text-xl font-bold" />
        </div>
      </div>
    </motion.nav>
  );
};
