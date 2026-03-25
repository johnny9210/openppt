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
      <body className="bg-blue-50 text-gray-800 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
