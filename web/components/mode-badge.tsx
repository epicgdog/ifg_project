import { Badge } from "@/components/ui/badge";

export function ModeBadge({ audience }: { audience: string }) {
  const normalized = (audience || "").toLowerCase();
  const isReferral =
    normalized.includes("referral") || normalized.includes("advocate");
  return (
    <Badge variant={isReferral ? "secondary" : "default"} className="capitalize">
      {isReferral ? "Referral Advocate" : "Owner"}
    </Badge>
  );
}
