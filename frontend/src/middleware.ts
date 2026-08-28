import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const publicPaths = ["/login", "/register", "/terms", "/privacy"];

// 编辑器为 public 静态文件（如 /editor/index.html），不能落入下方点号放行分支
const authRequiredPrefixes = ["/editor", "/html-workbench"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths, static files, and API routes
  if (
    publicPaths.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/")
  ) {
    return NextResponse.next();
  }

  const isProtectedRoute = authRequiredPrefixes.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );

  if (!isProtectedRoute && pathname.includes(".")) {
    return NextResponse.next();
  }

  // Check for auth cookie (set by AuthProvider alongside localStorage)
  const hasToken = request.cookies.get("auth_token");
  if (!hasToken) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
