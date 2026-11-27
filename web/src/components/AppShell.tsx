"use client";

import React, { useState } from "react";
import { AuthProvider } from "@/components/AuthProvider";
import { BgNetwork } from "@/components/BgNetwork";
import { CommandPalette } from "@/components/CommandPalette";
import { Navbar } from "@/components/Navbar";
import { ToastProvider } from "@/components/ToastProvider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [palOpen, setPalOpen] = useState(false);

  return (
    <ToastProvider>
      <AuthProvider>
        <BgNetwork />
        <Navbar onOpenPalette={() => setPalOpen(true)} />
        <main className="wrap">{children}</main>
        <footer className="wrap">
          Turning business data into actionable insights.
          <br />
          Contributors show <b>where</b> a change happened — not proof of <b>why</b>. Sample data is illustrative only.
        </footer>
        <CommandPalette open={palOpen} onOpenChange={setPalOpen} />
      </AuthProvider>
    </ToastProvider>
  );
}
