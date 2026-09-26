export function HeroHeadline() {
  return (
    <div className="text-center">
      <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-xs font-semibold text-blue-700 mb-6">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
        AI-Powered Repository Onboarding
      </div>

      <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
        Understand any repo{" "}
        <span className="text-blue-600">in seconds</span>
      </h1>

      <p className="mt-4 max-w-xl mx-auto text-base text-gray-500 leading-relaxed">
        DevPilot analyzes a GitHub repository and generates a structured
        onboarding report — architecture, key files, setup steps, dependencies,
        and recommended tasks.
      </p>
    </div>
  );
}
