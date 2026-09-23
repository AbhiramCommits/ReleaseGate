import { ChangeStage } from "../generated/graphql";
import styles from "./StageBadge.module.css";

const STAGE_LABELS: Record<ChangeStage, string> = {
  [ChangeStage.Draft]: "Draft",
  [ChangeStage.Submitted]: "Submitted",
  [ChangeStage.EngineeringReview]: "Engineering Review",
  [ChangeStage.ManufacturingReview]: "Manufacturing Review",
  [ChangeStage.Approved]: "Approved",
  [ChangeStage.Rejected]: "Rejected",
};

const STAGE_CLASSES: Record<ChangeStage, string> = {
  [ChangeStage.Draft]: styles.draft,
  [ChangeStage.Submitted]: styles.submitted,
  [ChangeStage.EngineeringReview]: styles.engineering,
  [ChangeStage.ManufacturingReview]: styles.manufacturing,
  [ChangeStage.Approved]: styles.approved,
  [ChangeStage.Rejected]: styles.rejected,
};

export function stageLabel(stage: ChangeStage): string {
  return STAGE_LABELS[stage];
}

export default function StageBadge({ stage }: { stage: ChangeStage }) {
  return (
    <span
      data-testid="stage-badge"
      className={`${styles.badge} ${STAGE_CLASSES[stage]}`}
    >
      {STAGE_LABELS[stage]}
    </span>
  );
}
