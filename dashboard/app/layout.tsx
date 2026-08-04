import type { Metadata } from "next";
import "./globals.css";
import "./typography.css";
import "./dense.css";

export const metadata: Metadata = {
  title: "Sonwet · Weather archive",
  description: "Explore the weather observations collected by Sonwet.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
