import Link from "next/link";

export default function Home() {
  return (
    <main className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-8 max-w-2xl px-8">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          PPT Code Generator
        </h1>
        <p className="text-gray-400 text-lg">
          자연어로 설명하면 AI가 React PPT 코드를 생성합니다.
        </p>
        <Link
          href="/editor"
          className="inline-block px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition-colors"
        >
          시작하기
        </Link>
      </div>
    </main>
  );
}
