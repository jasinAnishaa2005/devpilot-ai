import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="text-5xl font-bold text-gray-200 mb-4">404</div>
      <h1 className="text-xl font-semibold text-gray-800 mb-2">
        Page not found
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        This page doesn&apos;t exist. Head back to analyze a repository.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
      >
        ← Back to DevPilot
      </Link>
    </main>
  );
}
