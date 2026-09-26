import Link from "next/link";

export default function NotFound() {
  return (
    <main className="wine-bg min-h-screen flex flex-col items-center justify-center p-6 text-center">
      <div className="text-5xl font-bold text-[#520B1B] mb-4">404</div>
      <h1 className="text-xl font-semibold text-[#F7F2EF] mb-2">
        Page not found
      </h1>
      <p className="text-sm text-[#F7F2EF]/55 mb-8">
        This page doesn&apos;t exist. Head back to analyze a repository.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-md bg-[#3A0714] border border-[#7A1830]/60 px-4 py-2 text-sm font-medium text-white hover:bg-[#520B1B] transition-colors duration-200"
      >
        ← Back to DevPilot
      </Link>
    </main>
  );
}
