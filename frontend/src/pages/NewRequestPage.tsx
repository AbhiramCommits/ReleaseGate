import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RiskLevel, useCreateChangeRequestMutation } from "../generated/graphql";
import styles from "./NewRequestPage.module.css";

interface FormState {
  title: string;
  description: string;
  vehicleProgram: string;
  subsystem: string;
  riskLevel: RiskLevel | undefined;
}

const EMPTY_FORM: FormState = {
  title: "",
  description: "",
  vehicleProgram: "",
  subsystem: "",
  riskLevel: undefined,
};

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {};
  if (!form.title.trim()) {
    errors.title = "Title is required.";
  } else if (form.title.length > 500) {
    errors.title = "Title must be 500 characters or fewer.";
  }
  if (!form.description.trim()) {
    errors.description = "Description is required.";
  }
  if (!form.vehicleProgram.trim()) {
    errors.vehicleProgram = "Vehicle program is required.";
  }
  if (!form.subsystem.trim()) {
    errors.subsystem = "Subsystem is required.";
  }
  if (!form.riskLevel) {
    errors.riskLevel = "Risk level is required.";
  }
  return errors;
}

export default function NewRequestPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});
  const errors = validate(form);

  const createMutation = useCreateChangeRequestMutation({
    onSuccess: (data) => {
      navigate(`/requests/${data.createChangeRequest.id}`, { replace: true });
    },
  });

  const setField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
    setTouched((current) => ({ ...current, [field]: true }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched({ title: true, description: true, vehicleProgram: true, subsystem: true, riskLevel: true });
    if (Object.keys(errors).length > 0 || !form.riskLevel) {
      return;
    }
    createMutation.mutate({
      input: {
        title: form.title.trim(),
        description: form.description.trim(),
        vehicleProgram: form.vehicleProgram.trim(),
        subsystem: form.subsystem.trim(),
        riskLevel: form.riskLevel,
      },
    });
  };

  const showError = (field: keyof FormState) => touched[field] && errors[field];

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>New Change Request</h1>
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <label className={styles.label} htmlFor="title">
          Title
        </label>
        <input
          id="title"
          className={styles.input}
          value={form.title}
          onChange={(event) => setField("title", event.target.value)}
          placeholder="e.g. Bracket reinforcement"
        />
        {showError("title") && <p className={styles.error}>{errors.title}</p>}

        <label className={styles.label} htmlFor="description">
          Description
        </label>
        <textarea
          id="description"
          className={styles.textarea}
          value={form.description}
          onChange={(event) => setField("description", event.target.value)}
          placeholder="What is changing and why?"
          rows={5}
        />
        {showError("description") && <p className={styles.error}>{errors.description}</p>}

        <div className={styles.row}>
          <div className={styles.column}>
            <label className={styles.label} htmlFor="vehicleProgram">
              Vehicle Program
            </label>
            <input
              id="vehicleProgram"
              className={styles.input}
              value={form.vehicleProgram}
              onChange={(event) => setField("vehicleProgram", event.target.value)}
              placeholder="e.g. Voyager"
            />
            {showError("vehicleProgram") && (
              <p className={styles.error}>{errors.vehicleProgram}</p>
            )}
          </div>
          <div className={styles.column}>
            <label className={styles.label} htmlFor="subsystem">
              Subsystem
            </label>
            <input
              id="subsystem"
              className={styles.input}
              value={form.subsystem}
              onChange={(event) => setField("subsystem", event.target.value)}
              placeholder="e.g. Chassis"
            />
            {showError("subsystem") && <p className={styles.error}>{errors.subsystem}</p>}
          </div>
        </div>

        <label className={styles.label} htmlFor="riskLevel">
          Risk Level
        </label>
        <select
          id="riskLevel"
          className={styles.select}
          value={form.riskLevel ?? ""}
          onChange={(event) =>
            setField("riskLevel", event.target.value === "" ? undefined : (event.target.value as RiskLevel))
          }
        >
          <option value="">Select a risk level</option>
          {Object.values(RiskLevel).map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
        {showError("riskLevel") && <p className={styles.error}>{errors.riskLevel}</p>}

        {createMutation.isError && (
          <p className={styles.error}>{createMutation.error.message}</p>
        )}

        <button className={styles.submit} type="submit" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Creating..." : "Create Request"}
        </button>
      </form>
    </section>
  );
}
