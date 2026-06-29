"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body
        style={{
          margin: 0,
          background: "#0A0A0A",
          color: "#F0F0F0",
          fontFamily: "sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>
          Something went wrong
        </h2>
        <p style={{ color: "#888888", margin: 0, fontSize: "0.875rem" }}>
          {error?.message ?? "An unexpected error occurred."}
        </p>
        <button
          onClick={() => reset()}
          style={{
            padding: "8px 20px",
            background: "#1E1E1E",
            border: "1px solid #2A2A2A",
            color: "#F0F0F0",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "0.875rem",
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
