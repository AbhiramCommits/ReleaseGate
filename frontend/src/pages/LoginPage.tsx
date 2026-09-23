import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { login } from "../api/client";
import { setToken } from "../auth";
import styles from "./LoginPage.module.css";

interface LocationState {
  from?: { pathname: string };
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  const mutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: (data) => {
      setToken(data.access_token);
      const state = location.state as LocationState | null;
      navigate(state?.from?.pathname ?? "/requests", { replace: true });
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate();
  };

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1 className={styles.brand}>ReleaseGate</h1>
        <p className={styles.subtitle}>Sign in to manage change requests</p>
        <label className={styles.label} htmlFor="email">
          Email
        </label>
        <input
          id="email"
          className={styles.input}
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
        <label className={styles.label} htmlFor="password">
          Password
        </label>
        <input
          id="password"
          className={styles.input}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
        {mutation.isError && (
          <p className={styles.error}>{mutation.error.message}</p>
        )}
        <button
          className={styles.submit}
          type="submit"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
