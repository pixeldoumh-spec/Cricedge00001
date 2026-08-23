import { useQuery } from "@tanstack/react-query";
import api from "@/services/api";

export function useFixtures(format = "ALL") {
  return useQuery({
    queryKey: ["fixtures", { format }],
    queryFn: async () => {
      const config = format === "ALL" ? undefined : { params: { format } };
      const response = await api.get("/fixtures", config);
      if (!Array.isArray(response.data)) {
        throw new Error("Invalid fixture response from CricEdge API.");
      }
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

export function useFixtureFormats() {
  return useQuery({
    queryKey: ["fixture-formats"],
    queryFn: async () => {
      const response = await api.get("/fixtures/formats");
      if (!response.data || !Array.isArray(response.data.formats)) {
        throw new Error("Invalid format response from CricEdge API.");
      }
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
    retry: 2,
  });
}
