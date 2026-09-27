export function HeroHeadline() {
  return (
    <div className="text-center">
      {/* Badge */}
      <div className="inline-flex items-center gap-2 rounded-full border border-[#B85C6E]/40 bg-[#520B1B]/60 px-4 py-1.5 text-xs font-semibold text-[#F7F2EF] mb-6 shadow-[0_0_12px_rgba(184,92,110,0.15)]">
        <span className="h-1.5 w-1.5 rounded-full bg-[#B85C6E]" />
        AI-Powered Repository Onboarding
      </div>

      <h1 className="text-4xl font-bold tracking-tight text-[#F7F2EF] sm:text-5xl lg:text-6xl leading-tight">
        Understand any repo{" "}
        <span className="gradient-text">in seconds</span>
      </h1>

      <p className="mt-5 max-w-xl mx-auto text-base text-[#F7F2EF]/70 leading-relaxed">
        DevPilot analyzes a GitHub repository and generates a structured
        onboarding report — architecture, key files, setup steps, dependencies,
        and recommended tasks.
      </p>
    </div>
  );
}
