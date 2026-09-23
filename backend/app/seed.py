import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import (
    Approval,
    AuditEvent,
    ChangeRequest,
    ChangeStage,
    Decision,
    RiskLevel,
    Role,
    User,
)
from app.security import hash_password

random.seed(42)

SEED_PASSWORD = "password123"

USER_SEED = [
    ("requester@releasegate.dev", "Ava Requester", Role.REQUESTER),
    ("reviewer@releasegate.dev", "Ravi Reviewer", Role.REVIEWER),
    ("admin@releasegate.dev", "Morgan Admin", Role.ADMIN),
]

VEHICLE_PROGRAMS = ["Voyager", "Atlas", "Falcon", "Nimbus", "Titan"]
SUBSYSTEMS = [
    "Powertrain",
    "Chassis",
    "Electrical",
    "Body",
    "Interior",
    "Infotainment",
    "ADAS",
    "Thermal",
]

CHANGE_TEMPLATES = [
    ("Bracket reinforcement", "Strengthen mounting brackets to meet updated durability targets."),
    (
        "Wiring harness routing update",
        "Reroute main harness to reduce chafing risk near the firewall.",
    ),
    ("Software calibration update", "Update ECU calibration to improve cold-start behavior."),
    (
        "Fastener torque revision",
        "Revise torque specification on suspension fasteners per new test data.",
    ),
    ("Material substitution", "Replace bracket material with a higher-strength alloy."),
    ("Sensor mount relocation", "Relocate wheel speed sensor mount for improved signal quality."),
    ("Seal geometry change", "Adjust door seal geometry to reduce wind noise at highway speed."),
    ("Connector pin-out change", "Update connector pin-out to support a new camera variant."),
    ("Coolant hose re-route", "Re-route coolant hose to clear the revised front-end structure."),
    ("Damping curve retune", "Retune shock damping curve for improved ride comfort."),
    ("Weld sequence update", "Update weld sequence on the rear subframe to reduce distortion."),
    ("Paint masking revision", "Revise paint masking spec for the C-pillar trim region."),
    ("Battery tray sealant spec", "Update battery tray sealant application specification."),
    ("HVAC blend door logic", "Revise HVAC blend door control logic for faster warm-up."),
    ("Emblem retention change", "Switch emblem retention from tape to mechanical clips."),
    ("Headlamp aim procedure", "Update headlamp aim procedure for the facelift front fascia."),
    ("Carpet backing material", "Change carpet backing material to improve acoustics."),
    ("Steering column shroud", "Modify steering column shroud for revised switch packaging."),
    ("Exhaust hanger isolator", "Change exhaust hanger isolator durometer to reduce vibration."),
    ("Sunroof drain routing", "Re-route sunroof drains to prevent pooling in the rocker area."),
]

REVIEW_COMMENTS = [
    None,
    "Looks good, proceed.",
    "Approved with standard conditions.",
    "Risk accepted for this program.",
    "Please provide additional test data.",
    "Needs updated FMEA before proceeding.",
]

REQUEST_CHANGES_COMMENT = "Please add test data before this moves forward."
REJECT_COMMENT = "Rejected - see attached notes."


def event_times(start: datetime, count: int, now: datetime) -> list[datetime]:
    times = [start]
    cursor = start
    for _ in range(count):
        remaining = now - timedelta(minutes=30) - cursor
        cursor += remaining * random.uniform(0.15, 0.5)
        times.append(cursor)
    return times


def stage_transitions(target: ChangeStage) -> list[tuple[ChangeStage | None, ChangeStage, str]]:
    transitions = [(None, ChangeStage.DRAFT, "CREATED")]
    if target is ChangeStage.DRAFT:
        return transitions
    transitions.append((ChangeStage.DRAFT, ChangeStage.SUBMITTED, "SUBMITTED"))
    if target is ChangeStage.SUBMITTED:
        return transitions
    transitions.append(
        (ChangeStage.SUBMITTED, ChangeStage.ENGINEERING_REVIEW, "MOVED_TO_ENGINEERING_REVIEW")
    )
    if target is ChangeStage.ENGINEERING_REVIEW:
        return transitions
    if target is ChangeStage.REJECTED and random.random() < 0.5:
        transitions.append((ChangeStage.ENGINEERING_REVIEW, ChangeStage.REJECTED, "REJECTED"))
        return transitions
    transitions.append(
        (
            ChangeStage.ENGINEERING_REVIEW,
            ChangeStage.MANUFACTURING_REVIEW,
            "MOVED_TO_MANUFACTURING_REVIEW",
        )
    )
    if target is ChangeStage.MANUFACTURING_REVIEW:
        return transitions
    if target is ChangeStage.REJECTED:
        transitions.append((ChangeStage.MANUFACTURING_REVIEW, ChangeStage.REJECTED, "REJECTED"))
        return transitions
    transitions.append((ChangeStage.MANUFACTURING_REVIEW, ChangeStage.APPROVED, "APPROVED"))
    return transitions


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)):
            print("Seed data already present; skipping.")
            return

        users: dict[Role, User] = {}
        for email, full_name, role in USER_SEED:
            user = User(
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(SEED_PASSWORD),
            )
            users[role] = user
            db.add(user)
        db.flush()

        now = datetime.now(UTC)
        requesters = [users[Role.REQUESTER], users[Role.REVIEWER], users[Role.ADMIN]]
        requester_weights = [80, 10, 10]

        targets = (
            [ChangeStage.DRAFT] * 7
            + [ChangeStage.SUBMITTED] * 7
            + [ChangeStage.ENGINEERING_REVIEW] * 7
            + [ChangeStage.MANUFACTURING_REVIEW] * 7
            + [ChangeStage.APPROVED] * 7
            + [ChangeStage.REJECTED] * 5
        )
        random.shuffle(targets)

        total_approvals = 0
        total_events = 0
        for index, target in enumerate(targets):
            title, description = CHANGE_TEMPLATES[index % len(CHANGE_TEMPLATES)]
            program = random.choice(VEHICLE_PROGRAMS)
            subsystem = random.choice(SUBSYSTEMS)
            requester = random.choices(requesters, weights=requester_weights, k=1)[0]

            transitions = stage_transitions(target)
            times = event_times(now - timedelta(days=random.uniform(3, 90)), len(transitions), now)

            change_request = ChangeRequest(
                ticket_key=f"ECR-{1000 + index}",
                title=title,
                description=f"{description} Applies to the {program} program, {subsystem} subsystem.",
                vehicle_program=program,
                subsystem=subsystem,
                risk_level=random.choices(
                    [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH], weights=[20, 50, 30], k=1
                )[0],
                current_stage=target,
                requester=requester,
                created_at=times[0],
                updated_at=times[-1],
            )
            db.add(change_request)
            db.flush()

            events: list[AuditEvent] = []
            approvals: list[Approval] = []
            for idx, (from_stage, to_stage, action) in enumerate(transitions):
                actor = requester
                if to_stage is ChangeStage.APPROVED or (
                    to_stage is ChangeStage.REJECTED
                    and from_stage is ChangeStage.MANUFACTURING_REVIEW
                ):
                    actor = users[Role.ADMIN]
                elif from_stage is ChangeStage.ENGINEERING_REVIEW and (
                    to_stage is ChangeStage.MANUFACTURING_REVIEW or to_stage is ChangeStage.REJECTED
                ):
                    actor = users[Role.REVIEWER]

                events.append(
                    AuditEvent(
                        change_request=change_request,
                        actor=actor,
                        from_stage=from_stage,
                        to_stage=to_stage,
                        action=action,
                        meta={"source": "seed"},
                        created_at=times[idx],
                    )
                )

                if from_stage is ChangeStage.ENGINEERING_REVIEW and (
                    to_stage is ChangeStage.MANUFACTURING_REVIEW
                ):
                    approvals.append(
                        Approval(
                            change_request=change_request,
                            stage=ChangeStage.ENGINEERING_REVIEW,
                            reviewer=users[Role.REVIEWER],
                            decision=Decision.APPROVE,
                            comment=random.choice(REVIEW_COMMENTS),
                            decided_at=times[idx],
                        )
                    )
                elif from_stage is ChangeStage.MANUFACTURING_REVIEW and (
                    to_stage is ChangeStage.APPROVED
                ):
                    approvals.append(
                        Approval(
                            change_request=change_request,
                            stage=ChangeStage.MANUFACTURING_REVIEW,
                            reviewer=users[Role.ADMIN],
                            decision=Decision.APPROVE,
                            comment=random.choice(REVIEW_COMMENTS),
                            decided_at=times[idx],
                        )
                    )
                elif to_stage is ChangeStage.REJECTED:
                    reviewer = (
                        users[Role.ADMIN]
                        if from_stage is ChangeStage.MANUFACTURING_REVIEW
                        else users[Role.REVIEWER]
                    )
                    approvals.append(
                        Approval(
                            change_request=change_request,
                            stage=from_stage,
                            reviewer=reviewer,
                            decision=Decision.REJECT,
                            comment=REJECT_COMMENT,
                            decided_at=times[idx],
                        )
                    )

            if target is ChangeStage.ENGINEERING_REVIEW and random.random() < 0.4:
                entry_index = next(
                    idx
                    for idx, (_, to_stage, _) in enumerate(transitions)
                    if to_stage is ChangeStage.ENGINEERING_REVIEW
                )
                decision_time = times[entry_index] + (
                    now - timedelta(minutes=30) - times[entry_index]
                ) * random.uniform(0.1, 0.4)
                approvals.append(
                    Approval(
                        change_request=change_request,
                        stage=ChangeStage.ENGINEERING_REVIEW,
                        reviewer=users[Role.REVIEWER],
                        decision=Decision.REQUEST_CHANGES,
                        comment=REQUEST_CHANGES_COMMENT,
                        decided_at=decision_time,
                    )
                )
                events.append(
                    AuditEvent(
                        change_request=change_request,
                        actor=users[Role.REVIEWER],
                        from_stage=ChangeStage.ENGINEERING_REVIEW,
                        to_stage=ChangeStage.ENGINEERING_REVIEW,
                        action="REQUESTED_CHANGES",
                        meta={"source": "seed"},
                        created_at=decision_time,
                    )
                )

            db.add_all(events)
            db.add_all(approvals)
            total_events += len(events)
            total_approvals += len(approvals)

        db.commit()
        print(
            f"Seeded 3 users, {len(targets)} change requests, "
            f"{total_approvals} approvals, {total_events} audit events."
        )


if __name__ == "__main__":
    seed()
