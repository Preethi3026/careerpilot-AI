import { useEffect, useRef } from "react";

export type OfficeAgent = {
  id: number;
  name: string;
  status: "idle" | "chatting" | "working" | "queued" | "visiting" | "completed" | "failed" | "skipped";
  station?: string;
  phase?: string;
  stepIndex?: number;
  stepCount?: number;
};

type OfficeSceneProps = {
  agents: OfficeAgent[];
  selectedId: number | null;
  onAgentClick: (id: number) => void;
  onStationClick: (station: string) => void;
  onTimeClick: () => void;
};

type Point = { x: number; y: number };
type Actor = {
  x: number; y: number; target: Point; path: Point[]; mode: OfficeAgent["status"];
  station?: string; step: number; blink: number; bob: number; home: Point;
  wanderAt: number; returnAt: number; wandering: boolean; breakKind: "staff" | "tea" | "snack" | null;
};

const W = 640;
const H = 360;
const DESKS: Point[] = [
  { x: 72, y: 162 }, { x: 145, y: 162 }, { x: 218, y: 162 }, { x: 291, y: 162 },
  { x: 72, y: 267 }, { x: 145, y: 267 }, { x: 218, y: 267 }, { x: 291, y: 267 },
];
const BREAK_SPOTS: Record<"staff" | "tea" | "snack", Point[]> = {
  staff: [{ x: 490, y: 174 }, { x: 520, y: 176 }],
  tea: [{ x: 472, y: 181 }, { x: 487, y: 184 }],
  snack: [{ x: 515, y: 182 }, { x: 531, y: 183 }],
};
const STATIONS: Record<string, { label: string; y: number; icon: string; color: string }> = {
  web: { label: "WEB", y: 137, icon: "W", color: "#5fb8ce" },
  files: { label: "FILES", y: 181, icon: "F", color: "#9c83d3" },
  notes: { label: "NOTES", y: 225, icon: "N", color: "#dfb75e" },
  database: { label: "DATA", y: 269, icon: "D", color: "#6fa678" },
  code: { label: "DESK", y: 313, icon: "⌘", color: "#d47e59" },
};
const SKIN = ["#f1c9a4", "#d99d75", "#b97755", "#8f5c45", "#e5b98d", "#c78362", "#f0d1b0", "#a36d51"];
const HAIR = ["#3a2b26", "#5c3828", "#26252d", "#8a5b32", "#4c3436", "#2b201e", "#6a4731", "#312b27"];
const SHIRTS = ["#4f7891", "#718d63", "#b36d54", "#625a86", "#d0a54f", "#487e76", "#a15e75", "#56739b"];

function color(index: number, values: string[]) { return values[(index * 5 + 1) % values.length]; }
function px(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, fill: string) {
  g.fillStyle = fill; g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
}
function label(g: CanvasRenderingContext2D, text: string, x: number, y: number, fill = "#f5eed6", size = 7) {
  g.fillStyle = fill; g.font = `700 ${size}px 'Space Mono', monospace`; g.fillText(text, x, y);
}

function drawWindow(g: CanvasRenderingContext2D, x: number, width: number, t: number, phase: number) {
  const top = 16, height = 72;
  px(g, x - 4, top - 4, width + 8, height + 8, "#583f34");
  const sky = g.createLinearGradient(0, top, 0, top + height);
  const night = phase < 5.5 || phase > 20.5;
  sky.addColorStop(0, night ? "#233858" : phase > 18 ? "#d58773" : "#8ec8d3");
  sky.addColorStop(.68, night ? "#647b9b" : phase > 18 ? "#f2bd83" : "#d0e6d0");
  sky.addColorStop(.69, night ? "#61795d" : "#87b775");
  sky.addColorStop(1, night ? "#385848" : "#53834e");
  px(g, x, top, width, height, "#8ec8d3");
  g.fillStyle = sky; g.fillRect(x, top, width, height);
  // Distant hills, trees and a passing cloud use a low-resolution drawing pass.
  for (let i = 0; i < 7; i++) {
    const bx = x + i * 21 - 4;
    px(g, bx, top + 48 + ((i * 7) % 8), 24, 17, i % 2 ? "#6da267" : "#78ad6c");
    px(g, bx + 5, top + 40 + ((i * 7) % 8), 10, 14, i % 2 ? "#4d7d51" : "#5d8d59");
  }
  const sunX = x + 10 + ((phase / 24) * (width - 30));
  px(g, sunX, top + 12 + Math.sin((phase / 24) * Math.PI) * 8, 10, 10, night ? "#e6e3c2" : "#ffe18d");
  const cloudX = x - 22 + ((t * 7) % (width + 45));
  const cloudY = top + 20 + (x % 3) * 4;
  px(g, cloudX, cloudY, 22, 5, "#f2f0df");
  px(g, cloudX + 4, cloudY - 4, 12, 5, "#f2f0df");
  px(g, cloudX + 17, cloudY + 2, 5, 3, "#f2f0df");
  // Window rails and soft glass glints.
  px(g, x - 3, top + 34, width + 6, 4, "#75523b");
  px(g, x + Math.floor(width / 2) - 2, top - 3, 4, height + 6, "#75523b");
  px(g, x + 9, top + 5, 2, 25, "rgba(255,255,255,.35)");
}

function drawOffice(g: CanvasRenderingContext2D, agents: OfficeAgent[], actors: Map<number, Actor>, selectedId: number | null, focusedId: number | null, t: number, timeMode: number) {
  const liveHour = new Date().getHours() + new Date().getMinutes() / 60;
  const hour = timeMode === 0 ? liveHour : [9.5, 13.5, 18.6, 22][timeMode - 1];
  const night = hour < 6 || hour > 19;
  px(g, 0, 0, W, H, "#dfd2b4");
  // Back wall and windows.
  px(g, 0, 0, W, 108, night ? "#ab9d82" : "#dbc9a7");
  drawWindow(g, 19, 125, t, hour);
  drawWindow(g, 153, 125, t, hour);
  px(g, 300, 12, 3, 84, "#9b7656");
  px(g, 315, 15, 147, 53, "#f0e5c7");
  px(g, 311, 11, 155, 61, "#634735");
  px(g, 315, 15, 147, 53, "#f0e5c7");
  label(g, "CAREERPILOT", 331, 34, "#284635", 12);
  label(g, "LOCAL AI OFFICE", 335, 50, "#777050", 7);
  label(g, timeMode === 0 ? "LIVE" : ["", "MORNING", "AFTERNOON", "SUNSET", "NIGHT"][timeMode], 423, 62, "#88734a", 5);
  px(g, 473, 15, 68, 76, "#8b593d");
  px(g, 479, 21, 56, 64, "#bb9b70");
  label(g, "STAFF", 491, 37, "#fff0cb", 8);
  px(g, 486, 45, 40, 32, "#476b53");
  label(g, "ROOM", 495, 65, "#fff0cb", 7);
  // Wall furnishings and reception.
  px(g, 16, 60, 72, 28, "#765037"); px(g, 20, 64, 64, 20, "#a8754f");
  label(g, "RECEPTION", 24, 77, "#fff2d2", 7);
  px(g, 94, 69, 32, 16, "#718d63");
  label(g, "TEAM BOARD", 95, 65, "#31523f", 6);
  px(g, 135, 68, 21, 18, "#806f52"); px(g, 139, 72, 13, 10, "#d2bd87");
  px(g, 0, 105, W, 255, "#b78355");
  const floorLight = g.createLinearGradient(0, 105, 0, 360);
  floorLight.addColorStop(0, "rgba(63,42,29,.14)");
  floorLight.addColorStop(.38, "rgba(63,42,29,.035)");
  floorLight.addColorStop(1, "rgba(255,229,174,.09)");
  g.fillStyle = floorLight; g.fillRect(0, 105, W, 255);
  // Wood floor as repeating, pixel-sized boards.
  for (let row = 0; row < 11; row++) {
    const y = 108 + row * 23;
    px(g, 0, y, W, 2, "rgba(74,48,32,.32)");
    for (let x = (row % 2) * 31; x < W; x += 64) {
      px(g, x, y + 2, 1, 21, "rgba(74,48,32,.16)");
      px(g, x + 4, y + 6 + (row % 3) * 3, 13 + (row % 4) * 3, 1, "rgba(255,226,176,.12)");
    }
  }
  // A clear corridor connects desks, stations and the break area.
  px(g, 25, 198, 555, 20, "#d1a36d");
  px(g, 25, 198, 555, 2, "rgba(255,236,187,.4)");
  label(g, "WORK FLOOR", 30, 119, "#6b442f", 7);
  label(g, "TEAM LOUNGE", 398, 235, "#6b442f", 7);
  // Eight workstations.
  for (let i = 0; i < DESKS.length; i++) {
    const d = DESKS[i];
    const row = i < 4 ? 0 : 1;
    const y = row === 0 ? 133 : 238;
    const agentWorking = agents[i]?.status === "working";
    const screen = agentWorking ? "#c7f2a2" : i % 2 ? "#8fc9c4" : "#9bc9dc";
    // Chair, broad desk top, monitor, tower, keyboard, and mouse at every station.
    px(g, d.x - 8, y + 24, 16, 4, "#5c7159");
    px(g, d.x - 6, y + 28, 2, 5, "#364b3e"); px(g, d.x + 4, y + 28, 2, 5, "#364b3e");
    px(g, d.x - 33, y + 18, 66, 7, "rgba(53,37,26,.24)");
    px(g, d.x - 31, y + 12, 62, 7, "#a16c45");
    px(g, d.x - 31, y + 18, 62, 7, "#68452e");
    px(g, d.x - 19, y - 23, 38, 28, "#263b35");
    px(g, d.x - 16, y - 20, 32, 21, "#172d2a");
    px(g, d.x - 14, y - 18, 28, 17, screen);
    px(g, d.x - 12, y - 16, 9, 1, "#315b51");
    px(g, d.x - 12, y - 13, 16 + (i % 3) * 3, 1, "#487967");
    px(g, d.x - 12, y - 10, 11 + (i % 4) * 2, 1, "#315b51");
    px(g, d.x - 12, y - 7, 18, 1, "#487967");
    if (agentWorking) px(g, d.x + 9 + Math.floor(Math.sin(t * 8 + i) * 2), y - 7, 2, 2, "#fff4a3");
    px(g, d.x - 4, y + 5, 8, 7, "#59695c"); px(g, d.x - 11, y + 10, 22, 2, "#344a40");
    px(g, d.x + 22, y + 6, 7, 12, "#33483e"); px(g, d.x + 24, y + 8, 3, 5, "#526b5c");
    px(g, d.x + 24, y + 15, 2, 2, agentWorking ? "#8de99c" : "#8caa88");
    px(g, d.x - 13, y + 13, 22, 3, "#34453c");
    for (let key = 0; key < 5; key++) px(g, d.x - 11 + key * 4, y + 14, 2, 1, "#d7cda9");
    px(g, d.x + 13, y + 13, 4, 4, "#ddd2b3");
    px(g, d.x - 7, y + 20, 14, 3, "#315946");
    label(g, String(i + 1).padStart(2, "0"), d.x - 4, y + 22, "#fff0cb", 5);
  }
  // Tools are visible work locations. Their beacon lights when an agent visits.
  label(g, "TOOL STATIONS", 554, 119, "#6b442f", 6);
  const stationed = agents.filter((a) => a.status === "working" || a.status === "visiting").map((a) => a.station);
  for (const [name, station] of Object.entries(STATIONS)) {
    const active = stationed.includes(name);
    px(g, 555, station.y - 12, 69, 35, "#604a3c");
    px(g, 558, station.y - 9, 63, 28, active ? "#eee0b9" : "#d5c5a2");
    px(g, 562, station.y - 5, 19, 19, active ? station.color : "#657b67");
    label(g, station.icon, 568, station.y + 8, "#fff8df", 9);
    label(g, station.label, 585, station.y + 2, "#463c33", 6);
    px(g, 614, station.y - 5, 4, 4, active ? "#6ce39a" : "#8c9881");
  }
  // Lounge furniture: sofa, tables, coffee and plants.
  px(g, 391, 245, 148, 95, "#bca575");
  px(g, 398, 261, 130, 63, "#657b60");
  px(g, 401, 256, 124, 11, "#819476");
  px(g, 396, 289, 14, 32, "#536a58"); px(g, 516, 289, 14, 32, "#536a58");
  px(g, 430, 287, 64, 12, "#78543a"); px(g, 436, 280, 52, 8, "#a57249");
  px(g, 446, 281, 9, 7, "#e4c78b"); px(g, 469, 278, 7, 10, "#f1e1ba");
  px(g, 540, 296, 20, 6, "#735039"); px(g, 545, 278, 9, 18, "#5f8058");
  // Cafeteria counter in the left corner.
  px(g, 10, 293, 94, 48, "#d7bd8c");
  px(g, 15, 307, 77, 8, "#76513a"); px(g, 18, 297, 71, 11, "#b9784e");
  label(g, "CAFE", 37, 305, "#fff2d2", 7);
  px(g, 22, 325, 7, 7, "#f2e1b5"); px(g, 38, 323, 7, 9, "#fff1cf");
  label(g, "☕", 39, 330, "#4f4638", 7);
  // Nearby game table creates a reason for agents to gather.
  px(g, 111, 303, 47, 21, "#523c32"); px(g, 114, 305, 41, 15, "#67919a");
  px(g, 133, 306, 2, 13, "#f4eccf"); px(g, 119, 309, 7, 5, "#f2e1ad");
  label(g, "ARCADE", 117, 335, "#65462f", 6);
  // Staff room refreshment counter with a kettle and a shared snack plate.
  px(g, 466, 119, 80, 5, "rgba(53,37,26,.24)");
  px(g, 469, 111, 75, 8, "#78543a"); px(g, 473, 101, 66, 10, "#d7bd8c");
  px(g, 480, 103, 15, 8, "#405e50"); px(g, 483, 99, 8, 5, "#405e50");
  px(g, 488, 96 + Math.sin(t * 4) * 2, 2, 5, "rgba(255,255,255,.6)");
  px(g, 503, 103, 20, 4, "#f3e9cf"); px(g, 505, 100, 5, 4, "#c9794f");
  px(g, 513, 99, 5, 5, "#d7a357"); px(g, 520, 101, 4, 3, "#9d6344");
  label(g, "STAFF ROOM · TEA & SNACKS", 463, 132, "#fff1cf", 5);
  px(g, 467, 138, 78, 2, "#6a4934");
  // Daylight moves across the room as the live sun travels past the windows.
  const daylight = Math.max(0, Math.sin(((hour - 6) / 13) * Math.PI));
  if (daylight > 0.04) {
    g.fillStyle = `rgba(255, 226, 145, ${0.035 + daylight * 0.055})`;
    g.beginPath(); g.moveTo(65, 105); g.lineTo(174, 105); g.lineTo(265 + Math.sin(t / 18) * 44, 355); g.lineTo(16 + Math.sin(t / 18) * 25, 355); g.closePath(); g.fill();
  }
  // Actors sit or stand at the point implied by their current activity.
  agents.forEach((agent, i) => {
    const actor = actors.get(agent.id);
    if (!actor) return;
    const walking = actor.path.length > 0;
    const seated = !walking && !actor.breakKind && Math.hypot(actor.x - actor.home.x, actor.y - actor.home.y) < 3;
    const portraitY = actor.y - (seated ? 18 : 0);
    const activeBrain = agent.status === "working";
    const brainColor = activeBrain ? (Math.sin(t * 5 + i) > 0 ? "#ed9db0" : "#ca7188") : "#80c49a";
    drawPerson(g, seated ? { ...actor, y: portraitY } : actor, i, walking, seated, selectedId === agent.id || (!selectedId && focusedId === agent.id), t);
    const job = agent.name.length > 14 ? `${agent.name.slice(0, 13)}…` : agent.name;
    const personY = portraitY - 57 - Math.sin(t * 5 + i) * (walking ? 0 : .6);
    px(g, actor.x - job.length * 2.7 - 5, personY - 10, job.length * 5.4 + 10, 13, selectedId === agent.id ? "#f5dd8e" : "rgba(38,48,39,.9)");
    label(g, job, actor.x - job.length * 2.7, personY - 1, selectedId === agent.id ? "#3b372a" : "#f6f0d8", 6.5);

    if (agent.status === "chatting" && selectedId === agent.id) {
      px(g, actor.x - 20, portraitY - 54, 10, 9, "#fff0ba");
      label(g, "!", actor.x - 17, portraitY - 47, "#315946", 7);
    }
    if (agent.status === "working" && seated && agent.phase) {
      const bx = actor.x - 43, by = portraitY - 97;
      const dots = ".".repeat(1 + (Math.floor(t * 2 + i) % 3));
      px(g, bx, by, 86, 24, "#fff4d2");
      px(g, bx, by, 86, 2, activeBrain ? brainColor : "#ca7188"); px(g, bx, by + 22, 86, 2, "#315946");
      px(g, bx, by, 2, 24, "#315946"); px(g, bx + 84, by, 2, 24, "#315946");
      label(g, `THINK ${((agent.stepIndex || 0) + 1)}/${agent.stepCount || 1}${dots}`, bx + 5, by + 9, "#426149", 4.5);
      label(g, agent.phase.slice(0, 21), bx + 5, by + 18, "#294737", 5);
      px(g, actor.x - 1, by + 24, 2, 4, "#ca7188"); px(g, actor.x - 1, by + 28, 2, 3, "#fff4d2");
    }
    if (actor.breakKind && actor.mode === "idle" && actor.path.length === 0) {
      const bx = actor.x - 39, by = actor.y - 49;
      px(g, bx, by, 27, 15, "#fff4d2"); px(g, bx, by, 27, 2, "#49624c");
      if (actor.breakKind === "tea") {
        px(g, bx + 5, by + 6, 9, 5, "#f5f0de"); px(g, bx + 14, by + 7, 3, 3, "#f5f0de");
        px(g, bx + 6, by + 12, 12, 1, "#80563e");
        px(g, bx + 7, by + 3 - Math.round(Math.sin(t * 5 + i) * 1), 1, 2, "#aa9071");
        label(g, "TEA", bx + 19, by + 10, "#426149", 5);
      } else if (actor.breakKind === "snack") {
        px(g, bx + 5, by + 5, 9, 8, "#d99a50"); px(g, bx + 7, by + 3, 5, 2, "#e9ba70");
        px(g, bx + 8, by + 7, 2, 2, "#80563e"); px(g, bx + 12, by + 10, 2, 2, "#80563e");
        label(g, "YUM", bx + 16, by + 10, "#426149", 5);
      } else {
        label(g, "BREAK", bx + 3, by + 10, "#426149", 5);
      }
    }
  });
  // The front edge of each table passes in front of seated agents.
  for (let i = 0; i < DESKS.length; i++) {
    const desk = DESKS[i], rowY = i < 4 ? 133 : 238;
    const actor = agents[i] ? actors.get(agents[i].id) : undefined;
    if (!actor || Math.hypot(actor.x - desk.x, actor.y - desk.y) > 4) continue;
    px(g, desk.x - 31, rowY + 12, 62, 7, "#a16c45");
    px(g, desk.x - 33, rowY + 18, 66, 7, "#68452e");
    // Monitor foreground sits between the seated avatar and the viewer, just below the face.
    px(g, desk.x - 20, rowY - 31, 40, 31, "#263b35");
    px(g, desk.x - 17, rowY - 28, 34, 23, "#172d2a");
    px(g, desk.x - 15, rowY - 26, 30, 19, actor.mode === "working" ? "#c7f2a2" : i % 2 ? "#8fc9c4" : "#9bc9dc");
    px(g, desk.x - 13, rowY - 24, 9, 1, "#315b51");
    px(g, desk.x - 13, rowY - 21, 17 + (i % 3) * 2, 1, "#487967");
    px(g, desk.x - 13, rowY - 18, 12 + (i % 4) * 2, 1, "#315b51");
    px(g, desk.x - 13, rowY - 15, 20, 1, "#487967");
    if (actor.mode === "working") px(g, desk.x + 10 + Math.floor(Math.sin(t * 8 + i) * 2), rowY - 15, 2, 2, "#fff4a3");
    px(g, desk.x - 4, rowY - 5, 8, 17, "#59695c"); px(g, desk.x - 12, rowY + 10, 24, 2, "#344a40");
    px(g, desk.x + 22, rowY + 6, 7, 12, "#33483e");
    px(g, desk.x + 24, rowY + 8, 3, 5, "#526b5c");
    px(g, desk.x + 24, rowY + 15, 2, 2, actor.mode === "working" ? "#8de99c" : "#8caa88");
    px(g, desk.x - 13, rowY + 13, 22, 3, "#34453c");
    for (let key = 0; key < 5; key++) px(g, desk.x - 11 + key * 4, rowY + 14, 2, 1, "#d7cda9");
    px(g, desk.x + 13, rowY + 13, 4, 4, "#ddd2b3");
    const typing = actor.mode === "working" ? Math.round(Math.sin(t * 15 + i)) : 0;
    px(g, desk.x - 8, desk.y - 15 + typing, 3, 2, color(i, SKIN));
    px(g, desk.x + 5, desk.y - 15 - typing, 3, 2, color(i, SKIN));
    px(g, desk.x - 7, rowY + 20, 14, 3, "#315946");
    label(g, String(i + 1).padStart(2, "0"), desk.x - 4, rowY + 22, "#fff0cb", 5);
  }
  // Keep every animated brain visible in front of the desk equipment and tied to its avatar.
  const activeAgents = agents.filter((agent) => agent.status === "working");
  const waitingAgents = agents.filter((agent) => agent.status === "queued");
  if (activeAgents.length && waitingAgents.length) {
    g.save();
    g.strokeStyle = "rgba(116, 224, 180, .72)";
    g.shadowColor = "#73e2b1";
    g.shadowBlur = 9;
    g.lineWidth = 1.5;
    g.setLineDash([3, 3]);
    for (const active of activeAgents) {
      const source = actors.get(active.id);
      if (!source) continue;
      for (const waiting of waitingAgents) {
        const target = actors.get(waiting.id);
        if (!target) continue;
        g.beginPath();
        g.moveTo(source.x + 11, source.y - 48);
        g.lineTo(target.x + 11, target.y - 48);
        g.stroke();
      }
    }
    g.restore();
  }
  agents.forEach((agent, i) => {
    const actor = actors.get(agent.id);
    if (!actor) return;
    const walking = actor.path.length > 0;
    const seated = !walking && !actor.breakKind && Math.hypot(actor.x - actor.home.x, actor.y - actor.home.y) < 3;
    const portraitY = actor.y - (seated ? 18 : 0);
    const bx = actor.x + 11, by = portraitY - 53;
    const brainColor = agent.status === "working"
      ? Math.sin(t * 5 + i) > 0 ? "#ed9db0" : "#ca7188"
      : agent.status === "failed" ? "#d75a58" : actor.breakKind ? "#edc778" : "#80c49a";
    px(g, bx + 5, by, 6, 2, brainColor);
    px(g, bx + 3, by + 2, 10, 3, brainColor);
    px(g, bx + 1, by + 5, 14, 5, brainColor);
    px(g, bx + 3, by + 10, 10, 3, brainColor);
    px(g, bx + 5, by + 13, 6, 2, brainColor);
    px(g, bx + 8, by + 2, 1, 12, "#f8f1d8");
    if (Math.sin(t * 7 + i) > 0) px(g, bx + 3, by + 4, 2, 2, "#fff2c9");
    if (Math.sin(t * 6 + i * 2) > 0) px(g, bx + 11, by + 8, 2, 2, "#fff2c9");
    px(g, actor.x + 6, by + 5, 6, 2, "#54715a");
    if (agent.status === "completed") label(g, "✓", bx + 16, by + 10, "#2e9a65", 10);
    if (agent.status === "failed") label(g, "!", bx + 16, by + 10, "#bd3434", 10);
  });
  // Warm room lamps are visible in the evening.
  if (night) {
    for (const x of [125, 260, 390, 520]) {
      px(g, x, 105, 18, 2, "#4c443a"); px(g, x + 6, 107, 6, 5, "#edc671");
      g.fillStyle = "rgba(255, 219, 143, .045)"; g.beginPath(); g.moveTo(x + 2, 112); g.lineTo(x + 17, 112); g.lineTo(x + 50, 252); g.lineTo(x - 32, 252); g.fill();
    }
  }
}

function drawPerson(g: CanvasRenderingContext2D, actor: Actor, index: number, walking: boolean, seated: boolean, selected: boolean, t: number) {
  const x = Math.round(actor.x), y = Math.round(actor.y);
  const bounce = walking ? 0 : Math.round(Math.sin(t * 3 + index * 1.7) * 1);
  const skin = color(index, SKIN), hair = color(index, HAIR), shirt = color(index, SHIRTS);
  const working = actor.mode === "working";
  const step = walking ? Math.round(Math.sin(t * 12 + index) * 3) : 0;
  const typing = working ? Math.round(Math.sin(t * 15 + index) * 2) : 0;
  // Give each small sprite more screen area so faces and clothing read clearly.
  g.save();
  g.translate(x, y);
  g.scale(1.35, 1.35);
  // Floor shadow and selection ring are for people away from their seated desks.
  if (!seated) {
    px(g, -9, -2, 18, 3, "rgba(43,39,31,.32)");
    if (selected) { px(g, -13, -4, 26, 1, "#f7df82"); px(g, -13, -1, 26, 1, "#f7df82"); px(g, -13, -4, 1, 4, "#f7df82"); px(g, 12, -4, 1, 4, "#f7df82"); }
  }
  // Seated teammates tuck their legs behind the desk; visitors keep the walking pose.
  if (!seated) {
    px(g, -6 + Math.min(0, step), -12 + bounce, 5, 8, "#394b54");
    px(g, 1 + Math.max(0, step), -12 + bounce, 5, 8, "#394b54");
    px(g, -7 + Math.min(0, step), -4 + bounce, 7, 2, "#332c28");
    px(g, Math.max(0, step), -4 + bounce, 7, 2, "#332c28");
  }
  // Body, collar, arms and hands.
  px(g, -7, -24 + bounce, 14, 12, shirt);
  px(g, -8, -21 + bounce + (walking ? step : working ? typing : 0), 3, 9, shirt);
  px(g, 5, -21 + bounce - (walking ? step : working ? typing : 0), 3, 9, shirt);
  px(g, -8, -13 + bounce + (walking ? step : working ? typing : 0), 3, 3, skin);
  px(g, 5, -13 + bounce - (walking ? step : working ? typing : 0), 3, 3, skin);
  px(g, -2, -23 + bounce, 4, 3, "#f2e5d0");
  px(g, -6, -24 + bounce, 2, 10, "rgba(255,255,255,.2)");
  // Neck, face and hair; varied palettes keep the crew distinct without emoji dolls.
  px(g, -2, -28 + bounce, 5, 5, skin);
  px(g, -6, -38 + bounce, 12, 11, skin);
  px(g, -6, -40 + bounce, 12, 5, hair);
  px(g, -8, -36 + bounce, 3, 7, hair);
  px(g, 5, -36 + bounce, 3, 5, hair);
  px(g, -4, -33 + bounce, 1, 1, "#272b29");
  px(g, 2, -33 + bounce, 1, 1, "#272b29");
  px(g, -2, -29 + bounce, 3, 1, "#9c5f50");
  // Shoulder badge.
  px(g, 3, -21 + bounce, 2, 3, "#f3d57f");
  g.restore();
}

function getTarget(agent: OfficeAgent, index: number): Point {
  if (agent.status === "idle" || agent.status === "working") return DESKS[index % DESKS.length];
  if (agent.status === "visiting") {
    const station = STATIONS[(agent.station || "").toLowerCase()];
    return station ? { x: 540, y: station.y + 5 } : DESKS[index % DESKS.length];
  }
  if (agent.status === "queued") return { x: 387 + (index % 4) * 29, y: 222 + Math.floor(index / 4) * 14 };
  return DESKS[index % DESKS.length];
}

function route(from: Point, to: Point): Point[] {
  if (Math.hypot(from.x - to.x, from.y - to.y) < 3) return [];
  const path: Point[] = [];
  if (Math.abs(from.y - 208) > 3) path.push({ x: from.x, y: 208 });
  if (Math.abs(from.x - to.x) > 3) path.push({ x: to.x, y: 208 });
  path.push(to);
  return path;
}

export default function OfficeScene({ agents, selectedId, onAgentClick, onStationClick, onTimeClick }: OfficeSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const actorsRef = useRef(new Map<number, Actor>());
  const agentsRef = useRef(agents);
  const selectedRef = useRef(selectedId);
  const stationClickRef = useRef(onStationClick);
  const timeModeRef = useRef(0);
  const focusedIdRef = useRef<number | null>(null);
  agentsRef.current = agents;
  selectedRef.current = selectedId;
  stationClickRef.current = onStationClick;

  useEffect(() => {
    const actors = actorsRef.current;
    agents.forEach((agent, index) => {
      let actor = actors.get(agent.id);
      const target = getTarget(agent, index);
      if (!actor) {
        const home = DESKS[index % DESKS.length];
        actor = { x: home.x, y: home.y, target, path: [], mode: "idle", step: 0, blink: 0, bob: index, home, wanderAt: performance.now() / 1000 + 30 + index * 10, returnAt: 0, wandering: false, breakKind: null };
        actors.set(agent.id, actor);
      }
      if (actor.mode !== agent.status || actor.station !== agent.station) {
        actor.path = route({ x: actor.x, y: actor.y }, target);
        actor.mode = agent.status;
        actor.station = agent.station;
        actor.target = target;
        actor.wandering = false;
        actor.returnAt = 0;
        actor.breakKind = null;
      }
    });
  }, [agents]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const g = canvas?.getContext("2d");
    if (!canvas || !g) return;
    let raf = 0;
    let lastDraw = 0;
    const hitTargets = { agents: [] as { id: number; x: number; y: number }[], stations: [] as { name: string; x: number; y: number }[] };
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden || now - lastDraw < 40) return;
      const dt = Math.min(.08, (now - (lastDraw || now)) / 1000);
      lastDraw = now;
      for (const [actorId, actor] of actorsRef.current) {
        const index = agentsRef.current.findIndex((item) => item.id === actorId);
        const seconds = now / 1000;
        if (actor.mode === "idle" && actor.path.length === 0) {
          if (actor.wandering && seconds >= actor.returnAt) {
            actor.wandering = false;
            actor.breakKind = null;
            actor.path = route({ x: actor.x, y: actor.y }, actor.home);
            actor.wanderAt = seconds + 70 + (index % 5) * 20;
          } else if (!actor.wandering && seconds >= actor.wanderAt) {
            actor.wandering = true;
            const cycle = Math.floor(seconds / 24 + index);
            const kind = (["staff", "tea", "snack"] as const)[cycle % 3];
            actor.breakKind = kind;
            const spots = BREAK_SPOTS[kind];
            const stop = spots[index % spots.length];
            actor.path = route({ x: actor.x, y: actor.y }, stop);
            actor.returnAt = seconds + 18 + (index % 3) * 3;
          }
        }
        if (actor.path.length) {
          const next = actor.path[0];
          const dx = next.x - actor.x, dy = next.y - actor.y, dist = Math.hypot(dx, dy);
          const travel = 75 * dt;
          if (dist <= travel + 1) { actor.x = next.x; actor.y = next.y; actor.path.shift(); }
          else { actor.x += dx / dist * travel; actor.y += dy / dist * travel; }
        }
      }
      g.imageSmoothingEnabled = false;
      // The backing canvas is doubled for crisp pixels; draw in the 640×360
      // logical coordinate space so the room fills the displayed canvas.
      g.setTransform(2, 0, 0, 2, 0, 0);
      drawOffice(g, agentsRef.current, actorsRef.current, selectedRef.current, focusedIdRef.current, now / 1000, timeModeRef.current);
      hitTargets.agents = agentsRef.current.flatMap((agent) => {
        const actor = actorsRef.current.get(agent.id);
        return actor ? [{ id: agent.id, x: actor.x, y: actor.y }] : [];
      });
      hitTargets.stations = Object.entries(STATIONS).map(([name, station]) => ({ name, x: 589, y: station.y }));
    };
    raf = requestAnimationFrame(frame);
    const onClick = (event: MouseEvent) => {
      const bounds = canvas.getBoundingClientRect();
      const scale = Math.min(bounds.width / W, bounds.height / H);
      const drawnWidth = W * scale, drawnHeight = H * scale;
      const left = bounds.left + (bounds.width - drawnWidth) / 2;
      const top = bounds.top + (bounds.height - drawnHeight) / 2;
      const x = (event.clientX - left) / scale;
      const y = (event.clientY - top) / scale;
      if (x < 0 || x > W || y < 0 || y > H) return;
      const actor = hitTargets.agents.find((item) => Math.abs(item.x - x) < 15 && Math.abs(item.y - y) < 28);
      if (actor) { focusedIdRef.current = actor.id; onAgentClick(actor.id); return; }
      if (x > 550 && y > 120) {
        const station = hitTargets.stations.find((item) => Math.abs(item.y - y) < 17);
        if (station) { stationClickRef.current(station.name); return; }
      }
      if (y < 100 && x < 285) {
        timeModeRef.current = (timeModeRef.current + 1) % 5;
        onTimeClick();
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (!agentsRef.current.length) return;
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
        event.preventDefault();
        const current = agentsRef.current.findIndex((agent) => agent.id === focusedIdRef.current);
        const direction = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
        const next = (current + direction + agentsRef.current.length) % agentsRef.current.length;
        focusedIdRef.current = agentsRef.current[next].id;
      } else if ((event.key === "Enter" || event.key === " ") && focusedIdRef.current !== null) {
        event.preventDefault(); onAgentClick(focusedIdRef.current);
      }
    };
    canvas.addEventListener("click", onClick);
    canvas.addEventListener("keydown", onKeyDown);
    return () => { cancelAnimationFrame(raf); canvas.removeEventListener("click", onClick); canvas.removeEventListener("keydown", onKeyDown); };
  }, [onAgentClick, onTimeClick]);

  return (
    <canvas
      ref={canvasRef}
      className="office-canvas"
      width={W * 2}
      height={H * 2}
      tabIndex={0}
      role="application"
      aria-label="CareerPilot pixel office. Click an agent to talk, a tool station to inspect it, or a window to change the time."
      title="Click an agent to talk · click a tool station to inspect it · click a window to change the time"
    />
  );
}
