import { RiskLevel } from "../generated/graphql";
import styles from "./RiskBadge.module.css";

const RISK_LABELS: Record<RiskLevel, string> = {
  [RiskLevel.Low]: "Low",
  [RiskLevel.Medium]: "Medium",
  [RiskLevel.High]: "High",
};

const RISK_CLASSES: Record<RiskLevel, string> = {
  [RiskLevel.Low]: styles.low,
  [RiskLevel.Medium]: styles.medium,
  [RiskLevel.High]: styles.high,
};

export function riskLabel(risk: RiskLevel): string {
  return RISK_LABELS[risk];
}

export default function RiskBadge({ risk }: { risk: RiskLevel }) {
  return <span className={`${styles.badge} ${RISK_CLASSES[risk]}`}>{RISK_LABELS[risk]}</span>;
}
