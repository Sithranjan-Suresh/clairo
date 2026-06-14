import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PATH_COUNT = 32;
const VIEWBOX = "0 0 1400 900";
const WAVE_FLOW_DURATION_S = 12;

/** Smooth cubic path through wave-offset points (uniform curvature start → end). */
function pointsToSmoothCubicPath(points: [number, number][]): string {
  if (points.length < 2) return "";
  let d = `M ${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];

    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;

    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }

  return d;
}

/**
 * Diagonal wave paths with the same sinusoidal bend at corners and center.
 * Endpoints extend past the viewBox so visible corners sit on curved segments.
 */
function buildCurvyPath(index: number, direction: 1 | -1): string {
  const segmentCount = 12;
  const amplitude = 52 + index * 2.4;
  const waveCount = 2.35 + (index % 6) * 0.1;
  const phase = index * 0.38 * direction;
  const lane = index * 8 * direction;

  const startX = -280 + lane;
  const startY = 1020 - index * 16;
  const endX = 1580 + lane;
  const endY = -200 - index * 5;

  const dx = endX - startX;
  const dy = endY - startY;
  const length = Math.hypot(dx, dy) || 1;
  const normalX = (-dy / length) * direction;
  const normalY = (dx / length) * direction;

  const points: [number, number][] = [];

  for (let i = 0; i <= segmentCount; i++) {
    const t = i / segmentCount;
    const baseX = startX + dx * t;
    const baseY = startY + dy * t;
    const wave = Math.sin(t * Math.PI * waveCount + phase) * amplitude;
    points.push([baseX + normalX * wave, baseY + normalY * wave]);
  }

  return pointsToSmoothCubicPath(points);
}

function FloatingPaths({
  direction,
  className,
}: {
  direction: 1 | -1;
  className?: string;
}) {
  const paths = Array.from({ length: PATH_COUNT }, (_, i) => ({
    id: i,
    d: buildCurvyPath(i, direction),
    width: 0.55 + i * 0.028,
    opacity: 0.24 + i * 0.012,
    delay: `${-((i / PATH_COUNT) * WAVE_FLOW_DURATION_S).toFixed(3)}s`,
  }));

  return (
    <svg
      className={cn("h-full w-full", className)}
      viewBox={VIEWBOX}
      fill="none"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <title>Background paths</title>
      {paths.map((path) => (
        <path
          key={path.id}
          d={path.d}
          className="wave-path"
          pathLength={100}
          strokeWidth={path.width}
          strokeOpacity={path.opacity}
          style={{ animationDelay: path.delay }}
        />
      ))}
    </svg>
  );
}

function WavyPathsCorner({ mirrored }: { mirrored?: boolean }) {
  return (
    <div
      className={cn(
        "absolute inset-0",
        mirrored && "scale-x-[-1] scale-y-[-1]",
      )}
    >
      <FloatingPaths direction={1} />
      <FloatingPaths direction={-1} />
    </div>
  );
}

const HERO_VIEWBOX = "0 0 1600 900";
const HERO_BANDS = [280, 380, 480, 580, 680] as const;
const HERO_PATHS_PER_BAND = 12;

/** Wide horizontal flowing lines for premium hero backgrounds. */
function buildHorizontalFlowPath(
  index: number,
  bandY: number,
  direction: 1 | -1,
): string {
  const segmentCount = 22;
  const startX = -520;
  const endX = 2120;
  const amplitude = 34 + (index % 10) * 5;
  const waveCount = 3.6 + (index % 5) * 0.12;
  const phase = index * 0.26 * direction + bandY * 0.0015;
  const lane = index * 5.5 * direction;

  const dx = endX - startX;
  const points: [number, number][] = [];

  for (let i = 0; i <= segmentCount; i++) {
    const t = i / segmentCount;
    const x = startX + dx * t;
    const wave = Math.sin(t * Math.PI * waveCount + phase) * amplitude;
    const y = bandY + lane * 0.22 + wave;
    points.push([x, y]);
  }

  return pointsToSmoothCubicPath(points);
}

/** Full-viewport cinematic wave lines (middle / lower-middle). */
export function CinematicWaveBackground({ className }: { className?: string }) {
  const totalPaths = HERO_BANDS.length * HERO_PATHS_PER_BAND * 2;
  let pathIndex = 0;

  const paths = HERO_BANDS.flatMap((bandY, bandIndex) =>
    ([1, -1] as const).flatMap((direction) =>
      Array.from({ length: HERO_PATHS_PER_BAND }, (_, i) => {
        const id = `${bandY}-${direction}-${i}`;
        const delay = `${-((pathIndex++ / totalPaths) * 16).toFixed(3)}s`;
        return {
          id,
          d: buildHorizontalFlowPath(i, bandY, direction),
          width: 0.32 + (i % 7) * 0.055,
          opacity: 0.04 + (i % HERO_PATHS_PER_BAND) * 0.004 + bandIndex * 0.006,
          delay,
        };
      }),
    ),
  );

  return (
    <div className={cn("cinematic-wave-layer", className)} aria-hidden>
      <svg
        className="h-full w-full"
        viewBox={HERO_VIEWBOX}
        fill="none"
        preserveAspectRatio="xMidYMid slice"
      >
        <title>Cinematic wave background</title>
        {paths.map((path) => (
          <path
            key={path.id}
            d={path.d}
            className="wave-path wave-path--hero"
            pathLength={100}
            strokeWidth={path.width}
            strokeOpacity={path.opacity}
            style={{ animationDelay: path.delay }}
          />
        ))}
      </svg>
      <div className="cinematic-wave-layer__vignette" />
    </div>
  );
}

/** Animated wavy paths — use `fixed` for full-viewport page backgrounds. */
export function BackgroundPathsLayer({
  className,
  fixed = false,
}: {
  className?: string;
  /** Pin to viewport (entire page behind UI). */
  fixed?: boolean;
}) {
  return (
    <div
      className={cn(
        "background-paths-layer pointer-events-none overflow-hidden bg-black",
        fixed ? "fixed inset-0 z-0" : "absolute inset-0",
        className,
      )}
      aria-hidden
    >
      <WavyPathsCorner />
      <WavyPathsCorner mirrored />
    </div>
  );
}

export function BackgroundPaths({
  title = "Background Paths",
}: {
  title?: string;
}) {
  const words = title.split(" ");

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-neutral-950">
      <div className="absolute inset-0">
        <WavyPathsCorner />
        <WavyPathsCorner mirrored />
      </div>

      <div className="relative z-10 container mx-auto px-4 text-center md:px-6">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2 }}
          className="mx-auto max-w-4xl"
        >
          <h1 className="font-display mb-8 text-5xl italic tracking-tighter sm:text-7xl md:text-8xl">
            {words.map((word, wordIndex) => (
              <span
                key={wordIndex}
                className="mr-4 inline-block last:mr-0"
              >
                {word.split("").map((letter, letterIndex) => (
                  <motion.span
                    key={`${wordIndex}-${letterIndex}`}
                    initial={{ y: 100, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{
                      delay: wordIndex * 0.1 + letterIndex * 0.03,
                      type: "spring",
                      stiffness: 150,
                      damping: 25,
                    }}
                    className="inline-block bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent"
                  >
                    {letter}
                  </motion.span>
                ))}
              </span>
            ))}
          </h1>

          <div
            className="group relative inline-block overflow-hidden rounded-2xl bg-gradient-to-b from-white/10 to-black/10 p-px shadow-lg backdrop-blur-lg transition-shadow duration-300 hover:shadow-xl"
          >
            <Button
              variant="ghost"
              className="font-ui rounded-[1.15rem] border border-white/10 bg-black/95 px-8 py-6 text-lg font-semibold text-white backdrop-blur-md transition-all duration-300 hover:bg-black hover:shadow-md"
            >
              <span className="opacity-90 transition-opacity group-hover:opacity-100">
                Discover Excellence
              </span>
              <span className="ml-3 opacity-70 transition-all duration-300 group-hover:translate-x-1.5 group-hover:opacity-100">
                →
              </span>
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
