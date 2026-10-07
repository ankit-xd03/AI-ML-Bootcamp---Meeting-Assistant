# Meeting Record

## Summary
The team reviewed API latency, noting it is 300 ms versus a target under 200 ms, and decided to keep the current database schema. They planned a CI pipeline deployment by Friday, assigned documentation updates, and scheduled benchmark sharing by Priya on Monday, while mentioning future load testing and continued model training.

## Minutes
### API latency
Latency is about 300 milliseconds, target is under 200 milliseconds.

### Redis caching
A suggestion to move to Redis caching was raised but no decision was made.

### Database schema
The team agreed to keep the current schema and not change it this sprint.

### CI pipeline deployment
The new CI pipeline will be deployed by Friday.

### Documentation
Documentation needs to be updated.

### Load testing
Load testing was mentioned as a future consideration.

### PyTorch model training
The model needs three more days of training before moving to Kubernetes.

### Benchmark results
Priya will share benchmark results with the team on Monday.

## Key Decisions
- Keep the current database schema for this sprint (00:14)
- Postpone decision on Redis caching today (00:14)

## Action Items
- Deploy the new CI pipeline | Owner: unspecified | Deadline: Friday (00:27)
- Update the documentation | Owner: unspecified | Deadline: unspecified (00:32)
- Share benchmark results with the team | Owner: Priya | Deadline: Monday (00:32)
