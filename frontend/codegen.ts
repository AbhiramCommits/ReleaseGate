import type { CodegenConfig } from "@graphql-codegen/cli";

const config: CodegenConfig = {
  schema: "schema.graphql",
  documents: "src/graphql/**/*.graphql",
  generates: {
    "src/generated/graphql.ts": {
      plugins: ["typescript-operations", "typescript-react-query"],
      config: {
        enumType: "enum",
        reactQueryVersion: 5,
        errorType: "Error",
        scalars: {
          DateTime: "string",
          JSON: "unknown",
        },
        fetcher: {
          func: "src/api/graphqlClient#graphqlFetcher",
          isReactHook: false,
        },
        exposeQueryKeys: true,
        exposeMutationKeys: true,
        addInfiniteQuery: false,
      },
    },
  },
};

export default config;
