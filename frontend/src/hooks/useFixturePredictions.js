import { useQuery } from "@tanstack/react-query";
import api from "@/services/api";

export function useFixturePredictions(fixtureId) {
  return useQuery({
    queryKey: ["fixture-predictions", fixtureId],
    queryFn: async () => {
      const response = await api.get(`/fixtures/${fixtureId}/predictions`);
      return response.data;
    },
    enabled: Boolean(fixtureId),
  });
}
