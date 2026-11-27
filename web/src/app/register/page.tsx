import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = {
  title: "Create your account · AI Business Detective",
};

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="card" style={{ marginTop: 32 }}>Loading…</div>}>
      <AuthForm mode="register" />
    </Suspense>
  );
}
