"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { apiPost, apiGet } from "./api";

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

function setCookie(name: string, value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        setCookie("auth_token", savedToken);
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        removeCookie("auth_token");
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost<{ access_token: string; token_type: string }>(
      "/users/login",
      { email, password }
    );
    const t = data.access_token;
    localStorage.setItem("token", t);
    setCookie("auth_token", t);
    setToken(t);

    const u = await apiGet<{ id: string; email: string; full_name: string }>("/users/me");
    const userInfo: User = { id: u.id, email: u.email, full_name: u.full_name || "" };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await apiPost("/users/", { email, password, full_name: fullName });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    removeCookie("auth_token");
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
