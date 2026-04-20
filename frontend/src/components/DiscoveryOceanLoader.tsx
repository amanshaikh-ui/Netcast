"use client";

const PLATFORMS = ["YouTube", "Reddit", "TikTok", "Facebook", "Instagram"];

const PLATFORM_COLORS: Record<string, string> = {
  YouTube: "#ef4444",
  Reddit: "#f97316",
  TikTok: "#22d3ee",
  Facebook: "#3b82f6",
  Instagram: "#ec4899",
};

export function DiscoveryOceanLoader({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background:
          "linear-gradient(135deg, #020b18 0%, #030f1f 50%, #020b18 100%)",
        backdropFilter: "blur(8px)",
      }}
      role="status"
      aria-live="polite"
      aria-label="Searching social platforms"
    >
      {/* Ambient top glow */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "600px",
          height: "300px",
          background:
            "radial-gradient(ellipse, rgba(34,211,238,0.14) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      {/* Grid lines overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          pointerEvents: "none",
          maskImage:
            "radial-gradient(ellipse 60% 50% at 50% 40%, black 20%, transparent 100%)",
        }}
      />

      {/* Main card */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "2rem",
          maxWidth: "440px",
          width: "100%",
          padding: "0 1.5rem",
        }}
      >
        {/* Scanning ring animation */}
        <div style={{ position: "relative", width: "120px", height: "120px" }}>
          {/* Outer pulse ring */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              border: "1px solid rgba(34,211,238,0.2)",
              animation: "radar-ping 2s ease-out infinite",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: "-12px",
              borderRadius: "50%",
              border: "1px solid rgba(34,211,238,0.1)",
              animation: "radar-ping 2s ease-out infinite 0.4s",
            }}
          />
          {/* Spinning arc */}
          <svg
            viewBox="0 0 120 120"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              animation: "spin-cw 1.4s linear infinite",
            }}
          >
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              stroke="url(#arcGrad)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="90 250"
            />
            <defs>
              <linearGradient id="arcGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity="0" />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity="1" />
              </linearGradient>
            </defs>
          </svg>
          {/* Counter spinning arc */}
          <svg
            viewBox="0 0 120 120"
            style={{
              position: "absolute",
              inset: "10px",
              width: "calc(100% - 20px)",
              height: "calc(100% - 20px)",
              animation: "spin-ccw 2.2s linear infinite",
            }}
          >
            <circle
              cx="50"
              cy="50"
              r="44"
              fill="none"
              stroke="url(#arcGrad2)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="60 220"
            />
            <defs>
              <linearGradient id="arcGrad2" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#a78bfa" stopOpacity="0" />
                <stop offset="100%" stopColor="#a78bfa" stopOpacity="0.9" />
              </linearGradient>
            </defs>
          </svg>
          {/* Center icon — radar dot */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                background:
                  "radial-gradient(circle, #67e8f9 0%, #22d3ee 60%, #0891b2 100%)",
                boxShadow: "0 0 20px 4px rgba(34,211,238,0.5)",
                animation: "dot-pulse 1.4s ease-in-out infinite",
              }}
            />
          </div>
        </div>

        {/* Platform scan indicators */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.6rem",
            width: "100%",
          }}
        >
          {PLATFORMS.map((name, i) => (
            <div
              key={name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.55rem 1rem",
                borderRadius: "0.75rem",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                animation: `scan-row 0.4s ease-out ${i * 0.12}s both`,
              }}
            >
              {/* Colour dot */}
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  flexShrink: 0,
                  background: PLATFORM_COLORS[name],
                  boxShadow: `0 0 8px 2px ${PLATFORM_COLORS[name]}80`,
                  animation: "dot-pulse 1.6s ease-in-out infinite",
                  animationDelay: `${i * 0.22}s`,
                }}
              />
              {/* Label */}
              <span
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "rgba(226,232,240,0.85)",
                  flex: 1,
                }}
              >
                {name}
              </span>
              {/* Scanning bar */}
              <div
                style={{
                  flex: 2,
                  height: "4px",
                  borderRadius: "9999px",
                  background: "rgba(255,255,255,0.05)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    borderRadius: "9999px",
                    background: `linear-gradient(90deg, transparent, ${PLATFORM_COLORS[name]}, transparent)`,
                    animation: `scan-bar 1.6s ease-in-out infinite`,
                    animationDelay: `${i * 0.3}s`,
                  }}
                />
              </div>
              {/* Status */}
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "rgba(103,232,249,0.55)",
                  fontFamily: "monospace",
                  animation: `blink-text 1.2s step-end infinite`,
                  animationDelay: `${i * 0.15}s`,
                }}
              >
                scanning
              </span>
            </div>
          ))}
        </div>

        <p
          style={{
            color: "rgba(148,163,184,0.7)",
            fontSize: "0.875rem",
            textAlign: "center",
            letterSpacing: "0.02em",
          }}
        >
          Casting the net across all networks…
        </p>
      </div>
    </div>
  );
}
