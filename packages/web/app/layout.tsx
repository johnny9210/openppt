import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PPT Code Generator",
  description: "AI-powered PPT code generation from natural language",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
