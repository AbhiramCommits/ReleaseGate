import { useState } from "react";
import { keepPreviousData } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import RiskBadge from "../components/RiskBadge";
import Skeleton from "../components/Skeleton";
import StageBadge from "../components/StageBadge";
import { formatDate } from "../format";
import { ChangeStage, RiskLevel, useChangeRequestsQuery } from "../generated/graphql";
import styles from "./RequestsPage.module.css";

const PAGE_SIZE = 10;

const STAGE_OPTIONS = Object.values(ChangeStage);
const RISK_OPTIONS = Object.values(RiskLevel);

export default function RequestsPage() {
  const [stage, setStage] = useState<ChangeStage | undefined>(undefined);
  const [riskLevel, setRiskLevel] = useState<RiskLevel | undefined>(undefined);
  const [cursorStack, setCursorStack] = useState<(string | undefined)[]>([]);

  const after = cursorStack.length > 0 ? cursorStack[cursorStack.length - 1] : undefined;
  const query = useChangeRequestsQuery(
    { stage, riskLevel, first: PAGE_SIZE, after },
    { placeholderData: keepPreviousData },
  );
  const connection = query.data?.changeRequests;
  const rows = connection?.edges ?? [];

  const handleStageChange = (value: string) => {
    setStage(value === "" ? undefined : (value as ChangeStage));
    setCursorStack([]);
  };

  const handleRiskChange = (value: string) => {
    setRiskLevel(value === "" ? undefined : (value as RiskLevel));
    setCursorStack([]);
  };

  const handleNext = () => {
    setCursorStack((stack) => [...stack, connection?.pageInfo.endCursor ?? undefined]);
  };

  const handlePrev = () => {
    setCursorStack((stack) => stack.slice(0, -1));
  };

  return (
    <section className={styles.page}>
      <div className={styles.toolbar}>
        <h1 className={styles.title}>Change Requests</h1>
        <div className={styles.filters}>
          <select
            aria-label="Stage filter"
            className={styles.select}
            value={stage ?? ""}
            onChange={(event) => handleStageChange(event.target.value)}
          >
            <option value="">All stages</option>
            {STAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <select
            aria-label="Risk filter"
            className={styles.select}
            value={riskLevel ?? ""}
            onChange={(event) => handleRiskChange(event.target.value)}
          >
            <option value="">All risk levels</option>
            {RISK_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      </div>

      {query.isLoading && (
        <div className={styles.table}>
          {Array.from({ length: 5 }, (_, row) => (
            <div className={styles.skeletonRow} key={row}>
              <Skeleton width="5rem" />
              <Skeleton width="14rem" />
              <Skeleton width="6rem" />
              <Skeleton width="6rem" />
              <Skeleton width="4rem" />
              <Skeleton width="9rem" />
              <Skeleton width="9rem" />
            </div>
          ))}
        </div>
      )}

      {query.isError && <p className={styles.error}>{query.error?.message}</p>}

      {!query.isLoading && !query.isError && (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Title</th>
                <th>Program</th>
                <th>Subsystem</th>
                <th>Risk</th>
                <th>Stage</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ node }) => (
                <tr key={node.id}>
                  <td className={styles.ticket}>
                    <Link className={styles.link} to={`/requests/${node.id}`}>
                      {node.ticketKey}
                    </Link>
                  </td>
                  <td>
                    <Link className={styles.link} to={`/requests/${node.id}`}>
                      {node.title}
                    </Link>
                  </td>
                  <td>{node.vehicleProgram}</td>
                  <td>{node.subsystem}</td>
                  <td>
                    <RiskBadge risk={node.riskLevel} />
                  </td>
                  <td>
                    <StageBadge stage={node.currentStage} />
                  </td>
                  <td className={styles.date}>{formatDate(node.updatedAt)}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td className={styles.empty} colSpan={7}>
                    <p>No change requests match the current filters.</p>
                    <Link className={styles.link} to="/requests/new">
                      Create a new request
                    </Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className={styles.pagination}>
            <button
              className={styles.pageButton}
              type="button"
              onClick={handlePrev}
              disabled={cursorStack.length === 0}
            >
              Previous
            </button>
            <span className={styles.pageInfo} aria-live="polite">
              {connection ? `${connection.totalCount} total` : ""}
            </span>
            <button
              className={styles.pageButton}
              type="button"
              onClick={handleNext}
              disabled={!connection?.pageInfo.hasNextPage}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
