// components/RequireAuth.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type AuthStatus = "checking" | "authed" | "redirect";

export default function RequireAuth({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("checking");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const raw =
      localStorage.getItem("shannova_user") ||
      localStorage.getItem("shanova_user");

    if (!raw) {
      setStatus("redirect");
      router.replace("/login");
      return;
    }

    try {
      JSON.parse(raw);
      setStatus("authed");
    } catch {
      setStatus("redirect");
      router.replace("/login");
    }
  }, [router]);

  if (status !== "authed") {
    return <p className="status-text">You must be logged in to access this page.</p>;
  }

  return <>{children}</>;
}
