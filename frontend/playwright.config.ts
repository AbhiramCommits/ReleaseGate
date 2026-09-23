import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: {
    command: "docker compose -f ../docker-compose.yml up -d --build",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 300_000,
  },
});
