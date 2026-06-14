import { useEffect, useRef } from "react";
import * as THREE from "three";
import { cn } from "@/lib/utils";

export interface GLSLHillsProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  cameraZ?: number;
  cameraY?: number;
  lookAtY?: number;
  planeSize?: number;
  speed?: number;
}

const VERTEX_SHADER = `
#define GLSLIFY 1
attribute vec3 position;
uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform float time;
varying vec3 vPosition;

mat4 rotateMatrixX(float radian) {
  return mat4(
    1.0, 0.0, 0.0, 0.0,
    0.0, cos(radian), -sin(radian), 0.0,
    0.0, sin(radian), cos(radian), 0.0,
    0.0, 0.0, 0.0, 1.0
  );
}

vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
vec3 fade(vec3 t) { return t*t*t*(t*(t*6.0-15.0)+10.0); }

float cnoise(vec3 P) {
  vec3 Pi0 = floor(P);
  vec3 Pi1 = Pi0 + vec3(1.0);
  Pi0 = mod289(Pi0);
  Pi1 = mod289(Pi1);
  vec3 Pf0 = fract(P);
  vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.yy, Pi1.yy);
  vec4 iz0 = Pi0.zzzz;
  vec4 iz1 = Pi1.zzzz;

  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0);
  vec4 ixy1 = permute(ixy + iz1);

  vec4 gx0 = ixy0 * (1.0 / 7.0);
  vec4 gy0 = fract(floor(gx0) * (1.0 / 7.0)) - 0.5;
  gx0 = fract(gx0);
  vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0));
  gx0 -= sz0 * (step(0.0, gx0) - 0.5);
  gy0 -= sz0 * (step(0.0, gy0) - 0.5);

  vec4 gx1 = ixy1 * (1.0 / 7.0);
  vec4 gy1 = fract(floor(gx1) * (1.0 / 7.0)) - 0.5;
  gx1 = fract(gx1);
  vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0));
  gx1 -= sz1 * (step(0.0, gx1) - 0.5);
  gy1 -= sz1 * (step(0.0, gy1) - 0.5);

  vec3 g000 = vec3(gx0.x,gy0.x,gz0.x);
  vec3 g100 = vec3(gx0.y,gy0.y,gz0.y);
  vec3 g010 = vec3(gx0.z,gy0.z,gz0.z);
  vec3 g110 = vec3(gx0.w,gy0.w,gz0.w);
  vec3 g001 = vec3(gx1.x,gy1.x,gz1.x);
  vec3 g101 = vec3(gx1.y,gy1.y,gz1.y);
  vec3 g011 = vec3(gx1.z,gy1.z,gz1.z);
  vec3 g111 = vec3(gx1.w,gy1.w,gz1.w);

  vec4 norm0 = taylorInvSqrt(vec4(dot(g000, g000), dot(g010, g010), dot(g100, g100), dot(g110, g110)));
  g000 *= norm0.x;
  g010 *= norm0.y;
  g100 *= norm0.z;
  g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001, g001), dot(g011, g011), dot(g101, g101), dot(g111, g111)));
  g001 *= norm1.x;
  g011 *= norm1.y;
  g101 *= norm1.z;
  g111 *= norm1.w;

  float n000 = dot(g000, Pf0);
  float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z));
  float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z));
  float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz));
  float n111 = dot(g111, Pf1);

  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}

void main(void) {
  vec3 updatePosition = (rotateMatrixX(radians(90.0)) * vec4(position, 1.0)).xyz;
  float sin1 = sin(radians(updatePosition.x / 128.0 * 90.0));
  vec3 noisePosition = updatePosition + vec3(0.0, 0.0, time * -30.0);
  float noise1 = cnoise(noisePosition * 0.08);
  float noise2 = cnoise(noisePosition * 0.06);
  float noise3 = cnoise(noisePosition * 0.4);
  vec3 lastPosition = updatePosition + vec3(0.0,
    noise1 * sin1 * 8.0
    + noise2 * sin1 * 8.0
    + noise3 * (abs(sin1) * 2.0 + 0.5)
    + pow(sin1, 2.0) * 40.0, 0.0);

  vPosition = lastPosition;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(lastPosition, 1.0);
}
`;

const FRAGMENT_SHADER = `
precision highp float;
#define GLSLIFY 1
varying vec3 vPosition;

void main(void) {
  float dist = length(vPosition);
  float opacity = (96.0 - dist) / 256.0 * 0.75;

  float height = clamp((vPosition.y + 5.0) / 55.0, 0.0, 1.0);

  vec3 valleyColor = vec3(0.02, 0.03, 0.10);
  vec3 midColor    = vec3(0.22, 0.28, 0.42);
  vec3 peakColor   = vec3(0.78, 0.84, 0.94);

  vec3 color = mix(valleyColor, midColor, smoothstep(0.0, 0.5, height));
  color      = mix(color, peakColor, smoothstep(0.5, 1.0, height));

  float rimLight = smoothstep(0.75, 1.0, height) * smoothstep(0.0, 0.45, vPosition.x / 64.0 + 0.5);
  color += vec3(0.22, 0.03, 0.03) * rimLight * 0.55;

  float horizonFade = 1.0 - smoothstep(55.0, 96.0, dist);
  opacity *= horizonFade;

  gl_FragColor = vec4(color, clamp(opacity, 0.0, 1.0));
}
`;

function GLSLHills({
  width = "100%",
  height = "100%",
  className,
  cameraZ = 125,
  cameraY = 8,
  lookAtY = 20,
  planeSize = 256,
  speed = 0.5,
}: GLSLHillsProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    class Plane {
      uniforms: { time: { type: string; value: number } };
      mesh: THREE.Mesh;
      time: number;

      constructor() {
        this.uniforms = {
          time: { type: "f", value: 0 },
        };
        this.mesh = this.createMesh();
        this.time = speed;
      }

      createMesh() {
        return new THREE.Mesh(
          new THREE.PlaneGeometry(planeSize, planeSize, planeSize, planeSize),
          new THREE.RawShaderMaterial({
            uniforms: this.uniforms,
            vertexShader: VERTEX_SHADER,
            fragmentShader: FRAGMENT_SHADER,
            transparent: true,
          }),
        );
      }

      render(delta: number) {
        this.uniforms.time.value += delta * this.time;
      }
    }

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      alpha: true,
    });
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 1, 10000);
    const clock = new THREE.Clock();
    const plane = new Plane();

    let animationId = 0;

    const resize = () => {
      const w = container.clientWidth || 1;
      const h = container.clientHeight || 1;
      canvas.width = w;
      canvas.height = h;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    };

    const render = () => {
      plane.render(clock.getDelta());
      renderer.render(scene, camera);
    };

    const renderLoop = () => {
      render();
      animationId = requestAnimationFrame(renderLoop);
    };

    renderer.setClearColor(0x000000, 0);
    camera.position.set(0, cameraY, cameraZ);
    camera.lookAt(new THREE.Vector3(0, lookAtY, 0));
    scene.add(plane.mesh);

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();
    renderLoop();

    return () => {
      cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
      scene.remove(plane.mesh);
      plane.mesh.geometry.dispose();
      (plane.mesh.material as THREE.Material).dispose();
      renderer.dispose();
    };
  }, [cameraZ, cameraY, lookAtY, planeSize, speed]);

  return (
    <div
      ref={containerRef}
      className={cn("relative overflow-hidden", className)}
      style={{ width, height }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-[1] h-full w-full"
        aria-hidden
      />
    </div>
  );
}

export { GLSLHills };
