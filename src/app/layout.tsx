import type { Metadata } from "next";
import Script from "next/script";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SPECTREX",
  description:
    "Citizen science portal: hunt transients and Planet X across the SPHEREx all-sky spectral survey.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://aladin.cds.unistra.fr" />
        <link rel="dns-prefetch" href="https://aladin.cds.unistra.fr" />
      </head>
      <body className={`${inter.variable} ${jetBrainsMono.variable} antialiased`}>
        {/*
          Runs before any Next.js client code so its `unhandledrejection`
          listener claims Aladin's leaked tile-fetch rejections before the
          dev overlay can record them (see public/aladin-rejection-guard.js).
        */}
        <Script
          src="/aladin-rejection-guard.js"
          strategy="beforeInteractive"
        />
        {children}
      </body>
    </html>
  );
}
