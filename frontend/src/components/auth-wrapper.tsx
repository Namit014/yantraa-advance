"use client";

import React, { useState, useEffect } from "react";
import { Lock, Mail, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  
  const [email, setEmail] = useState("teams@yantraa.tech");
  const [password, setPassword] = useState("Yantraa@2026");
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
      if (email === "teams@yantraa.tech" && password === "Yantraa@2026") {
        setIsAuthenticated(true);
        sessionStorage.setItem("isAuthenticated", "true");
      } else {
        setError("Invalid credentials. Please check your email and password.");
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
      
      {/* Background Ambient Grid/Crosshairs */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Horizontal and Vertical dividing lines */}
        <div className="absolute top-[80px] left-0 right-0 h-px bg-[#111111]" />
        <div className="absolute bottom-[80px] left-0 right-0 h-px bg-[#111111]" />
        <div className="absolute left-[240px] top-0 bottom-0 w-px bg-[#111111]" />
        <div className="absolute right-[240px] top-0 bottom-0 w-px bg-[#111111]" />

        {/* Corner markers on grid intersections */}
        <div className="absolute top-[75px] left-[235px] w-2.5 h-2.5 border border-[#333333]" />
        <div className="absolute top-[75px] right-[235px] w-2.5 h-2.5 border border-[#333333]" />
        <div className="absolute bottom-[75px] left-[235px] w-2.5 h-2.5 border border-[#333333]" />
        <div className="absolute bottom-[75px] right-[235px] w-2.5 h-2.5 border border-[#333333]" />
      </div>

      {/* Top Left Text */}
      <div className="absolute top-6 left-6 text-[#444444] text-[10px] font-mono tracking-wider z-10 flex flex-col gap-1.5">
        <span>18.9582° N, 72.8320° E</span>
        <span>[LINKEDIN]</span>
      </div>

      {/* Top Right Logo */}
      <div className="absolute top-6 right-6 z-10 flex items-center gap-3">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" stroke="#888888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-[#666666] font-medium tracking-wide">Yantraa</span>
        <div className="ml-4 w-4 h-4 relative">
          <div className="absolute top-1/2 left-0 right-0 h-px bg-[#444444]" />
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-[#444444]" />
        </div>
      </div>

      {/* Bottom Left Text */}
      <div className="absolute bottom-6 left-6 text-[#333333] text-[10px] font-medium tracking-wider z-10">
        Yantraa Inc.
      </div>

      {/* Bottom Right Waveform */}
      <div className="absolute bottom-6 right-6 z-10">
        <svg width="24" height="12" viewBox="0 0 24 12" fill="none" stroke="#333333" strokeWidth="1.5">
          <path d="M2 6 L6 2 L10 10 L14 4 L18 8 L22 6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      
      {/* Login Card Wrapper for Border Effect */}
      <div className="relative z-20" style={{ filter: "drop-shadow(0 0 40px rgba(0,0,0,0.8))" }}>
        
        {/* Main Card with Chamfered Corners via clip-path */}
        <div 
          className="relative w-[500px] bg-[#0A0A0A] p-[1px] overflow-hidden"
          style={{ clipPath: "polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px)" }}
        >
          {/* Inner Card content */}
          <div 
            className="w-full h-full bg-[#111111] bg-opacity-95 p-12 flex flex-col items-center relative"
            style={{ clipPath: "polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px)" }}
          >
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
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mb-6">
                  <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" stroke="#F0F0F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h2 className="text-[26px] font-normal text-[#F0F0F0] tracking-tight mb-2">Welcome Back</h2>
              <p className="text-[13px] text-[#777777]">Sign in to access Yantraa Advance</p>
            </div>

            <form onSubmit={handleLogin} className="w-full space-y-6">
              
              {/* Email Field */}
              <div className="space-y-2">
                <label className="text-[10px] font-mono text-[#666666] uppercase tracking-widest flex items-center gap-2">
                  <span className="text-[#444444]">///</span> EMAIL
                </label>
                <div className="relative">
                  {/* Field Corner Markers */}
                  <div className="absolute -top-[1px] -left-[1px] w-2 h-2 border-t border-l border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -top-[1px] -right-[1px] w-2 h-2 border-t border-r border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -left-[1px] w-2 h-2 border-b border-l border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -right-[1px] w-2 h-2 border-b border-r border-[#444444] pointer-events-none z-10" />
                  
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="h-[18px] w-[18px] text-[#555555] stroke-[1.5]" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teams@yantraa.tech"
                    className="w-full pl-12 pr-4 py-3.5 bg-[#0A0A0A] border border-[#222222] text-[#F0F0F0] placeholder:text-[#444444] text-[13px] focus:outline-none focus:border-[#444444] transition-colors"
                    required
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label className="text-[10px] font-mono text-[#666666] uppercase tracking-widest flex items-center gap-2">
                  <span className="text-[#444444]">///</span> PASSWORD
                </label>
                <div className="relative">
                  {/* Field Corner Markers */}
                  <div className="absolute -top-[1px] -left-[1px] w-2 h-2 border-t border-l border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -top-[1px] -right-[1px] w-2 h-2 border-t border-r border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -left-[1px] w-2 h-2 border-b border-l border-[#444444] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -right-[1px] w-2 h-2 border-b border-r border-[#444444] pointer-events-none z-10" />

                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Lock className="h-[18px] w-[18px] text-[#555555] stroke-[1.5]" />
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-12 pr-4 py-3.5 bg-[#0A0A0A] border border-[#222222] text-[#F0F0F0] placeholder:text-[#444444] text-[13px] focus:outline-none focus:border-[#444444] transition-colors tracking-widest"
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="text-xs text-[#E0E0E0] border border-[#333333] p-3 text-center bg-[#1A1A1A]">
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="relative w-full group flex items-center justify-center gap-2 py-3.5 px-4 bg-[#1A1A1A] border border-[#2A2A2A] hover:bg-[#222222] hover:border-[#444444] text-[#F0F0F0] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* Button Corner Markers */}
                  <div className="absolute -top-[1px] -left-[1px] w-1.5 h-1.5 border-t border-l border-[#555555] pointer-events-none z-10" />
                  <div className="absolute -top-[1px] -right-[1px] w-1.5 h-1.5 border-t border-r border-[#555555] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -left-[1px] w-1.5 h-1.5 border-b border-l border-[#555555] pointer-events-none z-10" />
                  <div className="absolute -bottom-[1px] -right-[1px] w-1.5 h-1.5 border-b border-r border-[#555555] pointer-events-none z-10" />

                  {isLoading ? (
                    <div className="w-4 h-4 border-2 border-[#555555] border-t-[#F0F0F0] rounded-full animate-spin" />
                  ) : (
                    <>
                      <span className="text-[13px] font-medium tracking-wide">Sign In</span>
                      <ArrowRight className="w-4 h-4 text-[#888888] group-hover:text-[#F0F0F0] group-hover:translate-x-1 transition-all" />
                    </>
                  )}
                </button>
              </div>
            </form>
            
            <div className="mt-8 text-center flex items-center gap-2 text-[#555555]">
              <Lock className="w-[14px] h-[14px]" />
              <span className="text-[11px] font-medium">Secure authentication layer.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
