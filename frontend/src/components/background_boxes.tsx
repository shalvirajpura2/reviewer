import { useEffect, useRef } from "react";

type Point = {
  x: number;
  y: number;
};

type TrailCell = {
  i: number;
  j: number;
  alpha: number;
  color: string;
};

type Vec2 = {
  x: number;
  y: number;
};

type ActiveCell = {
  i: number;
  j: number;
  life: number;
};

const accent_core = "92,255,138";
const accent_soft = "76,217,116";
const accent_edge = "210,255,222";

export function BackgroundBoxes() {
  const canvas_ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvas_ref.current;
    if (!canvas) return;

    const context = canvas.getContext("2d");
    if (!context) return;

    const ctx: CanvasRenderingContext2D = context;
    const stable_canvas: HTMLCanvasElement = canvas;

    let animation_frame = 0;
    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let cell_width = 88;
    let cell_height = 52;
    let origin: Vec2 = { x: 0, y: 0 };
    let range_i = 0;
    let range_j = 0;

    const pointer: Point = { x: 0, y: 0 };
    const smooth_pointer: Point = { x: 0, y: 0 };
    const fade_trail: TrailCell[] = [];
    const active_cells: ActiveCell[] = [];

    let last_spawn_time = 0;
    let last_center_key = "";
    const reduced_motion_query = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reduce_motion = reduced_motion_query.matches;

    function basis_a() {
      return { x: cell_width, y: cell_height };
    }

    function basis_b() {
      return { x: -cell_width, y: cell_height };
    }

    function lattice_point(i: number, j: number) {
      const a = basis_a();
      const b = basis_b();
      return {
        x: origin.x + i * a.x + j * b.x,
        y: origin.y + i * a.y + j * b.y
      };
    }

    function resize() {
      const rect = stable_canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;

      if (width < 700) {
        cell_width = 64;
        cell_height = 38;
      } else if (width < 1200) {
        cell_width = 76;
        cell_height = 45;
      } else {
        cell_width = 88;
        cell_height = 52;
      }

      range_i = Math.ceil(width / cell_width) + 10;
      range_j = Math.ceil(height / cell_height) + 10;
      origin = { x: width * 0.5, y: -height * 0.28 };

      dpr = Math.min(window.devicePixelRatio || 1, 2);
      stable_canvas.width = Math.round(width * dpr);
      stable_canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      pointer.x = width * 0.66;
      pointer.y = height * 0.56;
      smooth_pointer.x = pointer.x;
      smooth_pointer.y = pointer.y;
    }

    function draw_polygon(points: Vec2[]) {
      if (points.length === 0) return;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let index = 1; index < points.length; index += 1) {
        ctx.lineTo(points[index].x, points[index].y);
      }
      ctx.closePath();
    }

    function draw_grid() {
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(255,255,255,0.095)";

      for (let i = -range_i; i <= range_i; i += 1) {
        const start = lattice_point(i, -2);
        const end = lattice_point(i, range_j + 4);
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }

      for (let j = -range_j; j <= range_j; j += 1) {
        const start = lattice_point(-range_i - 2, j);
        const end = lattice_point(range_i + 2, j);
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
    }

    function draw_base_glow() {
      const gradient = ctx.createRadialGradient(
        width * 0.48,
        height * 0.34,
        0,
        width * 0.48,
        height * 0.34,
        Math.max(width * 0.42, 320)
      );

      gradient.addColorStop(0, "rgba(92,255,138,0.045)");
      gradient.addColorStop(0.45, "rgba(92,255,138,0.02)");
      gradient.addColorStop(1, "rgba(12,12,13,0)");

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
    }

    function fill_cell(i: number, j: number, alpha: number, rgb: string) {
      const p0 = lattice_point(i, j);
      const p1 = lattice_point(i + 1, j);
      const p2 = lattice_point(i + 1, j + 1);
      const p3 = lattice_point(i, j + 1);

      draw_polygon([p0, p1, p2, p3]);
      ctx.fillStyle = `rgba(${rgb},${alpha})`;
      ctx.fill();

      draw_polygon([p0, p1, p2, p3]);
      ctx.strokeStyle = `rgba(${accent_edge},${Math.min(alpha * 0.46, 0.32)})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    function solve_lattice(x: number, y: number) {
      const a = basis_a();
      const b = basis_b();
      const px = x - origin.x;
      const py = y - origin.y;
      const det = a.x * b.y - a.y * b.x;

      return {
        i: (px * b.y - py * b.x) / det,
        j: (py * a.x - px * a.y) / det
      };
    }

    function spawn_fade_trail(now: number, center_i: number, center_j: number) {
      if (now - last_spawn_time < 90) return;
      last_spawn_time = now;

      fade_trail.push({
        i: center_i,
        j: center_j,
        alpha: 0.06,
        color: accent_soft
      });

      if (fade_trail.length > 8) {
        fade_trail.splice(0, fade_trail.length - 8);
      }
    }

    function draw_fade_trail() {
      for (let index = fade_trail.length - 1; index >= 0; index -= 1) {
        const item = fade_trail[index];
        item.alpha *= 0.952;

        if (item.alpha < 0.018) {
          fade_trail.splice(index, 1);
          continue;
        }

        fill_cell(item.i, item.j, item.alpha, item.color);
      }
    }

    function update_active_cells(center_i: number, center_j: number) {
      const next_key = `${center_i}:${center_j}`;
      if (next_key === last_center_key) {
        return;
      }

      last_center_key = next_key;
      active_cells.unshift({ i: center_i, j: center_j, life: 1 });

      const deduped: ActiveCell[] = [];
      for (const cell of active_cells) {
        if (!deduped.some((item) => item.i === cell.i && item.j === cell.j)) {
          deduped.push(cell);
        }
        if (deduped.length === 4) {
          break;
        }
      }

      active_cells.splice(0, active_cells.length, ...deduped);
    }

    function draw_cluster(now: number) {
      const lattice = solve_lattice(smooth_pointer.x, smooth_pointer.y);
      const center_i = Math.round(lattice.i);
      const center_j = Math.round(lattice.j);

      update_active_cells(center_i, center_j);

      active_cells.forEach((cell, index) => {
        cell.life *= 0.986;
        const base_alpha = [0.34, 0.23, 0.16, 0.11][index] ?? 0.08;
        const alpha = base_alpha * Math.max(cell.life, 0.68);
        const color = index === 0 ? accent_edge : index <= 2 ? accent_core : accent_soft;
        fill_cell(cell.i, cell.j, alpha, color);
      });

      const neighbors = [
        { di: 0, dj: 1, alpha: 0.038 },
        { di: 1, dj: 0, alpha: 0.034 },
        { di: -1, dj: 0, alpha: 0.034 },
        { di: 0, dj: -1, alpha: 0.034 }
      ];

      for (const item of neighbors) {
        fill_cell(center_i + item.di, center_j + item.dj, item.alpha, accent_soft);
      }

      spawn_fade_trail(now, center_i, center_j);
    }

    function draw_pointer_glow() {
      const gradient = ctx.createRadialGradient(
        smooth_pointer.x,
        smooth_pointer.y,
        0,
        smooth_pointer.x,
        smooth_pointer.y,
        cell_width * 1.8
      );

      gradient.addColorStop(0, "rgba(160,255,188,0.1)");
      gradient.addColorStop(0.34, "rgba(92,255,138,0.05)");
      gradient.addColorStop(1, "rgba(12,12,13,0)");

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
    }

    function draw_edge_fade() {
      const fade = ctx.createRadialGradient(
        width * 0.5,
        height * 0.48,
        Math.min(width, height) * 0.18,
        width * 0.5,
        height * 0.48,
        Math.max(width * 0.74, height)
      );

      fade.addColorStop(0, "rgba(12,12,13,0)");
      fade.addColorStop(0.72, "rgba(12,12,13,0.08)");
      fade.addColorStop(1, "rgba(12,12,13,0.26)");

      ctx.fillStyle = fade;
      ctx.fillRect(0, 0, width, height);
    }

    function render(now: number) {
      ctx.clearRect(0, 0, width, height);
      draw_base_glow();
      draw_grid();

      if (reduce_motion) {
        smooth_pointer.x = width * 0.66;
        smooth_pointer.y = height * 0.56;
      } else {
        smooth_pointer.x += (pointer.x - smooth_pointer.x) * 0.16;
        smooth_pointer.y += (pointer.y - smooth_pointer.y) * 0.16;
      }

      draw_pointer_glow();
      draw_fade_trail();
      draw_cluster(now);
      draw_edge_fade();

      animation_frame = window.requestAnimationFrame(render);
    }

    function on_pointer_move(event: PointerEvent) {
      const rect = stable_canvas.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
    }

    function on_pointer_leave() {
      pointer.x = width * 0.66;
      pointer.y = height * 0.56;
    }

    function on_reduced_motion_change(event: MediaQueryListEvent) {
      reduce_motion = event.matches;
    }

    resize();
    animation_frame = window.requestAnimationFrame(render);

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", on_pointer_move, { passive: true });
    window.addEventListener("pointerleave", on_pointer_leave);
    reduced_motion_query.addEventListener("change", on_reduced_motion_change);

    return () => {
      window.cancelAnimationFrame(animation_frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", on_pointer_move);
      window.removeEventListener("pointerleave", on_pointer_leave);
      reduced_motion_query.removeEventListener("change", on_reduced_motion_change);
    };
  }, []);

  return (
    <div className="background-boxes" aria-hidden="true">
      <canvas ref={canvas_ref} className="background-boxes-canvas" />
      <div className="background-boxes-overlay" />
    </div>
  );
}
