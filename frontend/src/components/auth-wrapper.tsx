"use client";

import React, { useState, useEffect } from "react";
import { Lock, Mail, ArrowRight } from "lucide-react";

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

    // Simulate a brief loading state for better UX
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

  // Prevent hydration mismatch
  if (!isMounted) return null;

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] relative overflow-hidden">
      {/* Subtle background glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/8 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/8 rounded-full blur-[140px] pointer-events-none" />
      
      {/* Login Container */}
      <div className="relative z-10 w-full max-w-md p-8 rounded-2xl bg-[#161616] border border-[#2A2A2A] shadow-2xl transition-all duration-500 hover:border-[#333333]">
        
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-[#1E1E1E] mb-5 border border-[#2A2A2A]">
            <Lock className="w-6 h-6 text-[#888888]" />
          </div>
          <h2 className="text-2xl font-semibold text-[#F0F0F0] tracking-tight mb-1.5">Welcome Back</h2>
          <p className="text-sm text-[#888888]">Sign in to access Yantraa Advance</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#888888] uppercase tracking-wider ml-0.5">Email</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Mail className="h-4 w-4 text-[#555555]" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full pl-10 pr-4 py-3 bg-[#1E1E1E] border border-[#2A2A2A] rounded-xl text-[#F0F0F0] placeholder:text-[#555555] text-sm focus:outline-none focus:ring-1 focus:ring-[#444444] focus:border-[#444444] transition-all duration-200"
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#888888] uppercase tracking-wider ml-0.5">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Lock className="h-4 w-4 text-[#555555]" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-3 bg-[#1E1E1E] border border-[#2A2A2A] rounded-xl text-[#F0F0F0] placeholder:text-[#555555] text-sm focus:outline-none focus:ring-1 focus:ring-[#444444] focus:border-[#444444] transition-all duration-200"
                required
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-400/8 border border-red-400/15 p-3 rounded-lg text-center animate-in fade-in slide-in-from-top-1">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full group relative flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold rounded-xl shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-sm mt-2"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                Sign In
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>
        
        <div className="mt-6 text-center text-xs text-[#555555]">
          <p>Secure authentication layer.</p>
        </div>
      </div>
    </div>
  );
}
