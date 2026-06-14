import { useRef, useEffect } from "react";
import * as THREE from "three";
import { cn } from "@/lib/utils";

export interface ParticleWaveProps {
  className?: string;
}

const particleVertex = `
  attribute float scale;
  uniform float uTime;
  void main() {
    vec3 p = position;
    float s = scale;
    p.y += (sin(p.x + uTime) * 0.5) + (cos(p.y + uTime) * 0.1) * 2.0;
    p.x += (sin(p.y + uTime) * 0.5);
    s += (sin(p.x + uTime) * 0.5) + (cos(p.y + uTime) * 0.1) * 2.0;

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
    gl_PointSize = s * 15.0 * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const particleFragment = `
  uniform vec3 uColor;
  void main() {
    gl_FragColor = vec4(uColor, 0.5);
  }
`;

function getCurrentTheme() {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function getBackgroundColor(theme: string) {
  return theme === "dark"
    ? new THREE.Color(0x000000)
    : new THREE.Color(0xffffff);
}

function getParticleColor(theme: string) {
  return theme === "dark"
    ? new THREE.Vector3(0.796, 0.835, 0.882)
    : new THREE.Vector3(0.1, 0.1, 0.12);
}

export function ParticleWave({ className = "" }: ParticleWaveProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    particles: THREE.Points;
    particleMaterial: THREE.ShaderMaterial;
    animationId: number | null;
  } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const winWidth = window.innerWidth;
    const winHeight = window.innerHeight;
    const aspectRatio = winWidth / winHeight;

    const camera = new THREE.PerspectiveCamera(75, aspectRatio, 0.01, 1000);
    camera.position.set(0, 6, 5);

    const scene = new THREE.Scene();

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
    });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(winWidth, winHeight);

    const currentTheme = getCurrentTheme();
    renderer.setClearColor(getBackgroundColor(currentTheme));

    const gap = 0.3;
    const amountX = 200;
    const amountY = 200;
    const particleNum = amountX * amountY;
    const particlePositions = new Float32Array(particleNum * 3);
    const particleScales = new Float32Array(particleNum);

    let i = 0;
    let j = 0;
    for (let ix = 0; ix < amountX; ix++) {
      for (let iy = 0; iy < amountY; iy++) {
        particlePositions[i] = ix * gap - (amountX * gap) / 2;
        particlePositions[i + 1] = 0;
        particlePositions[i + 2] = iy * gap - (amountX * gap) / 2;
        particleScales[j] = 1;
        i += 3;
        j++;
      }
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(particlePositions, 3),
    );
    particleGeometry.setAttribute(
      "scale",
      new THREE.BufferAttribute(particleScales, 1),
    );

    const particleMaterial = new THREE.ShaderMaterial({
      transparent: true,
      vertexShader: particleVertex,
      fragmentShader: particleFragment,
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: getParticleColor(currentTheme) },
      },
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    sceneRef.current = {
      scene,
      camera,
      renderer,
      particles,
      particleMaterial,
      animationId: null,
    };

    const animate = () => {
      if (!sceneRef.current) return;

      const ctx = sceneRef.current;
      ctx.particleMaterial.uniforms.uTime.value += 0.05;

      const theme = getCurrentTheme();
      ctx.particleMaterial.uniforms.uColor.value = getParticleColor(theme);
      ctx.renderer.setClearColor(getBackgroundColor(theme));

      ctx.camera.lookAt(ctx.scene.position);
      ctx.renderer.render(ctx.scene, ctx.camera);

      ctx.animationId = requestAnimationFrame(animate);
    };

    const handleResize = () => {
      if (!sceneRef.current) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      sceneRef.current.camera.aspect = w / h;
      sceneRef.current.camera.updateProjectionMatrix();
      sceneRef.current.renderer.setPixelRatio(
        Math.min(window.devicePixelRatio || 1, 2),
      );
      sceneRef.current.renderer.setSize(w, h);
    };

    animate();
    window.addEventListener("resize", handleResize);

    return () => {
      if (sceneRef.current?.animationId) {
        cancelAnimationFrame(sceneRef.current.animationId);
      }
      window.removeEventListener("resize", handleResize);

      if (sceneRef.current) {
        const { scene, renderer, particles, particleMaterial } = sceneRef.current;
        scene.remove(particles);
        particles.geometry.dispose();
        particleMaterial.dispose();
        renderer.dispose();
        sceneRef.current = null;
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={cn("block h-full w-full", className)}
      aria-hidden
    />
  );
}
