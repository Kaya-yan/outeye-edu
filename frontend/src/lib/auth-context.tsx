"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { apiPost, apiGet, ApiError } from "./api";

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

  // 挂载时读取 localStorage，并校验 token 是否仍然有效
  // 校验失败（401）则静默登出，避免后续请求被拒
  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (savedToken && savedUser) {
      try {
        const userInfo: User = JSON.parse(savedUser);
        setToken(savedToken);
        setUser(userInfo);
        setCookie("auth_token", savedToken);

        // 后台异步校验 token 有效性，不阻塞 UI
        apiGet<{ id: string; email: string; full_name: string }>("/users/me")
          .then((fresh) => {
            const validated: User = { id: fresh.id, email: fresh.email, full_name: fresh.full_name || "" };
            localStorage.setItem("user", JSON.stringify(validated));
            setUser(validated);
          })
          .catch((err) => {
            if (err instanceof ApiError && err.status === 401) {
              // Token 失效，静默登出
              localStorage.removeItem("token");
              localStorage.removeItem("user");
              removeCookie("auth_token");
              setToken(null);
              setUser(null);
            }
          });
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        removeCookie("auth_token");
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // 1. 获取 token
    const data = await apiPost<{ access_token: string; token_type: string }>(
      "/users/login",
      { email, password }
    );
    const t = data.access_token;
    localStorage.setItem("token", t);
    setCookie("auth_token", t);
    setToken(t);

    // 2. 拉取用户信息；失败时用邮箱兜底，保证 setUser 必被调用
    //    避免注册后 token 即时未生效导致 /users/me 401 把人踢回 /login
    let userInfo: User;
    try {
      const u = await apiGet<{ id: string; email: string; full_name: string }>("/users/me");
      userInfo = { id: u.id, email: u.email, full_name: u.full_name || "" };
    } catch {
      userInfo = { id: "", email, full_name: email };
    }
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await apiPost("/users/", { email, password, full_name: fullName });
    // 注册成功后立即用刚提交的账号密码登录
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    removeCookie("auth_token");
    setToken(null);
    setUser(null);
    // 登出做全量刷新，确保所有缓存的用户态清空
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
