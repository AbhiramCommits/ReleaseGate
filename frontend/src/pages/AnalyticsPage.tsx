import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { stageLabel } from "../components/StageBadge";
import { formatHours } from "../format";
import { ChangeStage, useCycleTimeQuery } from "../generated/graphql";
import styles from "./AnalyticsPage.module.css";

const IN_FLIGHT_STAGES = [
  ChangeStage.Draft,
  ChangeStage.Submitted,
  ChangeStage.EngineeringReview,
  ChangeStage.ManufacturingReview,
];

export default function AnalyticsPage() {
  const query = useCycleTimeQuery();

  if (query.isLoading) {
    return <p className={styles.note}>Loading...</p>;
  }

  if (query.isError || !query.data?.cycleTimeAnalytics) {
    return (
      <p className={styles.error}>
        {query.error?.message ?? "Failed to load analytics."}
      </p>
    );
  }

  const analytics = query.data.cycleTimeAnalytics;
  const chartData = analytics.stageMetrics.map((metric) => ({
    name: stageLabel(metric.stage),
    averageHours: metric.averageHours ?? 0,
    medianHours: metric.medianHours ?? 0,
  }));

  const countFor = (stage: ChangeStage) =>
    analytics.currentStageCounts.find((entry) => entry.stage === stage)
      ?.count ?? 0;
  const inFlight = IN_FLIGHT_STAGES.reduce(
    (total, stage) => total + countFor(stage),
    0,
  );
  const totalRequests = analytics.currentStageCounts.reduce(
    (total, entry) => total + entry.count,
    0,
  );
  const slowest = analytics.topSlowestStages[0];

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Analytics</h1>

      <div className={styles.tiles}>
        <div className={styles.tile}>
          <p className={styles.tileValue}>
            {formatHours(analytics.endToEndAverageHours)}
          </p>
          <p className={styles.tileLabel}>Avg end-to-end approval</p>
        </div>
        <div className={styles.tile}>
          <p className={styles.tileValue}>{inFlight}</p>
          <p className={styles.tileLabel}>In-flight requests</p>
        </div>
        <div className={styles.tile}>
          <p className={styles.tileValue}>{totalRequests}</p>
          <p className={styles.tileLabel}>Total requests</p>
        </div>
      </div>

      {slowest && (
        <div className={styles.callout}>
          <strong>Slowest stage:</strong> {stageLabel(slowest.stage)} with an
          average dwell of {formatHours(slowest.averageHours)} (
          {slowest.samples} sample
          {slowest.samples === 1 ? "" : "s"}).
        </div>
      )}

      <div className={styles.chartCard}>
        <h2 className={styles.chartTitle}>Average dwell hours per stage</h2>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart
            data={chartData}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar
              dataKey="averageHours"
              name="Avg hours"
              fill="#4f46e5"
              radius={[4, 4, 0, 0]}
            />
            <Bar
              dataKey="medianHours"
              name="Median hours"
              fill="#a5b4fc"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
