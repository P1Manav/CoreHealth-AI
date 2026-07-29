/**
 * WebglBackground — Dynamic Canvas rendering organic bokeh light fields & grid dots
 * for both Dark Mode (Image 2: Lime/Green) and Light Mode (Image 1: Terracotta/Coral).
 */
import { useEffect, useRef } from 'react';

function WebglBackground({ theme = 'dark' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    // Organic bokeh blobs positions
    const blobs = [
      { x: width * 0.75, y: height * 0.3, radius: 280, phase: 0 },
      { x: width * 0.85, y: height * 0.7, radius: 320, phase: 1.5 },
      { x: width * 0.65, y: height * 0.8, radius: 240, phase: 3.0 },
      { x: width * 0.95, y: height * 0.2, radius: 260, phase: 4.5 },
    ];

    let time = 0;

    const render = () => {
      time += 0.008;
      ctx.clearRect(0, 0, width, height);

      const isLight = theme === 'light';

      // 1. Base split background
      const bgGrad = ctx.createLinearGradient(0, 0, width, 0);
      if (isLight) {
        bgGrad.addColorStop(0, '#FFFFFF');
        bgGrad.addColorStop(0.48, '#FFFFFF');
        bgGrad.addColorStop(0.52, '#fff7ed');
        bgGrad.addColorStop(1, '#ffedd5');
      } else {
        bgGrad.addColorStop(0, '#020617');
        bgGrad.addColorStop(0.48, '#020617');
        bgGrad.addColorStop(0.52, '#040d12');
        bgGrad.addColorStop(1, '#02080a');
      }
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // 2. Draw organic bokeh blobs on the right side
      blobs.forEach((b) => {
        b.phase += 0.005;
        const currentX = b.x + Math.sin(b.phase) * 35;
        const currentY = b.y + Math.cos(b.phase * 0.8) * 35;

        const blobGrad = ctx.createRadialGradient(
          currentX,
          currentY,
          0,
          currentX,
          currentY,
          b.radius
        );

        if (isLight) {
          // Warm terracotta / coral / amber bokeh (Image 1)
          blobGrad.addColorStop(0, 'rgba(234, 88, 12, 0.45)');
          blobGrad.addColorStop(0.4, 'rgba(225, 29, 72, 0.3)');
          blobGrad.addColorStop(0.7, 'rgba(251, 191, 36, 0.2)');
          blobGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        } else {
          // Green / Lime bokeh (Image 2)
          blobGrad.addColorStop(0, 'rgba(163, 230, 53, 0.35)');
          blobGrad.addColorStop(0.4, 'rgba(101, 163, 13, 0.2)');
          blobGrad.addColorStop(0.7, 'rgba(21, 128, 61, 0.08)');
          blobGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        }

        ctx.fillStyle = blobGrad;
        ctx.beginPath();
        ctx.arc(currentX, currentY, b.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // 3. Grid dots overlay on the right half (from x = width * 0.48)
      const dotSpacing = 24;
      const startX = Math.floor((width * 0.48) / dotSpacing) * dotSpacing;
      ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)';

      for (let x = startX; x < width; x += dotSpacing) {
        for (let y = 0; y < height; y += dotSpacing) {
          ctx.beginPath();
          ctx.arc(x, y, 0.85, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [theme]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}

export default WebglBackground;
