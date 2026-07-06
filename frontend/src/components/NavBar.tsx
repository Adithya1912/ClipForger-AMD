import { Link } from "@tanstack/react-router";

export function NavBar() {
  return (
    <header className="relative z-20 flex items-center justify-between px-6 py-5 md:px-12">
      <Link to="/" className="flex items-center">
        <span className="font-brand text-5xl font-normal tracking-normal text-foreground md:text-6xl">
          ClipForger
        </span>
      </Link>
      <nav className="flex items-center gap-6 font-mono text-xs uppercase tracking-widest text-muted-foreground">
        <Link to="/" activeOptions={{ exact: true }} activeProps={{ className: "text-foreground" }}>
          Upload
        </Link>
        <Link to="/history" activeProps={{ className: "text-foreground" }}>
          Jobs
        </Link>
      </nav>
    </header>
  );
}
