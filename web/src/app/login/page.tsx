import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = {
  title: "Sign in · AI Business Detective",
};

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="card" style={{ marginTop: 32 }}>Loading…</div>}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
