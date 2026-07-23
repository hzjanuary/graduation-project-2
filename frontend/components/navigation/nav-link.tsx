"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface NavLinkProps {
  href: string;
  label: string;
}

export function NavLink({ href, label }: NavLinkProps) {
  const pathname = usePathname();
  const isActive =
    pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));

  return (
    <Link
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "relative flex min-h-10 items-center rounded-md border border-transparent px-3 text-sm font-medium transition",
        isActive
          ? "border-primary/30 bg-primary/10 pl-4 text-foreground shadow-[0_0_26px_hsl(var(--primary)/0.16)] before:absolute before:left-0 before:top-2 before:h-6 before:w-0.5 before:rounded-full before:bg-primary"
          : "text-muted-foreground hover:border-border/70 hover:bg-secondary/50 hover:text-foreground",
      )}
      href={href}
    >
      {label}
    </Link>
  );
}
