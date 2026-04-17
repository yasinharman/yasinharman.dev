export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-8 py-6 flex items-center justify-between pointer-events-none">
      <div className="flex items-center gap-2 pointer-events-auto">
        <span className="text-xl tracking-tight text-white transition-colors cursor-pointer group font-bricolage font-semibold">
          Yasin<span className="text-orange-500 group-hover:text-orange-400 transition-colors drop-shadow-[0_0_8px_rgba(249,115,22,0.5)] font-bricolage font-semibold">.</span>Harman
        </span>
      </div>
      {/* Empty right side to enforce the constraint: No nav links or buttons */}
    </header>
  );
}