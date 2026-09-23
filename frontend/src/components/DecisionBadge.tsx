import { Decision } from "../generated/graphql";
import styles from "./DecisionBadge.module.css";

const DECISION_LABELS: Record<Decision, string> = {
  [Decision.Approve]: "Approved",
  [Decision.Reject]: "Rejected",
  [Decision.RequestChanges]: "Changes Requested",
};

const DECISION_CLASSES: Record<Decision, string> = {
  [Decision.Approve]: styles.approve,
  [Decision.Reject]: styles.reject,
  [Decision.RequestChanges]: styles.requestChanges,
};

export default function DecisionBadge({ decision }: { decision: Decision }) {
  return (
    <span className={`${styles.badge} ${DECISION_CLASSES[decision]}`}>
      {DECISION_LABELS[decision]}
    </span>
  );
}
