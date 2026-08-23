import { useQuery } from "@tanstack/react-query";
import api, { encodePathSegment } from "@/services/api";

export function useFixturePredictions(fixtureId) {
  return useQuery({
    queryKey: ["fixture-predictions", fixtureId],
    queryFn: async () => {
      const response = await api.get(`/fixtures/${encodePathSegment(fixtureId)}/predictions`);
      if (!response.data || typeof response.data !== "object") {
        throw new Error("Invalid prediction response from CricEdge API.");
      }
      if (!response.data.fixture || !Array.isArray(response.data.markets)) {
        throw new Error("Incomplete prediction response from CricEdge API.");
      }
      return response.data;
    },
    enabled: Boolean(fixtureId),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}
