"use client";

import React, { useState, useEffect } from "react";
import { Lock, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { DM_Sans } from "next/font/google";

const dmSans = DM_Sans({ subsets: ["latin"], weight: ["400"] });

const CrossIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 13 13" fill="none">
    <path d="M6.40167 0V12.8159" stroke="white" strokeWidth="0.5"/>
    <path d="M12.8159 6.1134L2.38419e-07 6.1134" stroke="white" strokeWidth="0.5"/>
    <path d="M6.40796 4.57886C6.71211 5.40081 7.36017 6.04888 8.18213 6.35303C7.36017 6.65718 6.71211 7.30524 6.40796 8.1272C6.10381 7.30524 5.45575 6.65718 4.63379 6.35303C5.45575 6.04888 6.10381 5.40081 6.40796 4.57886Z" fill="white"/>
  </svg>
);

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const auth = sessionStorage.getItem("isAuthenticated");
    if (auth === "true") {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    setTimeout(() => {
      if (email && password) {
        setIsAuthenticated(true);
        sessionStorage.setItem("isAuthenticated", "true");
      } else {
        setError("Please enter your credentials.");
      }
      setIsLoading(false);
    }, 600);
  };

  if (!isMounted) return null;

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#000000] relative overflow-hidden font-sans">
      <style>{`
        input:-webkit-autofill,
        input:-webkit-autofill:hover, 
        input:-webkit-autofill:focus, 
        input:-webkit-autofill:active {
            transition: background-color 5000s ease-in-out 0s;
            -webkit-text-fill-color: #F0F0F0 !important;
        }
      `}</style>
      {/* Background Ambient Grid/Crosshairs (Anchored to Card Corners) */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="relative w-[725px] h-[662px] scale-[0.85] transform-gpu">
          {/* Horizontal Top Line */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[200vw] h-[1.18px] bg-[#111111]" />
          {/* Horizontal Bottom Line */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[200vw] h-[1.18px] bg-[#111111]" />
          {/* Vertical Left Line */}
          <div className="absolute left-0 top-1/2 -translate-y-1/2 h-[200vh] w-[1.18px] bg-[#111111]" />
          {/* Vertical Right Line */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 h-[200vh] w-[1.18px] bg-[#111111]" />

          {/* Intersection Markers (Crosses) */}
          <div className="absolute top-0 left-0 w-3 h-3 transform -translate-x-1/2 -translate-y-1/2 text-[rgba(255,255,255,0.18)]"><div className="absolute top-1/2 left-0 right-0 h-[0.5px] bg-current"/><div className="absolute left-1/2 top-0 bottom-0 w-[0.5px] bg-current"/></div>
          <div className="absolute top-0 right-0 w-3 h-3 transform translate-x-1/2 -translate-y-1/2 text-[rgba(255,255,255,0.18)]"><div className="absolute top-1/2 left-0 right-0 h-[0.5px] bg-current"/><div className="absolute left-1/2 top-0 bottom-0 w-[0.5px] bg-current"/></div>
          <div className="absolute bottom-0 left-0 w-3 h-3 transform -translate-x-1/2 translate-y-1/2 text-[rgba(255,255,255,0.18)]"><div className="absolute top-1/2 left-0 right-0 h-[0.5px] bg-current"/><div className="absolute left-1/2 top-0 bottom-0 w-[0.5px] bg-current"/></div>
          <div className="absolute bottom-0 right-0 w-3 h-3 transform translate-x-1/2 translate-y-1/2 text-[rgba(255,255,255,0.18)]"><div className="absolute top-1/2 left-0 right-0 h-[0.5px] bg-current"/><div className="absolute left-1/2 top-0 bottom-0 w-[0.5px] bg-current"/></div>
        </div>
      </div>

      {/* Top Left Text */}
      <div className="absolute top-6 left-6 text-[#444444] text-[10px] font-mono tracking-wider z-10 flex flex-col gap-1.5">
        <span>18.9582° N, 72.8320° E</span>
        <span>[LINKEDIN]</span>
      </div>

      {/* Top Right Logo */}
      <div className="absolute top-6 right-6 z-10 flex items-center gap-3">
        <img src="/yantraa-logo.png" alt="Yantraa" className="w-[18px] h-[18px] object-contain opacity-70 grayscale" />
        <span className="text-[#666666] font-medium tracking-wide">Yantraa</span>
      </div>

      {/* Bottom Left Text */}
      <div className="absolute bottom-6 left-6 text-[#333333] text-[10px] font-medium tracking-wider z-10">
        Yantraa Inc.
      </div>
      
      {/* Login Card Wrapper for Border Effect */}
      <div className="relative z-20 scale-[0.85] transform-gpu" style={{ filter: "drop-shadow(0 0 40px rgba(0,0,0,0.8))" }}>
        
        {/* Main Card */}
        <div className="relative w-[725px] h-[662px] flex flex-col items-center justify-center">
          
          {/* SVG Background Layer */}
          <div className="absolute inset-0 z-0 pointer-events-none">
            <svg width="725" height="662" viewBox="0 0 725 662" fill="none" xmlns="http://www.w3.org/2000/svg">
              <g filter="url(#filter0_n_37_284)">
                <mask id="path-1-inside-1_37_284" fill="white">
                  <path d="M724.788 661.237H490.159L475.709 642.205H263.689L249.239 661.237H0V0H241.884L256.884 19.7568H468.903L483.903 0H724.788V661.237Z"/>
                </mask>
                <path d="M724.788 661.237H490.159L475.709 642.205H263.689L249.239 661.237H0V0H241.884L256.884 19.7568H468.903L483.903 0H724.788V661.237Z" fill="#2A2A2B"/>
                <path d="M724.788 661.237V661.737H725.288V661.237H724.788ZM490.159 661.237L489.761 661.54L489.911 661.737H490.159V661.237ZM475.709 642.205L476.107 641.903L475.957 641.705H475.709V642.205ZM263.689 642.205V641.705H263.441L263.291 641.903L263.689 642.205ZM249.239 661.237V661.737H249.487L249.637 661.54L249.239 661.237ZM0 661.237H-0.5V661.737H0V661.237ZM0 0V-0.5H-0.5V0H0ZM241.884 0L242.282 -0.302347L242.132 -0.5H241.884V0ZM256.884 19.7568L256.486 20.0592L256.636 20.2568H256.884V19.7568ZM468.903 19.7568V20.2568H469.151L469.302 20.0592L468.903 19.7568ZM483.903 0V-0.5H483.655L483.505 -0.302347L483.903 0ZM724.788 0H725.288V-0.5H724.788V0ZM724.788 661.237V660.737H490.159V661.237V661.737H724.788V661.237ZM490.159 661.237L490.557 660.935L476.107 641.903L475.709 642.205L475.311 642.507L489.761 661.54L490.159 661.237ZM475.709 642.205V641.705H263.689V642.205V642.705H475.709V642.205ZM263.689 642.205L263.291 641.903L248.841 660.935L249.239 661.237L249.637 661.54L264.088 642.507L263.689 642.205ZM249.239 661.237V660.737H0V661.237V661.737H249.239V661.237ZM0 661.237H0.5V0H0H-0.5V661.237H0ZM0 0V0.5H241.884V0V-0.5H0V0ZM241.884 0L241.486 0.302347L256.486 20.0592L256.884 19.7568L257.282 19.4545L242.282 -0.302347L241.884 0ZM256.884 19.7568V20.2568H468.903V19.7568V19.2568H256.884V19.7568ZM468.903 19.7568L469.302 20.0592L484.302 0.302347L483.903 0L483.505 -0.302347L468.505 19.4545L468.903 19.7568ZM483.903 0V0.5H724.788V0V-0.5H483.903V0ZM724.788 0H724.288V661.237H724.788H725.288V0H724.788Z" fill="white" fillOpacity="0.18" mask="url(#path-1-inside-1_37_284)"/>
              </g>
              <defs>
                <filter id="filter0_n_37_284" x="0" y="0" width="724.788" height="661.237" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
                  <feFlood floodOpacity="0" result="BackgroundImageFix"/>
                  <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"/>
                  <feTurbulence type="fractalNoise" baseFrequency="2 2" stitchTiles="stitch" numOctaves="3" result="noise" seed="5351" />
                  <feColorMatrix in="noise" type="luminanceToAlpha" result="alphaNoise" />
                  <feComponentTransfer in="alphaNoise" result="coloredNoise1">
                    <feFuncA type="discrete" tableValues="1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 "/>
                  </feComponentTransfer>
                  <feComposite operator="in" in2="shape" in="coloredNoise1" result="noise1Clipped" />
                  <feFlood floodColor="rgba(0, 0, 0, 0.5)" result="color1Flood" />
                  <feComposite operator="in" in2="noise1Clipped" in="color1Flood" result="color1" />
                  <feMerge result="effect1_noise_37_284">
                    <feMergeNode in="shape" />
                    <feMergeNode in="color1" />
                  </feMerge>
                </filter>
              </defs>
            </svg>
          </div>

          {/* Inner Content overlaying the SVG */}
          <div className="relative z-10 w-full h-full px-24 py-16 flex flex-col items-center justify-center">
            {/* Top Right Options Button inside card */}
            <div className="absolute top-6 right-6 w-8 h-8 rounded-md bg-[#1A1A1A] border border-[#2A2A2A] flex items-center justify-center text-[#555555] hover:text-[#888888] cursor-pointer">
              <div className="grid grid-cols-2 gap-1">
                <div className="w-[3px] h-[3px] bg-currentColor rounded-full" />
                <div className="w-[3px] h-[3px] bg-currentColor rounded-full" />
                <div className="w-[3px] h-[3px] bg-currentColor rounded-full" />
                <div className="w-[3px] h-[3px] bg-currentColor rounded-full" />
              </div>
            </div>

            {/* Logo / Brand */}
            <div className="text-center mb-10 flex flex-col items-center">
              <img src="/yantraa-logo.png" alt="Yantraa" className="w-[32px] h-[32px] object-contain mb-6" />
              <h2 
                className={cn("text-[#FFF] text-center mb-3", dmSans.className)}
                style={{
                  fontSize: "30px",
                  fontWeight: 400,
                  lineHeight: "102%",
                  letterSpacing: "-2.4px"
                }}
              >
                Welcome
              </h2>
              <p 
                className={dmSans.className}
                style={{
                  color: "rgba(255, 255, 255, 0.21)",
                  textAlign: "center",
                  fontSize: "15px",
                  fontWeight: 300,
                  lineHeight: "102%",
                  letterSpacing: "-1.2px"
                }}
              >
                Sign in to access Yantraa Advance
              </p>
            </div>

            <form onSubmit={handleLogin} className="w-full max-w-[440px] space-y-10 mt-6">
              
              {/* Email Field */}
              <div className="relative w-full">
                {/* Top-Left Cross */}
                <div className="absolute -top-[6px] -left-[6px] z-20 text-white"><CrossIcon /></div>
                
                {/* Bottom-Right Cross */}
                <div className="absolute -bottom-[6px] -right-[6px] z-20 text-white"><CrossIcon /></div>

                {/* Left Border */}
                <div className="absolute left-0 top-[6px] bottom-0 w-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Bottom Border */}
                <div className="absolute left-0 bottom-0 right-[6px] h-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Right Border (starts below the 16px chamfer) */}
                <div className="absolute right-0 top-[16px] bottom-[6px] w-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Top Right Chamfer */}
                <svg className="absolute right-0 top-0 w-[16px] h-[16px] pointer-events-none z-10">
                  <line x1="0" y1="0" x2="16" y2="16" stroke="rgba(255,255,255,0.18)" strokeWidth="0.5" />
                </svg>
                
                {/* Top Border */}
                <div className="absolute top-0 left-[90px] right-[16px] h-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Label */}
                <div className="absolute top-[-9px] left-[16px] z-10 flex items-center gap-1.5">
                  <span className="text-[#666666] font-bold text-[13px] font-mono tracking-widest">///</span>
                  <span className="text-[#999999] text-[14px] font-medium tracking-wide">Email</span>
                </div>

                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="apj.kalam@nic.in"
                  className="w-full bg-transparent border-none pl-6 pr-4 pt-8 pb-4 text-[#F0F0F0] placeholder:text-[#555555] text-[15px] focus:outline-none transition-colors"
                  required
                />
              </div>

              {/* Password Field */}
              <div className="relative w-full">
                {/* Top-Left Cross */}
                <div className="absolute -top-[6px] -left-[6px] z-20 text-white"><CrossIcon /></div>
                
                {/* Bottom-Right Cross */}
                <div className="absolute -bottom-[6px] -right-[6px] z-20 text-white"><CrossIcon /></div>

                {/* Left Border */}
                <div className="absolute left-0 top-[6px] bottom-0 w-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Bottom Border */}
                <div className="absolute left-0 bottom-0 right-[6px] h-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Right Border (starts below the 16px chamfer) */}
                <div className="absolute right-0 top-[16px] bottom-[6px] w-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Top Right Chamfer */}
                <svg className="absolute right-0 top-0 w-[16px] h-[16px] pointer-events-none z-10">
                  <line x1="0" y1="0" x2="16" y2="16" stroke="rgba(255,255,255,0.18)" strokeWidth="0.5" />
                </svg>
                
                {/* Top Border */}
                <div className="absolute top-0 left-[115px] right-[16px] h-[0.5px] bg-[rgba(255,255,255,0.18)]" />
                
                {/* Label */}
                <div className="absolute top-[-9px] left-[16px] z-10 flex items-center gap-1.5">
                  <span className="text-[#666666] font-bold text-[13px] font-mono tracking-widest">///</span>
                  <span className="text-[#999999] text-[14px] font-medium tracking-wide">Password</span>
                </div>

                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-transparent border-none pl-6 pr-4 pt-8 pb-4 text-[#F0F0F0] placeholder:text-[#555555] text-[15px] focus:outline-none transition-colors tracking-widest"
                  required
                />
              </div>

              {error && (
                <div className="text-xs text-[#E0E0E0] border border-[rgba(255,255,255,0.1)] p-3 text-center bg-[#1A1A1A]">
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="relative w-full group flex items-center justify-center gap-2 py-4 px-4 bg-[#3A3A3B] hover:bg-[#4A4A4B] text-[#F0F0F0] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="w-4 h-4 border-2 border-[#555555] border-t-[#F0F0F0] rounded-full animate-spin" />
                  ) : (
                    <>
                      <span className="text-[14px] font-medium tracking-wide">Sign In</span>
                      <svg 
                        xmlns="http://www.w3.org/2000/svg" 
                        width="13" 
                        height="11" 
                        viewBox="0 0 13 11" 
                        fill="none"
                        className="text-[#888888] group-hover:text-[#F0F0F0] group-hover:translate-x-1 transition-all"
                      >
                        <circle cx="4.20185" cy="5.44445" r="1.12499" transform="rotate(90 4.20185 5.44445)" fill="currentColor"/>
                        <circle cx="1.12501" cy="5.44445" r="1.12499" transform="rotate(90 1.12501 5.44445)" fill="currentColor"/>
                        <circle cx="11.0915" cy="5.44445" r="1.12499" transform="rotate(90 11.0915 5.44445)" fill="currentColor"/>
                        <circle cx="7.71571" cy="1.12501" r="1.12499" transform="rotate(-180 7.71571 1.12501)" fill="currentColor"/>
                        <circle cx="9.52845" cy="3.19447" r="1.12499" transform="rotate(-180 9.52845 3.19447)" fill="currentColor"/>
                        <circle cx="7.27845" cy="5.34999" r="1.12499" transform="rotate(-180 7.27845 5.34999)" fill="currentColor"/>
                        <circle cx="7.47279" cy="9.57496" r="1.12499" transform="rotate(-180 7.47279 9.57496)" fill="currentColor"/>
                        <circle cx="9.30982" cy="7.59999" r="1.12499" transform="rotate(-180 9.30982 7.59999)" fill="currentColor"/>
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </form>
            
          </div>
        </div>
      </div>
    </div>
  );
}
