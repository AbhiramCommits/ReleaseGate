.PHONY: schema

schema:
	$(MAKE) -C backend schema
	cp backend/schema.graphql frontend/schema.graphql
