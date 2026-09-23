import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import DecisionBadge from "../components/DecisionBadge";
import RiskBadge from "../components/RiskBadge";
import Skeleton from "../components/Skeleton";
import StageBadge, { stageLabel } from "../components/StageBadge";
import { formatDate } from "../format";
import {
  ChangeRequestDetailQuery,
  useChangeRequestDetailQuery,
  useChangeRequestsQuery,
  useMeQuery,
  useTransitionChangeRequestMutation,
  WorkflowAction,
} from "../generated/graphql";
import { ACTION_LABELS, allowedActions, optimisticNextStage } from "../workflow";
import styles from "./RequestDetailPage.module.css";

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const requestId = id ?? "";
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");

  const detailKey = useChangeRequestDetailQuery.getKey({ id: requestId });
  const detailQuery = useChangeRequestDetailQuery({ id: requestId });
  const meQuery = useMeQuery();
  const transitionMutation = useTransitionChangeRequestMutation<
    Error,
    { previous?: ChangeRequestDetailQuery }
  >({
    onMutate: async ({ action }) => {
      await queryClient.cancelQueries({ queryKey: detailKey });
      const previous = queryClient.getQueryData<ChangeRequestDetailQuery>(detailKey);
      if (previous?.changeRequest) {
        queryClient.setQueryData<ChangeRequestDetailQuery>(detailKey, {
          ...previous,
          changeRequest: {
            ...previous.changeRequest,
            currentStage: optimisticNextStage(action, previous.changeRequest.currentStage),
          },
        });
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(detailKey, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: detailKey });
      queryClient.invalidateQueries({ queryKey: useChangeRequestsQuery.getKey() });
    },
  });

  if (detailQuery.isLoading) {
    return (
      <section className={styles.page} aria-busy="true">
        <Skeleton width="6rem" height="1rem" />
        <Skeleton width="20rem" height="1.75rem" className={styles.skeletonGap} />
        <div className={styles.skeletonRow}>
          <Skeleton width="9rem" height="1.5rem" />
          <Skeleton width="5rem" height="1.5rem" />
        </div>
        <div className={styles.skeletonBlock}>
          <Skeleton width="100%" height="1rem" />
          <Skeleton width="85%" height="1rem" />
          <Skeleton width="60%" height="1rem" />
        </div>
        <div className={styles.skeletonBlock}>
          <Skeleton width="100%" height="1rem" />
          <Skeleton width="70%" height="1rem" />
        </div>
      </section>
    );
  }

  const request = detailQuery.data?.changeRequest;
  if (detailQuery.isError || !request) {
    return (
      <section className={styles.page}>
        <h1 className={styles.title}>Request not found</h1>
        <p className={styles.note}>{detailQuery.error?.message ?? "This request may have been removed."}</p>
        <Link className={styles.link} to="/requests">
          Back to requests
        </Link>
      </section>
    );
  }

  const me = meQuery.data?.me;
  const actions = allowedActions(me?.role, request.currentStage, request.requesterId, me?.id);

  const handleAction = (action: WorkflowAction) => {
    transitionMutation.mutate({
      id: requestId,
      action,
      comment: comment.trim() || undefined,
    });
  };

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <div>
          <p className={styles.ticket}>{request.ticketKey}</p>
          <h1 className={styles.title}>{request.title}</h1>
          <p className={styles.meta}>
            {request.vehicleProgram} &middot; {request.subsystem} &middot; requested by{" "}
            {request.requester?.fullName ?? request.requesterId}
          </p>
        </div>
        <div className={styles.badges}>
          <StageBadge stage={request.currentStage} />
          <RiskBadge risk={request.riskLevel} />
        </div>
      </div>

      <p className={styles.dates}>
        Created {formatDate(request.createdAt)} &middot; Updated {formatDate(request.updatedAt)}
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Description</h2>
        <p className={styles.description}>{request.description}</p>
      </section>

      {actions.length > 0 && (
        <section className={styles.actionBar} aria-label="Transition actions">
          <h2 className={styles.sectionTitle}>Actions</h2>
          <textarea
            aria-label="Transition comment"
            className={styles.comment}
            placeholder="Add a comment (optional)"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={2}
          />
          <div className={styles.actionButtons}>
            {actions.map((action) => (
              <button
                key={action}
                className={styles.actionButton}
                type="button"
                onClick={() => handleAction(action)}
                disabled={transitionMutation.isPending}
              >
                {ACTION_LABELS[action]}
              </button>
            ))}
          </div>
          {transitionMutation.isError && (
            <p className={styles.error} role="alert">
              {transitionMutation.error.message}
            </p>
          )}
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Approval History</h2>
        {request.approvals.length === 0 ? (
          <p className={styles.note}>No approvals recorded yet.</p>
        ) : (
          <ul className={styles.approvalList}>
            {request.approvals.map((approval) => (
              <li key={approval.id} className={styles.approvalItem}>
                <DecisionBadge decision={approval.decision} />
                <span className={styles.approvalStage}>{stageLabel(approval.stage)}</span>
                <span className={styles.approvalReviewer}>
                  by {approval.reviewer?.fullName ?? "Unknown"}
                </span>
                <span className={styles.approvalDate}>{formatDate(approval.decidedAt)}</span>
                {approval.comment && (
                  <p className={styles.approvalComment}>{approval.comment}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Audit Trail</h2>
        <ol className={styles.timeline} data-testid="audit-timeline" aria-label="Audit trail">
          {request.auditEvents.map((event) => (
            <li key={event.id} className={styles.timelineItem}>
              <span className={styles.timelineDot} />
              <div className={styles.timelineBody}>
                <p className={styles.timelineAction}>
                  {event.action}
                  {event.fromStage && event.toStage && event.fromStage !== event.toStage && (
                    <span className={styles.timelineStage}>
                      {" "}
                      {stageLabel(event.fromStage)} &rarr; {stageLabel(event.toStage)}
                    </span>
                  )}
                </p>
                <p className={styles.timelineMeta}>
                  {event.actor?.fullName ?? "Unknown"} &middot; {formatDate(event.createdAt)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </section>
  );
}
