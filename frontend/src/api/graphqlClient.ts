import { getToken } from "../auth";

export class GraphQLError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GraphQLError";
  }
}

export function graphqlFetcher<TData, TVariables>(
  query: unknown,
  variables?: TVariables,
): () => Promise<TData> {
  return async () => {
    const token = getToken();
    const response = await fetch("/graphql", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query, variables }),
    });
    const payload = await response.json();
    if (payload.errors?.length) {
      throw new GraphQLError(payload.errors[0].message);
    }
    return payload.data as TData;
  };
}
