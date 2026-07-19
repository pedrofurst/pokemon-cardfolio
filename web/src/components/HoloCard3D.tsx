"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

interface HoloCard3DProps {
  imageUrl: string;
  onClose?: () => void;
}

const CARD_WIDTH = 2.5;
const CARD_HEIGHT = 3.5;
const CARD_DEPTH = 0.03;
const MAX_DRAG_ROTATION_Y = THREE.MathUtils.degToRad(35);
const MAX_DRAG_ROTATION_X = THREE.MathUtils.degToRad(18);
const DRAG_DECAY = 0.92;
const ROTATION_SMOOTHING = 0.15;

const SHEEN_VERTEX_SHADER = `
  varying vec3 vNormal;
  varying vec3 vWorldPosition;

  void main() {
    vNormal = normalize(mat3(modelMatrix) * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const SHEEN_FRAGMENT_SHADER = `
  uniform float uTime;
  uniform float uOpacity;
  uniform vec3 uLightDirection;
  varying vec3 vNormal;
  varying vec3 vWorldPosition;

  vec3 holoRainbow(float t) {
    vec3 cyan = vec3(0.475, 0.906, 0.875);
    vec3 indigo = vec3(0.424, 0.525, 1.0);
    vec3 magenta = vec3(0.788, 0.545, 1.0);
    vec3 gold = vec3(1.0, 0.851, 0.541);
    vec3 mint = vec3(0.561, 0.941, 0.753);
    float scaled = fract(t) * 4.0;
    if (scaled < 1.0) {
      return mix(cyan, indigo, scaled);
    }
    if (scaled < 2.0) {
      return mix(indigo, magenta, scaled - 1.0);
    }
    if (scaled < 3.0) {
      return mix(magenta, gold, scaled - 2.0);
    }
    return mix(gold, mint, scaled - 3.0);
  }

  void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
    float fresnel = pow(1.0 - clamp(dot(normal, viewDirection), 0.0, 1.0), 2.0);
    float lightDot = max(dot(reflect(-viewDirection, normal), normalize(uLightDirection)), 0.0);

    float band = (vWorldPosition.x * 0.55 + vWorldPosition.y * 0.35)
      + normal.x * 1.6
      + normal.y * 0.9
      + uTime * 0.06;

    vec3 color = holoRainbow(band) * (0.55 + 0.45 * lightDot);
    float alpha = uOpacity * mix(0.25, 1.0, fresnel);
    gl_FragColor = vec4(color, alpha);
  }
`;

type ViewerStatus = "loading" | "ready" | "fallback";

function detectWebglSupport(): boolean {
  try {
    const testCanvas = document.createElement("canvas");
    return Boolean(
      testCanvas.getContext("webgl2") || testCanvas.getContext("webgl")
    );
  } catch {
    return false;
  }
}

export function HoloCard3D({ imageUrl, onClose }: HoloCard3DProps) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<ViewerStatus>(() =>
    detectWebglSupport() ? "loading" : "fallback"
  );

  useEffect(() => {
    const stageElement = stageRef.current;
    if (!stageElement || !detectWebglSupport()) {
      return;
    }

    let disposed = false;
    let animationFrameId: number | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let renderer: THREE.WebGLRenderer | null = null;
    let texture: THREE.Texture | null = null;
    const disposableGeometries: THREE.BufferGeometry[] = [];
    const disposableMaterials: THREE.Material[] = [];

    function handleSetupFailure() {
      if (disposed) {
        return;
      }
      cleanupThreeResources();
      setStatus("fallback");
    }

    function cleanupThreeResources() {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
      resizeObserver?.disconnect();
      resizeObserver = null;
      stageElement!.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      disposableGeometries.forEach((geometry) => geometry.dispose());
      disposableMaterials.forEach((material) => material.dispose());
      texture?.dispose();
      if (renderer) {
        renderer.dispose();
        if (renderer.domElement.parentElement === stageElement) {
          stageElement!.removeChild(renderer.domElement);
        }
        renderer = null;
      }
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const dragRotation = { x: 0, y: 0 };
    const currentRotation = { x: 0, y: 0 };
    const dragPointerState = {
      isDragging: false,
      pointerId: -1,
      startX: 0,
      startY: 0,
      startRotationX: 0,
      startRotationY: 0,
    };

    function handlePointerDown(event: PointerEvent) {
      dragPointerState.isDragging = true;
      dragPointerState.pointerId = event.pointerId;
      dragPointerState.startX = event.clientX;
      dragPointerState.startY = event.clientY;
      dragPointerState.startRotationX = dragRotation.x;
      dragPointerState.startRotationY = dragRotation.y;
    }

    function handlePointerMove(event: PointerEvent) {
      if (!dragPointerState.isDragging || event.pointerId !== dragPointerState.pointerId) {
        return;
      }
      const deltaX = event.clientX - dragPointerState.startX;
      const deltaY = event.clientY - dragPointerState.startY;
      dragRotation.y = THREE.MathUtils.clamp(
        dragPointerState.startRotationY + deltaX * 0.01,
        -MAX_DRAG_ROTATION_Y,
        MAX_DRAG_ROTATION_Y
      );
      dragRotation.x = THREE.MathUtils.clamp(
        dragPointerState.startRotationX - deltaY * 0.006,
        -MAX_DRAG_ROTATION_X,
        MAX_DRAG_ROTATION_X
      );
    }

    function handlePointerUp(event: PointerEvent) {
      if (event.pointerId !== dragPointerState.pointerId) {
        return;
      }
      dragPointerState.isDragging = false;
    }

    try {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
      camera.position.set(0, 0, 6);

      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      const initialRect = stageElement.getBoundingClientRect();
      renderer.setSize(
        Math.max(initialRect.width, 1),
        Math.max(initialRect.height, 1)
      );
      stageElement.appendChild(renderer.domElement);

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
      const pointLight = new THREE.PointLight(0xffffff, 1.4, 0, 0.6);
      pointLight.position.set(2.5, 3, 4);
      scene.add(ambientLight, pointLight);

      const cardGroup = new THREE.Group();
      scene.add(cardGroup);

      const darkEdgeMaterial = new THREE.MeshStandardMaterial({
        color: 0x0c1220,
        roughness: 0.6,
        metalness: 0.2,
      });
      disposableMaterials.push(darkEdgeMaterial);

      const cardFrontMaterial = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 0.35,
        metalness: 0.1,
      });
      disposableMaterials.push(cardFrontMaterial);

      const cardGeometry = new THREE.BoxGeometry(
        CARD_WIDTH,
        CARD_HEIGHT,
        CARD_DEPTH
      );
      disposableGeometries.push(cardGeometry);

      const cardMesh = new THREE.Mesh(cardGeometry, [
        darkEdgeMaterial,
        darkEdgeMaterial,
        darkEdgeMaterial,
        darkEdgeMaterial,
        cardFrontMaterial,
        darkEdgeMaterial,
      ]);
      cardGroup.add(cardMesh);

      const sheenUniforms = {
        uTime: { value: 0 },
        uOpacity: { value: 0.35 },
        uLightDirection: { value: new THREE.Vector3(0.4, 0.5, 1) },
      };

      const sheenGeometry = new THREE.PlaneGeometry(CARD_WIDTH, CARD_HEIGHT);
      disposableGeometries.push(sheenGeometry);

      const sheenMaterial = new THREE.ShaderMaterial({
        uniforms: sheenUniforms,
        vertexShader: SHEEN_VERTEX_SHADER,
        fragmentShader: SHEEN_FRAGMENT_SHADER,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      disposableMaterials.push(sheenMaterial);

      const sheenMesh = new THREE.Mesh(sheenGeometry, sheenMaterial);
      sheenMesh.position.z = CARD_DEPTH / 2 + 0.01;
      cardGroup.add(sheenMesh);

      const textureLoader = new THREE.TextureLoader();
      textureLoader.crossOrigin = "anonymous";
      textureLoader.load(
        imageUrl,
        (loadedTexture) => {
          if (disposed) {
            loadedTexture.dispose();
            return;
          }
          loadedTexture.colorSpace = THREE.SRGBColorSpace;
          texture = loadedTexture;
          cardFrontMaterial.map = loadedTexture;
          cardFrontMaterial.needsUpdate = true;
          setStatus("ready");
        },
        undefined,
        () => {
          handleSetupFailure();
        }
      );

      resizeObserver = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (!entry || !renderer) {
          return;
        }
        const { width, height } = entry.contentRect;
        if (width <= 0 || height <= 0) {
          return;
        }
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
      });
      resizeObserver.observe(stageElement);

      stageElement.addEventListener("pointerdown", handlePointerDown);
      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);

      const clock = new THREE.Clock();
      let idleSwayPhase = 0;

      function animate() {
        animationFrameId = requestAnimationFrame(animate);
        const delta = clock.getDelta();

        if (!dragPointerState.isDragging) {
          dragRotation.x *= DRAG_DECAY;
          dragRotation.y *= DRAG_DECAY;
        }

        let idleSwayY = 0;
        let idleSwayX = 0;
        if (!prefersReducedMotion) {
          idleSwayPhase += delta;
          sheenUniforms.uTime.value += delta;
          if (!dragPointerState.isDragging) {
            idleSwayY = Math.sin(idleSwayPhase * 0.5) * 0.09;
            idleSwayX = Math.sin(idleSwayPhase * 0.35) * 0.04;
          }
        }

        const targetRotationY = dragRotation.y + idleSwayY;
        const targetRotationX = dragRotation.x + idleSwayX;
        currentRotation.y += (targetRotationY - currentRotation.y) * ROTATION_SMOOTHING;
        currentRotation.x += (targetRotationX - currentRotation.x) * ROTATION_SMOOTHING;
        cardGroup.rotation.y = currentRotation.y;
        cardGroup.rotation.x = currentRotation.x;

        renderer?.render(scene, camera);
      }
      animate();
    } catch {
      handleSetupFailure();
    }

    return () => {
      disposed = true;
      cleanupThreeResources();
    };
  }, [imageUrl]);

  return (
    <div className="holo3d">
      <div className="holo3d__stage" ref={stageRef}>
        {status === "fallback" && (
          <div className="holo3d__fallback">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageUrl} alt="Card" className="holo3d__fallback-img" />
            <span className="holo3d__fallback-caption">3D unavailable</span>
          </div>
        )}
      </div>
      {status !== "fallback" && <span className="holo3d__hint">Drag to rotate</span>}
      {onClose && (
        <button
          type="button"
          className="holo3d__close"
          onClick={onClose}
          aria-label="Close 3D view"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      )}
    </div>
  );
}
