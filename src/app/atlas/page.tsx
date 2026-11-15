import type { Metadata } from "next";
import { Dashboard } from "@/components/home/Dashboard";

export const metadata: Metadata = {
  title: "All-Sky Atlas · SpectraX",
};

export default function AtlasPage() {
  return <Dashboard />;
}
