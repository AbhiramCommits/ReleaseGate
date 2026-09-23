.PHONY: test lint fmt schema e2e

schema:
	$(MAKE) -C backend schema
	cp backend/schema.graphql frontend/schema.graphql

test:
	$(MAKE) -C backend test
	cd frontend && npm run test

lint:
	$(MAKE) -C backend lint
	cd frontend && npm run lint

fmt:
	$(MAKE) -C backend fmt
	cd frontend && npm run fmt

e2e:
	docker compose up -d --build
	for i in $$(seq 1 60); do curl -fsS http://localhost:8003/healthz >/dev/null 2>&1 && break; sleep 1; done
	cd frontend && npx playwright test
	docker compose down
