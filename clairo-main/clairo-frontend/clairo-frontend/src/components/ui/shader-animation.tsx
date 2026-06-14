import { useEffect, useRef } from "react";
import * as THREE from "three";
import { cn } from "@/lib/utils";

type SceneRef = {
  camera: THREE.Camera;
  scene: THREE.Scene;
  renderer: THREE.WebGLRenderer;
  uniforms: {
    time: { value: number };
    resolution: { value: THREE.Vector2 };
  };
  animationId: number;
  geometry: THREE.PlaneGeometry;
  material: THREE.ShaderMaterial;
};

export interface ShaderAnimationProps {
  /** Fires once when the intro shader sequence finishes (no loop). */
  onComplete?: () => void;
  /** Wall-clock duration before freezing and calling onComplete. */
  durationMs?: number;
  className?: string;
  /** When true, skip WebGL and invoke onComplete immediately. */
  reducedMotion?: boolean;
}

export function ShaderAnimation({
  onComplete,
  durationMs = 2000,
  className,
  reducedMotion,
}: ShaderAnimationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<SceneRef | null>(null);
  const onCompleteRef = useRef(onComplete);
  const completedRef = useRef(false);

  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    completedRef.current = false;

    const prefersReduced =
      reducedMotion ??
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReduced) {
      const id = window.setTimeout(() => {
        completedRef.current = true;
        onCompleteRef.current?.();
      }, 0);
      return () => window.clearTimeout(id);
    }

    const vertexShader = `
      void main() {
        gl_Position = vec4(position, 1.0);
      }
    `;

    const fragmentShader = `
      #define TWO_PI 6.2831853072
      #define PI 3.14159265359

      precision highp float;
      uniform vec2 resolution;
      uniform float time;

      void main(void) {
        vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);
        float t = time * 0.05;
        float lineWidth = 0.002;

        vec3 color = vec3(0.0);
        for(int j = 0; j < 3; j++){
          for(int i = 0; i < 5; i++){
            color[j] += lineWidth * float(i * i) / abs(fract(t - 0.01 * float(j) + float(i) * 0.01) * 5.0 - length(uv) + mod(uv.x + uv.y, 0.2));
          }
        }

        vec3 bgColor = vec3(0.02, 0.02, 0.04);
        vec3 finalColor = mix(bgColor, color, clamp(length(color) * 0.8, 0.0, 1.0));
        gl_FragColor = vec4(finalColor, 1.0);
      }
    `;

    const camera = new THREE.Camera();
    camera.position.z = 1;

    const scene = new THREE.Scene();
    const geometry = new THREE.PlaneGeometry(2, 2);

    const uniforms = {
      time: { value: 1.0 },
      resolution: { value: new THREE.Vector2() },
    };

    const material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
    });

    const canvas = renderer.domElement;
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";
    canvas.style.width = "100vw";
    canvas.style.height = "100vh";
    canvas.style.display = "block";
    canvas.style.margin = "0";
    canvas.style.padding = "0";
    canvas.style.border = "none";

    container.appendChild(canvas);

    const resize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      const pixelRatio = Math.min(window.devicePixelRatio, 2);

      renderer.setPixelRatio(pixelRatio);
      renderer.setSize(width, height, false);
      uniforms.resolution.value.set(width * pixelRatio, height * pixelRatio);
    };

    resize();

    window.addEventListener("resize", resize);
    window.addEventListener("orientationchange", resize);

    const startTime = performance.now();
    let animationId = 0;

    const animate = (now: number) => {
      animationId = requestAnimationFrame(animate);

      if (!completedRef.current) {
        uniforms.time.value += 0.05;
        if (now - startTime >= durationMs) {
          completedRef.current = true;
          onCompleteRef.current?.();
        }
      }

      renderer.render(scene, camera);
      if (sceneRef.current) {
        sceneRef.current.animationId = animationId;
      }
    };

    sceneRef.current = {
      camera,
      scene,
      renderer,
      uniforms,
      animationId: 0,
      geometry,
      material,
    };

    animationId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("orientationchange", resize);
      cancelAnimationFrame(animationId);

      if (sceneRef.current) {
        if (container.contains(sceneRef.current.renderer.domElement)) {
          container.removeChild(sceneRef.current.renderer.domElement);
        }

        sceneRef.current.geometry.dispose();
        sceneRef.current.material.dispose();
        sceneRef.current.renderer.dispose();
        sceneRef.current = null;
      }
    };
  }, [durationMs, reducedMotion]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "fixed inset-0 z-0 h-screen w-screen overflow-hidden bg-[#05050a]",
        className,
      )}
      style={{
        width: "100vw",
        height: "100vh",
        margin: 0,
        padding: 0,
        borderRadius: 0,
        border: "none",
      }}
      aria-hidden="true"
    />
  );
}
