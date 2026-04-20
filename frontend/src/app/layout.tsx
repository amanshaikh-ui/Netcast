import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SiteTopBar } from "@/components/SiteTopBar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NetCast — Social link intelligence",
  description:
    "Discover public product links across YouTube, Shorts, Reddit, TikTok, Facebook, and Instagram.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} mesh-grid relative min-h-screen font-sans antialiased`}
        style={{
          minHeight: "100vh",
          backgroundColor: "#030712",
          color: "#f4f4f5",
        }}
      >
        <SiteTopBar />
        {children}
      </body>
    </html>
  );
}
