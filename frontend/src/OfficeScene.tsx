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
  wanderAt: number; returnAt: number; wandering: boolean; breakKind: "staff" | "tea" | "snack" | "game" | "lounge" | "cafe" | null;
  breakSpotIndex: number;
};

const W = 640;
const H = 360;
const DESKS: Point[] = [
  { x: 72, y: 162 }, { x: 145, y: 162 }, { x: 218, y: 162 }, { x: 291, y: 162 },
  { x: 72, y: 267 }, { x: 145, y: 267 }, { x: 218, y: 267 }, { x: 291, y: 267 },
];
const BREAK_KINDS = ["game", "lounge", "cafe", "tea", "snack", "staff"] as const;
const BREAK_SPOTS: Record<(typeof BREAK_KINDS)[number], Point[]> = {
  staff: [{ x: 490, y: 174 }, { x: 520, y: 176 }],
  tea: [{ x: 472, y: 181 }, { x: 487, y: 184 }],
  snack: [{ x: 515, y: 182 }, { x: 531, y: 183 }],
  game: [{ x: 164, y: 322 }, { x: 178, y: 322 }],
  lounge: [{ x: 432, y: 305 }, { x: 484, y: 305 }],
  cafe: [{ x: 43, y: 322 }, { x: 79, y: 322 }],
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
const AGENT_NAME_COLORS = ["#62e0c3", "#d4a6ff", "#ff9db1", "#8ed1ff", "#ffdc77", "#ffab87", "#a6e89a", "#a9baff"];
const WORKSTATIONS = [
  { top: "#c98653", front: "#794b32", bezel: "#4e3547", accent: "#ffbd68", screen: "#a8d2df", ink: "#456879" },
  { top: "#4a9b91", front: "#28645f", bezel: "#254956", accent: "#83e3cf", screen: "#a9d6ce", ink: "#3d6b68" },
  { top: "#8970b0", front: "#59467d", bezel: "#3f345f", accent: "#d4a6ff", screen: "#c6b8df", ink: "#63537f" },
  { top: "#d5a342", front: "#8c682c", bezel: "#544325", accent: "#ffdc77", screen: "#e5d59e", ink: "#766334" },
  { top: "#568ab4", front: "#345c7b", bezel: "#2c405f", accent: "#8ed1ff", screen: "#a9cde1", ink: "#496c91" },
  { top: "#75a266", front: "#4b704b", bezel: "#344c3b", accent: "#a6e89a", screen: "#bdd6ac", ink: "#55714b" },
  { top: "#bd7186", front: "#7e4d60", bezel: "#573847", accent: "#ff9db1", screen: "#e6bac8", ink: "#805369" },
  { top: "#d27d51", front: "#894d34", bezel: "#50352c", accent: "#ffab87", screen: "#e8c0a8", ink: "#80533e" },
];

function color(index: number, values: string[]) { return values[(index * 5 + 1) % values.length]; }
function px(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, fill: string) {
  g.fillStyle = fill; g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
}
function label(g: CanvasRenderingContext2D, text: string, x: number, y: number, fill = "#f5eed6", size = 7) {
  g.fillStyle = fill; g.font = `700 ${size}px 'Space Mono', monospace`; g.fillText(text, x, y);
}

function drawToolIcon(g: CanvasRenderingContext2D, name: string, x: number, y: number, active: boolean, t: number) {
  const frame = active ? STATIONS[name].color : "#68715f";
  px(g, x, y, 19, 19, "#493c34");
  if (name === "files") {
    // Compact filing cabinet with hanging folders, tabs, and paper labels.
    px(g, x + 2, y + 3, 15, 13, "#8b7257"); px(g, x + 3, y + 4, 13, 10, "#d4c39f");
    px(g, x + 4, y + 7, 3, 7, "#6d9fba"); px(g, x + 8, y + 6, 3, 8, "#d38958"); px(g, x + 12, y + 8, 3, 6, "#78a58a");
    px(g, x + 4, y + 5, 2, 2, "#f6e9c7"); px(g, x + 8, y + 4, 2, 2, "#f6e9c7"); px(g, x + 12, y + 6, 2, 2, "#f6e9c7");
    px(g, x + 4, y + 9, 2, 1, "#e2eff2"); px(g, x + 8, y + 9, 2, 1, "#f3dec0"); px(g, x + 12, y + 10, 2, 1, "#e1eee2");
    px(g, x + 2, y + 15, 15, 2, "#5d4a3b"); px(g, x + 8, y + 15, 4, 1, "#f0d99a");
  } else if (name === "notes") {
    px(g, x + 2, y + 15, 15, 2, "#d5c7a6");
    px(g, x + 3, y + 5, 4, 10, "#d66c58"); px(g, x + 8, y + 3, 4, 12, "#7197bd"); px(g, x + 13, y + 6, 3, 9, "#d6b35e");
    px(g, x + 4, y + 6, 1, 8, "#f4d0b3"); px(g, x + 9, y + 4, 1, 10, "#d6e1ec"); px(g, x + 14, y + 7, 1, 7, "#fae8aa");
  } else if (name === "database") {
    for (let layer = 0; layer < 3; layer++) {
      const yy = y + 3 + layer * 5;
      g.fillStyle = layer === 0 ? "#73b99a" : "#4c8c85";
      g.beginPath(); g.ellipse(x + 9.5, yy + 2, 7, 2.2, 0, 0, Math.PI * 2); g.fill();
      px(g, x + 2, yy + 2, 15, 3, layer === 0 ? "#73b99a" : "#4c8c85");
      g.beginPath(); g.ellipse(x + 9.5, yy + 5, 7, 2.2, 0, 0, Math.PI); g.fill();
      px(g, x + 4, yy + 1, 3, 1, "#c4f1c5");
    }
  } else if (name === "web") {
    px(g, x + 3, y + 3, 13, 13, "#65bbd0"); px(g, x + 5, y + 5, 9, 9, "#376783");
    px(g, x + 8, y + 4, 3, 11, "#c9e9dd"); px(g, x + 4, y + 8, 11, 2, "#c9e9dd");
  } else {
    px(g, x + 2, y + 3, 15, 12, "#212944"); px(g, x + 4, y + 5, 11, 8, "#314b68");
    label(g, "</>", x + 4, y + 11, active ? "#b9ff85" : "#b8d4e8", 5.5);
    px(g, x + 8, y + 15, 4, 1, frame);
  }
  if (active) px(g, x + 15, y + 1 + Math.floor(Math.sin(t * 6) * 1), 3, 3, frame);
}

function drawSharedBrain(g: CanvasRenderingContext2D, agents: OfficeAgent[], actors: Map<number, Actor>, t: number) {
  const core = { x: 27, y: 43 };
  g.save();
  g.lineWidth = 1;
  g.setLineDash([1, 3]);
  g.lineDashOffset = -t * 9;
  agents.forEach((agent, index) => {
    const actor = actors.get(agent.id);
    if (!actor) return;
    const seated = (!actor.path.length && !actor.breakKind && Math.hypot(actor.x - actor.home.x, actor.y - actor.home.y) < 3)
      || (!actor.path.length && actor.breakKind === "lounge");
    const portraitY = actor.y - (seated ? 18 : 0);
    const target = { x: actor.x + 19, y: portraitY - 45 };
    const laneY = target.y < 150 ? 107 : 210;
    g.strokeStyle = agent.status === "working" ? "rgba(52,115,81,.78)" : `rgba(75,83,91,${.38 + (index % 2) * .08})`;
    g.beginPath();
    g.moveTo(core.x, core.y);
    g.lineTo(core.x, laneY);
    g.lineTo(target.x, laneY);
    g.lineTo(target.x, target.y);
    g.stroke();
    px(g, target.x - 1, target.y - 1, 3, 3, agent.status === "working" ? "#67c981" : "#7b8ca1");
  });
  g.restore();

  // Career Assistant's shared neural core in the upper-left office corner.
  px(g, 3, 8, 49, 83, "#583f34");
  px(g, 6, 11, 43, 77, "#f0e5c7");
  label(g, "CAREER AI", 9, 21, "#315946", 5.2);
  const pulse = Math.sin(t * 3) > 0 ? "#5e68a8" : "#347f70";
  px(g, 22, 25, 10, 2, pulse); px(g, 18, 27, 18, 3, pulse);
  px(g, 15, 30, 24, 8, pulse); px(g, 18, 38, 18, 4, pulse); px(g, 22, 42, 10, 2, pulse);
  px(g, 26, 27, 1, 16, "#f0e5c7");
  for (const [x, y] of [[19,32],[23,29],[31,31],[18,36],[29,37],[25,40]]) px(g, x, y, 2, 2, "#f0e5c7");
  label(g, "SHARED BRAIN", 8, 54, "#315946", 4.2);
  label(g, "CAREER ASSIST", 7, 63, "#6b5a49", 3.7);
  for (let i = 0; i < 8; i++) px(g, 10 + i * 4, 73, 2, 2, i < agents.length ? "#438653" : "#b5a989");
  label(g, "8 LIVE LINKS", 9, 83, "#6b5a49", 4);
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
  px(g, 0, 0, W, 108, night ? "#78876c" : "#b8c69f");
  drawWindow(g, 62, 108, t, hour);
  drawWindow(g, 180, 108, t, hour);
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
  px(g, 0, 105, W, 255, "#a59a8c");
  const floorLight = g.createLinearGradient(0, 105, 0, 360);
  floorLight.addColorStop(0, "rgba(53,48,44,.14)");
  floorLight.addColorStop(.38, "rgba(53,48,44,.035)");
  floorLight.addColorStop(1, "rgba(255,244,225,.12)");
  g.fillStyle = floorLight; g.fillRect(0, 105, W, 255);
  // Wood floor as repeating, pixel-sized boards.
  for (let row = 0; row < 11; row++) {
    const y = 108 + row * 23;
    px(g, 0, y, W, 2, "rgba(67,61,55,.3)");
    for (let x = (row % 2) * 31; x < W; x += 64) {
      px(g, x, y + 2, 1, 21, "rgba(67,61,55,.13)");
      px(g, x + 4, y + 6 + (row % 3) * 3, 13 + (row % 4) * 3, 1, "rgba(255,244,225,.16)");
    }
  }
  // A clear corridor connects desks, stations and the break area.
  px(g, 25, 198, 555, 20, "#c0b3a2");
  px(g, 25, 198, 555, 2, "rgba(255,249,237,.46)");
  label(g, "WORK FLOOR", 30, 119, "#6b442f", 7);
  label(g, "TEAM LOUNGE", 398, 235, "#6b442f", 7);
  // Eight workstations.
  for (let i = 0; i < DESKS.length; i++) {
    const d = DESKS[i];
    const style = WORKSTATIONS[i % WORKSTATIONS.length];
    const row = i < 4 ? 0 : 1;
    const y = row === 0 ? 133 : 238;
    const agentWorking = agents[i]?.status === "working";
    const screen = agentWorking ? "#c7f2a2" : style.screen;
    // Chair, broad desk top, monitor, tower, keyboard, and mouse at every station.
    px(g, d.x - 8, y + 24, 16, 4, "#5c7159");
    px(g, d.x - 6, y + 28, 2, 5, "#364b3e"); px(g, d.x + 4, y + 28, 2, 5, "#364b3e");
    px(g, d.x - 33, y + 18, 66, 7, "rgba(53,37,26,.24)");
    px(g, d.x - 31, y + 12, 62, 7, style.top);
    px(g, d.x - 31, y + 18, 62, 7, style.front);
    px(g, d.x - 19, y - 23, 38, 28, style.bezel);
    px(g, d.x - 16, y - 20, 32, 21, "#172d2a");
    px(g, d.x - 14, y - 18, 28, 17, screen);
    px(g, d.x - 12, y - 16, 9, 1, style.accent);
    px(g, d.x - 12, y - 13, 16 + (i % 3) * 3, 1, style.ink);
    px(g, d.x - 12, y - 10, 11 + (i % 4) * 2, 1, style.accent);
    px(g, d.x - 12, y - 7, 18, 1, style.ink);
    // Tiny chart column and blinking cursor make each screen feel active.
    px(g, d.x + 8, y - 17, 2, 3 + (i % 3) * 2, style.accent);
    px(g, d.x + 11, y - 17, 2, 5 + (i % 2) * 2, style.ink);
    px(g, d.x + 14, y - 17, 2, 2 + (i % 4), style.accent);
    if (agentWorking) px(g, d.x + 7 + Math.floor(Math.sin(t * 8 + i) * 2), y - 7, 2, 2, "#fff4a3");
    px(g, d.x - 4, y + 5, 8, 7, "#59695c"); px(g, d.x - 11, y + 10, 22, 2, "#344a40");
    px(g, d.x + 22, y + 6, 7, 12, "#33483e"); px(g, d.x + 24, y + 8, 3, 5, "#526b5c");
    px(g, d.x + 24, y + 15, 2, 2, agentWorking ? "#8de99c" : "#8caa88");
    px(g, d.x - 13, y + 13, 22, 3, style.bezel);
    for (let key = 0; key < 5; key++) px(g, d.x - 11 + key * 4, y + 14, 2, 1, "#e7d9bd");
    px(g, d.x + 13, y + 13, 4, 4, style.accent);
    px(g, d.x - 7, y + 20, 14, 3, style.front);
    label(g, String(i + 1).padStart(2, "0"), d.x - 4, y + 22, "#fff0cb", 5);
  }
  // Tools are visible work locations. Their beacon lights when an agent visits.
  label(g, "TOOL STATIONS", 554, 119, "#6b442f", 6);
  const stationed = agents.filter((a) => a.status === "working" || a.status === "visiting").map((a) => a.station);
  for (const [name, station] of Object.entries(STATIONS)) {
    const active = stationed.includes(name);
    px(g, 555, station.y - 12, 69, 35, "#604a3c");
    px(g, 558, station.y - 9, 63, 28, active ? "#eee0b9" : "#d5c5a2");
    drawToolIcon(g, name, 562, station.y - 5, active, t);
    label(g, station.label, 585, station.y + 2, active ? station.color : "#463c33", 6);
    px(g, 614, station.y - 5, 4, 4, active ? "#6ce39a" : "#8c9881");
  }
  // Lounge: layered rug and a furnished sofa with arms, cushion seams, and feet.
  px(g, 391, 245, 148, 95, "#bca575");
  px(g, 398, 327, 132, 5, "rgba(50,39,31,.28)");
  px(g, 404, 318, 7, 9, "#76543b"); px(g, 515, 318, 7, 9, "#76543b");
  px(g, 398, 267, 130, 56, "#657b60");
  px(g, 396, 262, 14, 49, "#536a58"); px(g, 516, 262, 14, 49, "#536a58");
  px(g, 400, 252, 122, 25, "#526b59");
  px(g, 404, 256, 54, 18, "#819476"); px(g, 463, 256, 54, 18, "#819476");
  px(g, 458, 256, 2, 18, "#536a58");
  px(g, 403, 278, 56, 36, "#789071"); px(g, 463, 278, 54, 36, "#789071");
  px(g, 458, 280, 3, 32, "#52694f");
  px(g, 414, 260, 17, 11, "#e1bf72"); px(g, 417, 262, 11, 7, "#f2d993");
  px(g, 480, 261, 18, 10, "#bc7880"); px(g, 483, 263, 12, 6, "#d8999d");
  px(g, 430, 287, 64, 12, "#78543a"); px(g, 436, 280, 52, 8, "#a57249");
  px(g, 446, 281, 9, 7, "#e4c78b"); px(g, 469, 278, 7, 10, "#f1e1ba");
  px(g, 540, 296, 20, 6, "#735039"); px(g, 545, 278, 9, 18, "#5f8058");
  // Cafeteria counter in the left corner.
  px(g, 10, 293, 94, 48, "#d7bd8c");
  px(g, 15, 307, 77, 8, "#76513a"); px(g, 18, 297, 71, 11, "#b9784e");
  label(g, "CAFE", 37, 305, "#fff2d2", 7);
  px(g, 22, 325, 7, 7, "#f2e1b5"); px(g, 38, 323, 7, 9, "#fff1cf");
  label(g, "☕", 39, 330, "#4f4638", 7);
  // Arcade cabinet with a pulsing game screen; idle agents walk here to play.
  px(g, 111, 293, 47, 38, "#42304f"); px(g, 114, 296, 41, 31, "#755293");
  px(g, 118, 299, 33, 18, "#171d38");
  px(g, 121, 302, 7, 2, "#62c6dd"); px(g, 133, 304, 8, 2, "#e66a91");
  px(g, 124 + Math.floor(Math.sin(t * 7) * 5), 308, 3, 3, "#ffe16f");
  px(g, 119, 320, 8, 3, "#df5f83"); px(g, 139, 320, 3, 3, "#f3d674"); px(g, 146, 320, 3, 3, "#8addaa");
  label(g, "GAME", 121, 315, "#f5d5ff", 5); label(g, "ARCADE", 117, 340, "#65462f", 6);
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
  // Dotted routes connect every agent to the single Career Assistant brain.
  drawSharedBrain(g, agents, actors, t);
  // Actors sit or stand at the point implied by their current activity.
  agents.forEach((agent, i) => {
    const actor = actors.get(agent.id);
    if (!actor) return;
    const walking = actor.path.length > 0;
    const seated = (!walking && !actor.breakKind && Math.hypot(actor.x - actor.home.x, actor.y - actor.home.y) < 3)
      || (!walking && actor.breakKind === "lounge");
    const portraitY = actor.y - (seated ? 18 : 0);
    const activeBrain = agent.status === "working";
    const brainColor = activeBrain ? (Math.sin(t * 5 + i) > 0 ? "#ed9db0" : "#ca7188") : "#80c49a";
    drawPerson(g, seated ? { ...actor, y: portraitY } : actor, i, walking, seated, selectedId === agent.id || (!selectedId && focusedId === agent.id), t);
    const job = agent.name.length > 14 ? `${agent.name.slice(0, 13)}…` : agent.name;
    const personY = portraitY - 57 - Math.sin(t * 5 + i) * (walking ? 0 : .6);
    px(g, actor.x - job.length * 2.7 - 5, personY - 10, job.length * 5.4 + 10, 13, selectedId === agent.id ? "#f5dd8e" : "rgba(38,48,39,.92)");
    label(g, job, actor.x - job.length * 2.7, personY - 1, selectedId === agent.id ? "#3b372a" : AGENT_NAME_COLORS[i % AGENT_NAME_COLORS.length], 6.5);

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
      if (actor.breakKind === "lounge") {
        px(g, bx + 4, by + 5, 18, 7, "#7fa58a"); px(g, bx + 7, by + 3, 5, 3, "#f0cf85");
        label(g, "LOUNGE", bx + 3, by + 13, "#426149", 4.5);
      } else if (actor.breakKind === "cafe") {
        px(g, bx + 6, by + 5, 9, 6, "#f5f0de"); px(g, bx + 15, by + 6, 3, 3, "#f5f0de");
        px(g, bx + 7, by + 3 - Math.round(Math.sin(t * 5 + i) * 1), 1, 2, "#aa9071");
        label(g, "CAFE", bx + 18, by + 11, "#426149", 4.5);
      } else if (actor.breakKind === "game") {
        px(g, bx + 4, by + 4, 14, 8, "#29213d"); px(g, bx + 6, by + 6, 10, 4, "#79d4dd");
        px(g, bx + 7 + Math.floor(Math.sin(t * 8 + i) * 2), by + 7, 2, 2, "#f6d66c");
        px(g, bx + 20, by + 6, 3, 2, "#e46c8f");
        label(g, "PLAY", bx + 3, by + 13, "#426149", 4.5);
      } else if (actor.breakKind === "tea") {
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
    const style = WORKSTATIONS[i % WORKSTATIONS.length];
    const actor = agents[i] ? actors.get(agents[i].id) : undefined;
    if (!actor || Math.hypot(actor.x - desk.x, actor.y - desk.y) > 4) continue;
    px(g, desk.x - 31, rowY + 12, 62, 7, style.top);
    px(g, desk.x - 33, rowY + 18, 66, 7, style.front);
    // Monitor foreground sits between the seated avatar and the viewer, just below the face.
    px(g, desk.x - 20, rowY - 31, 40, 31, style.bezel);
    px(g, desk.x - 17, rowY - 28, 34, 23, "#172d2a");
    px(g, desk.x - 15, rowY - 26, 30, 19, actor.mode === "working" ? "#c7f2a2" : style.screen);
    px(g, desk.x - 13, rowY - 24, 9, 1, style.accent);
    px(g, desk.x - 13, rowY - 21, 17 + (i % 3) * 2, 1, style.ink);
    px(g, desk.x - 13, rowY - 18, 12 + (i % 4) * 2, 1, style.accent);
    px(g, desk.x - 13, rowY - 15, 20, 1, style.ink);
    px(g, desk.x + 8, rowY - 24, 2, 3 + (i % 3) * 2, style.accent);
    px(g, desk.x + 11, rowY - 24, 2, 5 + (i % 2) * 2, style.ink);
    px(g, desk.x + 14, rowY - 24, 2, 2 + (i % 4), style.accent);
    if (actor.mode === "working") px(g, desk.x + 10 + Math.floor(Math.sin(t * 8 + i) * 2), rowY - 15, 2, 2, "#fff4a3");
    px(g, desk.x - 4, rowY - 5, 8, 17, style.bezel); px(g, desk.x - 12, rowY + 10, 24, 2, style.front);
    px(g, desk.x + 22, rowY + 6, 7, 12, style.bezel);
    px(g, desk.x + 24, rowY + 8, 3, 5, style.accent);
    px(g, desk.x + 24, rowY + 15, 2, 2, actor.mode === "working" ? "#8de99c" : "#8caa88");
    px(g, desk.x - 13, rowY + 13, 22, 3, style.bezel);
    for (let key = 0; key < 5; key++) px(g, desk.x - 11 + key * 4, rowY + 14, 2, 1, "#e7d9bd");
    px(g, desk.x + 13, rowY + 13, 4, 4, style.accent);
    const typing = actor.mode === "working" ? Math.round(Math.sin(t * 15 + i)) : 0;
    px(g, desk.x - 8, desk.y - 15 + typing, 3, 2, color(i, SKIN));
    px(g, desk.x + 5, desk.y - 15 - typing, 3, 2, color(i, SKIN));
    px(g, desk.x - 7, rowY + 20, 14, 3, style.front);
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
    const seated = (!walking && !actor.breakKind && Math.hypot(actor.x - actor.home.x, actor.y - actor.home.y) < 3)
      || (!walking && actor.breakKind === "lounge");
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
        actor = { x: home.x, y: home.y, target, path: [], mode: "idle", step: index % BREAK_KINDS.length, breakSpotIndex: index, blink: 0, bob: index, home, wanderAt: performance.now() / 1000 + 8 + index * 3, returnAt: 0, wandering: false, breakKind: null };
        actors.set(agent.id, actor);
      } else if (typeof actor.breakSpotIndex !== "number") {
        // Upgrade agents already present in a hot-reloaded dev session.
        actor.step = index % BREAK_KINDS.length;
        actor.breakSpotIndex = index;
        actor.breakKind = null;
        actor.wandering = false;
        actor.wanderAt = performance.now() / 1000 + 3 + index * 2;
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
            actor.wanderAt = seconds + 14 + (index % 4) * 3;
          } else if (!actor.wandering && seconds >= actor.wanderAt) {
            actor.wandering = true;
            const kind = BREAK_KINDS[actor.step % BREAK_KINDS.length];
            actor.step = (actor.step + 1) % BREAK_KINDS.length;
            actor.breakKind = kind;
            const spots = BREAK_SPOTS[kind];
            const stop = spots[actor.breakSpotIndex % spots.length];
            actor.breakSpotIndex += 1;
            actor.path = route({ x: actor.x, y: actor.y }, stop);
            actor.returnAt = seconds + 13 + (index % 3) * 2;
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
