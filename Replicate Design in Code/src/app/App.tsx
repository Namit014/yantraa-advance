import svgPaths from "@/imports/MacBookPro1684-1/svg-0nyjpfxfgv";
import imgLogo from "@/imports/MacBookPro1684-1/07d7a0ff8467e4a4fc8fe5bbae30f9fd55d44afb.png";

/* ── Sparkle ─────────────────────────────────────────────────────────── */
function Sparkle() {
  return (
    <svg fill="none" viewBox="0 0 15.507 15.925" width="16" height="16" className="block shrink-0">
      <path d="M7.741 0V15.925" stroke="white" strokeWidth="0.605" />
      <path d={svgPaths.p245dc100} stroke="white" strokeWidth="0.605" />
      <path d={svgPaths.p8ec1980} fill="white" />
    </svg>
  );
}

/* ── Sidebar nav icons ───────────────────────────────────────────────── */
function IconPlus() {
  return (
    <svg fill="none" viewBox="0 0 23.143 24" width="24" height="24">
      <path d={svgPaths.p31237200} fill="white" />
      <path d={svgPaths.p37372e00} fill="white" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg fill="none" viewBox="0 0 24 24" width="24" height="24">
      <path d={svgPaths.p5ff1400} fill="white" />
      <path d={svgPaths.p285d4e80} stroke="white" strokeWidth="1.8" />
    </svg>
  );
}

function IconFile() {
  return (
    <div className="w-6 h-6 flex items-center justify-center">
      <div className="-rotate-90">
        <svg fill="none" viewBox="0 0 24 23.143" width="24" height="23">
          <path d={svgPaths.p1ef15800} stroke="#FEFEFE" strokeWidth="1.8" />
          <line stroke="white" strokeWidth="1.8" x1="14.767" x2="14.767" y1="0.503" y2="22.64" />
        </svg>
      </div>
    </div>
  );
}

function IconRobot() {
  return (
    <svg fill="none" viewBox="0 0 24 24" width="24" height="24">
      <g clipPath="url(#rc)">
        <path d={svgPaths.pb7da400} stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="1.8" />
        <path d={svgPaths.p3db32500} stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="1.8" />
        <path d={svgPaths.p4330680} stroke="white" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
        <path d={svgPaths.p130f7940} fill="white" />
        <path d={svgPaths.p1e5de000} fill="white" />
      </g>
      <defs>
        <clipPath id="rc"><rect fill="white" width="24" height="24" /></clipPath>
      </defs>
    </svg>
  );
}

/* ── Toolbar icons (inside input box) ───────────────────────────────── */
function IconPin() {
  return (
    <svg fill="none" viewBox="0 0 21.393 21.485" width="20" height="20">
      <path d={svgPaths.p3fb4cb30} stroke="white" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function IconMic() {
  return (
    <svg fill="none" viewBox="0 0 20 20" width="20" height="20">
      <path d={svgPaths.p111b3a00} fill="white" />
      <path d={svgPaths.p17adb2f1} stroke="white" strokeWidth="1.8" />
      <rect fill="#F34B4B" height="2.315" stroke="white" strokeWidth="0.698" width="0.698" x="8.968" y="17.336" />
    </svg>
  );
}

function IconPromptLib() {
  return (
    <div className="-rotate-90 w-4 h-4 flex items-center justify-center shrink-0">
      <svg fill="none" viewBox="0 0 18 16.039" width="18" height="16">
        <path d={svgPaths.p282e8e00} stroke="#FEFEFE" strokeWidth="1.8" />
        <path d={svgPaths.p2eef3a80} stroke="white" strokeWidth="1.8" />
      </svg>
    </div>
  );
}

function IconUpgrade() {
  return (
    <svg fill="none" viewBox="0 0 18.646 18.655" width="18" height="18" className="shrink-0">
      <path d={svgPaths.p3b1f0a80} stroke="white" strokeLinecap="round" strokeLinejoin="bevel" strokeWidth="1.8" />
    </svg>
  );
}

/* ── Version badge (clipped polygon shape) ──────────────────────────── */
function VersionBadge() {
  return (
    <div className="relative h-[39px] w-[129px] shrink-0">
      {/* Polygon background */}
      <svg className="absolute inset-0 w-full h-full" fill="none" viewBox="0 0 129 39" preserveAspectRatio="none">
        <path d="M129 12L114.5 0H0V39H129V12Z" fill="#0E0E0E" />
      </svg>
      {/* Label + dot + chevron */}
      <div className="absolute inset-0 flex items-center gap-2 pl-[14px] top-[9px]" style={{ alignItems: "flex-start" }}>
        <div className="relative">
          <p className="font-['DM_Sans',sans-serif] text-white text-[16px] tracking-[-1.28px] leading-none ml-[7.76px]">
            Yantraa 1.0
          </p>
          {/* dot below text */}
          <div className="absolute left-[7.76px] top-[18px] w-[2px] h-[2px]">
            <div className="absolute inset-[-50%]">
              <svg fill="none" viewBox="0 0 4 4" width="4" height="4">
                <path d={svgPaths.p3c933380} stroke="white" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
            </div>
          </div>
        </div>
        <div className="rotate-180 w-5 h-5 shrink-0 mt-[0px]">
          <svg fill="none" viewBox="0 0 20 20" width="20" height="20">
            <path d="M16 13L10 7L4 13" stroke="white" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
    </div>
  );
}

/* ── Arrow / submit button ───────────────────────────────────────────── */
function ArrowButton() {
  return (
    <button className="shrink-0 hover:opacity-80 transition-opacity w-[38.5px] h-[38.5px]">
      <svg fill="none" viewBox="0 0 38.5 38.5" width="38.5" height="38.5">
        <rect fill="white" height="38.5" width="38.5" />
        <path d={svgPaths.p86d4020} stroke="black" strokeWidth="1.8" />
      </svg>
    </button>
  );
}

/* ── Suggestion card icons ───────────────────────────────────────────── */
function Icon3DBox() {
  return (
    <svg fill="none" viewBox="0 0 23.143 24" width="23" height="24" className="shrink-0">
      <path d="M11.571 22.957V12.522" stroke="white" strokeLinejoin="round" strokeWidth="1.8" />
      <path d={svgPaths.p3cd09800} stroke="white" strokeLinejoin="round" strokeWidth="1.86" />
      <path d={svgPaths.p27490a80} stroke="white" strokeLinejoin="round" strokeWidth="1.8" />
      <path d={svgPaths.pa697200} stroke="white" strokeWidth="1.8" />
    </svg>
  );
}

function IconDelta() {
  return (
    <svg fill="none" viewBox="0 0 24 24" width="24" height="24" className="shrink-0">
      <g clipPath="url(#dc)">
        <path d={svgPaths.p3e536200} stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="1.8" />
        <path d={svgPaths.p8ee900} stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="1.8" />
        <rect height="2.889" stroke="white" strokeWidth="1.3" width="7.905" x="7.078" y="1.47" />
        <path d={svgPaths.p12647980} stroke="white" strokeWidth="1.8" />
      </g>
      <defs>
        <clipPath id="dc"><rect fill="white" width="24" height="24" /></clipPath>
      </defs>
    </svg>
  );
}

function IconFeasibility() {
  return (
    <svg fill="none" viewBox="0 0 22 22" width="22" height="22" className="shrink-0">
      <g clipPath="url(#fc)">
        <path d="M14.097 1.889H20.281" stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="2" />
        <path d="M14.097 7.862H20.281" stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="2" />
        <path d="M14.097 13.834H20.281" stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="2" />
        <path d={svgPaths.p31addd00} fill="white" />
        <path d={svgPaths.p3e3ab400} fill="white" />
        <path d="M14.097 20.156H20.281" stroke="white" strokeLinecap="square" strokeLinejoin="round" strokeWidth="2" />
        <rect height="10.906" stroke="white" strokeWidth="1.8" width="9.162" x="1.725" y="1.72" />
      </g>
      <defs>
        <clipPath id="fc"><rect fill="white" width="22" height="22" /></clipPath>
      </defs>
    </svg>
  );
}

/* ── Suggestion card ─────────────────────────────────────────────────── */
function SuggestionCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="bg-[#101010] h-[132px] flex-1 min-w-0 relative overflow-hidden cursor-pointer hover:bg-[#161616] transition-colors">
      <div className="absolute inset-0 flex flex-col justify-center px-6 gap-2">
        <div className="flex gap-3 items-start">
          {icon}
          <p className="font-['DM_Sans',sans-serif] text-white text-[16px] leading-[1.25] tracking-[-1.28px]">
            {title}
          </p>
        </div>
        <p className="font-['DM_Sans',sans-serif] text-[#818181] text-[14px] leading-[1.3] tracking-[-1.12px]">
          {description}
        </p>
      </div>
    </div>
  );
}

/* ── Root ────────────────────────────────────────────────────────────── */
export default function App() {
  return (
    <div className="bg-black w-full min-h-screen flex font-['DM_Sans',sans-serif]">

      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-[94px] shrink-0 flex flex-col items-center py-6 relative">
        {/* Logo */}
        <img src={imgLogo} alt="Yantraa" className="w-11 h-[38px] object-contain mb-0" />

        {/* Nav icons */}
        <nav className="flex flex-col gap-5 items-center mt-[80px]">
          <button className="text-white/70 hover:text-white transition-colors"><IconPlus /></button>
          <button className="text-white/70 hover:text-white transition-colors"><IconSearch /></button>
          <button className="text-white/70 hover:text-white transition-colors"><IconFile /></button>
          <button className="text-white/70 hover:text-white transition-colors"><IconRobot /></button>
        </nav>

        {/* User avatar pinned to bottom */}
        <div className="mt-auto relative w-[46px] h-[46px] flex items-center justify-center">
          <div className="absolute inset-0 border border-[#d8d8d8] pointer-events-none" style={{ borderWidth: "0.803px" }} />
          <span className="text-[#dbdbdb] text-[15px] tracking-[-1.23px]">RM</span>
        </div>
      </aside>

      {/* ── Main panel ───────────────────────────────────────────────── */}
      <div className="flex-1 my-6 mr-6 border border-[#313131] relative flex flex-col overflow-hidden">

        {/* Panel corner sparkles */}
        <div className="absolute top-0 left-0 -translate-x-1/2 -translate-y-1/2 z-10 pointer-events-none"><Sparkle /></div>
        <div className="absolute top-0 right-0  translate-x-1/2 -translate-y-1/2 z-10 pointer-events-none"><Sparkle /></div>
        <div className="absolute bottom-0 left-0 -translate-x-1/2  translate-y-1/2 z-10 pointer-events-none"><Sparkle /></div>
        <div className="absolute bottom-0 right-0  translate-x-1/2  translate-y-1/2 z-10 pointer-events-none"><Sparkle /></div>

        {/* Upgrade button */}
        <div className="absolute top-6 right-6 z-10">
          <button className="relative flex items-center gap-2 bg-[#222] px-5 py-[8px] hover:bg-[#2a2a2a] transition-colors">
            <div className="absolute inset-0 border border-[#333] pointer-events-none" />
            <IconUpgrade />
            <span className="text-white text-[16px] tracking-[-1.3px] whitespace-nowrap">Upgrade</span>
          </button>
        </div>

        {/* Centered content block */}
        <div className="flex-1 flex flex-col items-center justify-center gap-[38px] px-8 py-16">

          {/* Title */}
          <h1
            className="text-white text-center font-normal w-full max-w-[966px]"
            style={{
              fontFamily: "'DM Sans', sans-serif",
              fontSize: "clamp(22px, 2.9vw, 40px)",
              letterSpacing: "-3.2px",
              lineHeight: "normal",
              fontVariationSettings: '"opsz" 14',
            }}
          >
            What would you like to build today?
          </h1>

          {/* Input box + cards */}
          <div className="flex flex-col gap-6 w-full max-w-[966px]">

            {/* Input box with corner sparkles */}
            <div className="relative">
              {/* Input corner sparkles */}
              <div className="absolute -top-2 -left-2 pointer-events-none z-10"><Sparkle /></div>
              <div className="absolute -top-2 -right-2 pointer-events-none z-10"><Sparkle /></div>
              <div className="absolute -bottom-2 -left-2 pointer-events-none z-10"><Sparkle /></div>
              <div className="absolute -bottom-2 -right-2 pointer-events-none z-10"><Sparkle /></div>

              <div className="bg-[#0e0e0e] border border-[#1e1e1e] flex flex-col" style={{ minHeight: "231px" }}>
                {/* Placeholder */}
                <div className="flex-1 px-6 pt-[23px]">
                  <p
                    className="text-[#6b6b6b]"
                    style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontSize: "clamp(16px, 2vw, 24px)",
                      letterSpacing: "-1.92px",
                      fontVariationSettings: '"opsz" 14',
                    }}
                  >
                    Make a pick and place robot |
                  </p>
                </div>

                {/* Toolbar */}
                <div className="flex items-center justify-between px-6 pt-3 pb-6">
                  {/* Left: pin + mic + prompt library */}
                  <div className="flex items-center gap-3">
                    <button className="p-[10px] hover:opacity-70 transition-opacity">
                      <IconPin />
                    </button>
                    <div className="relative h-[39.758px] w-[41px] overflow-hidden">
                      <div className="absolute left-[10px] top-[9.88px]">
                        <IconMic />
                      </div>
                    </div>
                    {/* Prompt Library button */}
                    <button className="relative h-[40px] w-[169px] hover:bg-[#1a1a1a] transition-colors shrink-0">
                      <div className="absolute inset-0 border border-[#181818] pointer-events-none" />
                      <div className="absolute left-[22px] top-[8px] flex items-center gap-0">
                        <IconPromptLib />
                        <span
                          className="text-white whitespace-nowrap ml-[14px]"
                          style={{
                            fontFamily: "'DM Sans', sans-serif",
                            fontSize: "16px",
                            letterSpacing: "-1.28px",
                            fontVariationSettings: '"opsz" 14',
                          }}
                        >
                          Prompt Library
                        </span>
                      </div>
                    </button>
                  </div>

                  {/* Right: version badge + arrow */}
                  <div className="flex items-center gap-4 shrink-0">
                    <VersionBadge />
                    <ArrowButton />
                  </div>
                </div>
              </div>
            </div>

            {/* Suggestion cards */}
            <div className="flex flex-col sm:flex-row gap-[30px]">
              <SuggestionCard
                icon={<Icon3DBox />}
                title="Design a Pick & Place Robot"
                description="Generate CAD, component mapping, and connections for a pick-and-place robotic system."
              />
              <SuggestionCard
                icon={<IconDelta />}
                title="Design a Delta Robot"
                description="Validate requirements, assess technical viability, and refine your robot before generating designs."
              />
              <SuggestionCard
                icon={<IconFeasibility />}
                title="Check Feasibility"
                description="Evaluate cost, complexity, technical viability and understand the process before building your robot."
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
