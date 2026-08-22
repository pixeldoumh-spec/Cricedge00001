import { useQuery } from "@tanstack/react-query";
import api from "@/services/api";

export function useFixtures(format = "ALL") {
  return useQuery({
    queryKey: ["fixtures", { format }],
    queryFn: async () => {
      const config = format === "ALL" ? undefined : { params: { format } };
      const response = await api.get("/fixtures", config);
      return response.data;
    },
  });
}

export function useFixtureFormats() {
  return useQuery({
    queryKey: ["fixture-formats"],
    queryFn: async () => {
      const response = await api.get("/fixtures/formats");
      return response.data;
    },
  });
}
