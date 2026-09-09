import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phoenix Valley Neighborhood Conditions Map",
  description: "Explore Census-based neighborhood conditions across Maricopa County. Transparent scores, public data, and local context.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
