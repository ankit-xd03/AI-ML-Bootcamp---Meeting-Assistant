# Meeting Record

## Summary
The team reviewed launch readiness, covering API latency, database choice, authentication, CI/CD pipeline, load testing, budget, documentation, and demo scheduling. They decided to keep PostgreSQL, use Locust for load testing, add a GPU instance, postpone CSV export, and set the demo for October 20. Action items include benchmarking Redis, completing OAuth login, updating design screens, deploying the pipeline by Tuesday, writing load test scripts, updating API docs, and drafting the export format.

## Minutes
### API latency
Current latency is ~450 ms, target under 200 ms; cause is a database query per request.

### Redis caching
Suggested as an idea but not committed; benchmark to be run.

### Database migration
Proposal to move to MongoDB deemed risky close to launch; decision to stay on PostgreSQL.

### Authentication/OAuth login
Priya assigned to implement OAuth login, pending final design screens.

### Dark mode
Considered dropping to save time, but decision deferred pending customer feedback.

### CI/CD pipeline
Pipeline nearly ready; deployment to staging moved to Tuesday to support benchmark.

### Load testing
Plan to test 10,000 concurrent users using Locust; scripts to be written.

### Budget
Cloud budget $12k with $8k spent; approved addition of one extra GPU instance for demo week.

### Documentation
API docs outdated; need update before launch.

### Customer feedback - CSV export
Three pilots requested CSV export; decision not to ship in first release, will be added in version 2.

### Demo date
Demo scheduled for 20th October after unanimous agreement.

## Key Decisions
- Stay on PostgreSQL for launch, no migration this quarter (01:03)
- Use Locust for load testing (02:17)
- Deploy CI/CD pipeline to staging on Tuesday (01:55)
- Add extra GPU instance for demo week (02:41)
- Do not ship CSV export in first release (03:08)
- Demo scheduled for 20th of October (03:36)

## Action Items
- Benchmark Redis caching and share results | Owner: unspecified | Deadline: Wednesday (00:41)
- Finish OAuth login | Owner: Priya | Deadline: next Friday (01:21)
- Ask design team for final login screens | Owner: unspecified | Deadline: unspecified (01:27)
- Deploy CI/CD pipeline to staging | Owner: Arjun | Deadline: Tuesday (01:55)
- Write load test scripts using Locust | Owner: Arjun | Deadline: unspecified (02:17)
- Update API documentation before launch | Owner: unspecified | Deadline: unspecified (02:41)
- Draft export format after launch | Owner: unspecified | Deadline: the week after launch (03:18)
