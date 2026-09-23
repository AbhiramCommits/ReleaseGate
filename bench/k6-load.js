import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8003";
const USER_EMAIL = __ENV.USER_EMAIL || "requester@releasegate.dev";
const USER_PASSWORD = __ENV.USER_PASSWORD || "password123";

export const options = {
  vus: 50,
  duration: "30s",
  summaryTrendStats: ["p(50)", "p(90)", "p(95)", "p(99)"],
};

const LIST_QUERY = `query {
  changeRequests(first: 20) {
    edges { node { id ticketKey title currentStage riskLevel requester { id } } }
    pageInfo { hasNextPage endCursor }
    totalCount
  }
}`;

const CYCLE_QUERY = `query {
  cycleTimeAnalytics {
    stageMetrics { stage averageHours medianHours samples }
    currentStageCounts { stage count }
    endToEndAverageHours
    topSlowestStages { stage averageHours }
  }
}`;

export function setup() {
  const response = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: USER_EMAIL, password: USER_PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  if (response.status !== 200) {
    throw new Error(`Login failed with status ${response.status}`);
  }
  return { token: response.json().access_token };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };

  const list = http.post(
    `${BASE_URL}/graphql`,
    JSON.stringify({ query: LIST_QUERY }),
    { headers, tags: { name: "changeRequests" } },
  );
  check(list, { "list ok": (r) => r.status === 200 });

  const cycle = http.post(
    `${BASE_URL}/graphql`,
    JSON.stringify({ query: CYCLE_QUERY }),
    { headers, tags: { name: "cycleTimeAnalytics" } },
  );
  check(cycle, { "cycle ok": (r) => r.status === 200 });

  sleep(0.2);
}
